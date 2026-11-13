#!/usr/bin/env python3
"""Controlled digest-based Docker Compose deployment and rollback."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIGEST_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-fA-F]{64}$")
DEFAULT_IMAGE_ENV_KEY = "SERVICE_IMAGE_REFERENCE"
IMAGE_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class DeploymentError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeploymentError(f"Ungültiges JSON in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise DeploymentError(f"JSON-Objekt erwartet: {path}")
    return document


def canonical_repository(image: str) -> str:
    name_part = image.split("@", 1)[0]
    parts = name_part.split("/")
    first = parts[0]
    if "." in first or ":" in first or first == "localhost":
        registry = first.lower()
        repository_parts = parts[1:]
    else:
        registry = "docker.io"
        repository_parts = parts
    if registry == "docker.io" and len(repository_parts) == 1:
        repository_parts = ["library", repository_parts[0]]
    return f"{registry}/{'/'.join(repository_parts)}".lower()


def validate_image(image: str, policy: dict[str, Any]) -> str:
    if not DIGEST_RE.fullmatch(image):
        raise DeploymentError(
            "Image muss vollständig über Registry/Repository@sha256:<digest> referenziert sein."
        )

    repository = canonical_repository(image)
    first_party = policy["first_party"]
    first_party_prefix = (
        f"{first_party['registry'].lower()}/"
        f"{first_party['namespace'].lower()}/"
    )
    if repository.startswith(first_party_prefix):
        return "first-party"

    third_party = {
        str(item["repository"]).lower()
        for item in policy.get("third_party", [])
    }
    if repository in third_party:
        return "third-party"

    raise DeploymentError(f"Image-Quelle ist nicht allowgelistet: {repository}")


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        env=env,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        if result.stdout:
            sys.stderr.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        raise DeploymentError(
            f"Befehl fehlgeschlagen ({result.returncode}): {' '.join(command)}"
        )
    return result


def compose_base(args: argparse.Namespace) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(args.release_env),
        "-p",
        args.project_name,
        "-f",
        str(args.compose_file),
    ]


def compose_config_for_image(args: argparse.Namespace, image: str) -> dict[str, Any]:
    env = os.environ.copy()
    env[args.image_env_key] = image
    result = run(
        [
            "docker",
            "compose",
            "-p",
            args.project_name,
            "-f",
            str(args.compose_file),
            "config",
            "--format",
            "json",
        ],
        env=env,
    )
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise DeploymentError(f"docker compose config lieferte ungültiges JSON: {exc}") from exc

    service = (document.get("services") or {}).get(args.service)
    if not isinstance(service, dict):
        raise DeploymentError(f"Service fehlt im Compose-Manifest: {args.service}")
    if service.get("image") != image:
        raise DeploymentError(
            f"Compose löst Zielimage nicht korrekt auf: {service.get('image')!r}"
        )
    return document


def write_release_env(path: Path, image: str, image_env_key: str) -> None:
    atomic_write(path, f"{image_env_key}={image}\n")


def validate_image_env_key(image_env_key: str) -> None:
    if not IMAGE_ENV_KEY_RE.fullmatch(image_env_key):
        raise DeploymentError(
            "Image-Environment-Key muss dem Muster [A-Z][A-Z0-9_]* entsprechen."
        )


def container_status(args: argparse.Namespace) -> tuple[bool, str | None]:
    result = run(
        compose_base(args) + ["ps", "-q", args.service],
        check=False,
    )
    container_id = result.stdout.strip()
    if not container_id:
        return False, None

    inspect = run(["docker", "inspect", container_id], check=False)
    if inspect.returncode != 0:
        return False, None
    document = json.loads(inspect.stdout)[0]
    state = document.get("State") or {}
    running = state.get("Running") is True
    health = (state.get("Health") or {}).get("Status")
    if health == "unhealthy":
        return False, health
    return running, health


def verification_probe(args: argparse.Namespace, image: str) -> bool:
    running, _ = container_status(args)
    if not running:
        return False

    if args.verify_url:
        try:
            request = urllib.request.Request(
                args.verify_url,
                headers={"User-Agent": "merchfactory-deployment-verifier/1"},
            )
            with urllib.request.urlopen(request, timeout=args.verify_timeout) as response:
                return response.status == args.expected_status
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return False

    if args.verify_exec:
        env = os.environ.copy()
        env.update(
            {
                "DEPLOY_SERVICE": args.service,
                "DEPLOY_PROJECT": args.project_name,
                "DEPLOY_IMAGE": image,
            }
        )
        result = run([args.verify_exec, *args.verify_arg], env=env, check=False)
        return result.returncode == 0

    raise DeploymentError("Verifikationsprobe fehlt.")


def wait_for_verification(args: argparse.Namespace, image: str) -> bool:
    for attempt in range(1, args.verify_attempts + 1):
        if verification_probe(args, image):
            print(f"VERIFICATION: erfolgreich nach Versuch {attempt}.")
            return True
        if attempt < args.verify_attempts:
            time.sleep(args.verify_interval)
    return False


def deploy_image(args: argparse.Namespace, image: str) -> None:
    write_release_env(args.release_env, image, args.image_env_key)
    run(
        compose_base(args)
        + ["up", "-d", "--no-build", "--pull", "never", args.service]
    )


def pull_image(image: str) -> None:
    run(["docker", "pull", image])


def release_record(args: argparse.Namespace, image: str) -> dict[str, Any]:
    return {
        "image": image,
        "source_revision": args.source_revision,
        "release_reference": args.release_reference,
        "approval_reference": args.approval_reference,
        "backup_reference": args.backup_reference,
        "deployed_at": utc_now(),
    }


def write_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(state, indent=2, sort_keys=True) + "\n")


def prior_releases(
    current: dict[str, Any] | None,
    previous: list[dict[str, Any]],
    *,
    exclude_image: str | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if current:
        candidates.append(current)
    candidates.extend(previous)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        image = str(item.get("image") or "")
        if not image or image == exclude_image or image in seen:
            continue
        seen.add(image)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def validate_common(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if not args.compose_file.is_file():
        raise DeploymentError(f"Compose-Datei fehlt: {args.compose_file}")
    if not args.image_policy.is_file():
        raise DeploymentError(f"Image-Policy fehlt: {args.image_policy}")
    if not args.deployment_policy.is_file():
        raise DeploymentError(f"Deployment-Policy fehlt: {args.deployment_policy}")

    if not args.verify_url and not args.verify_exec:
        raise DeploymentError("--verify-url oder --verify-exec ist erforderlich.")

    policy = load_json(args.image_policy)
    deploy_policy = load_json(args.deployment_policy)

    if not hasattr(args, "image_env_key"):
        args.image_env_key = DEFAULT_IMAGE_ENV_KEY
    validate_image_env_key(args.image_env_key)
    default_image_env_key = str(
        (deploy_policy.get("state") or {}).get(
            "release_env_variable",
            DEFAULT_IMAGE_ENV_KEY,
        )
    )
    service_specific_keys_allowed = bool(
        (deploy_policy.get("state") or {}).get(
            "service_specific_release_env_variables_allowed",
            False,
        )
    )
    if (
        args.image_env_key != default_image_env_key
        and not service_specific_keys_allowed
    ):
        raise DeploymentError(
            "Service-spezifische Image-Environment-Keys sind laut Deployment-Policy nicht erlaubt."
        )

    if args.environment not in deploy_policy["approvals"]:
        raise DeploymentError(f"Unbekannte Umgebung: {args.environment}")
    approval = deploy_policy["approvals"][args.environment]
    if approval["approval_reference_required"] and not args.approval_reference:
        raise DeploymentError(
            f"{args.environment} benötigt eine Approval-Referenz."
        )

    data_rule = deploy_policy["data_changes"][args.data_change]
    if data_rule["backup_required"] and not args.backup_reference:
        raise DeploymentError(
            f"Datenänderung '{args.data_change}' benötigt eine Backup-Referenz."
        )
    if (
        args.rollback_mode == "automatic"
        and not data_rule["automatic_artifact_rollback_allowed"]
    ):
        raise DeploymentError(
            "Automatischer Artefakt-Rollback ist bei destruktiven Datenänderungen verboten."
        )
    if data_rule.get("restore_plan_required") and not args.restore_plan_reference:
        raise DeploymentError(
            "Destruktive Datenänderung benötigt eine Restore-Plan-Referenz."
        )

    return policy, deploy_policy


def automatic_rollback(
    args: argparse.Namespace,
    state: dict[str, Any],
    attempted_image: str,
    error: str,
) -> None:
    current = state.get("current")
    if not isinstance(current, dict) or not current.get("image"):
        state["last_attempt"] = {
            "status": "failed-no-known-good-version",
            "attempted_image": attempted_image,
            "error": error,
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise DeploymentError(
            "Deployment fehlgeschlagen und es existiert keine bekannte gute Rollback-Version."
        )

    rollback_image = str(current["image"])
    print(f"ROLLBACK: stelle bekannte gute Version wieder her: {rollback_image}")

    try:
        pull_image(rollback_image)
        deploy_image(args, rollback_image)
        rollback_verified = wait_for_verification(args, rollback_image)
    except DeploymentError as rollback_exc:
        state["last_attempt"] = {
            "status": "rollback-failed",
            "attempted_image": attempted_image,
            "rollback_image": rollback_image,
            "error": error,
            "rollback_error": str(rollback_exc),
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise DeploymentError(
            "Deployment ist fehlgeschlagen und der Rollback konnte nicht ausgeführt werden."
        ) from rollback_exc

    if not rollback_verified:
        state["last_attempt"] = {
            "status": "rollback-failed",
            "attempted_image": attempted_image,
            "rollback_image": rollback_image,
            "error": error,
            "rollback_error": "Rollback-Verifikation ist fehlgeschlagen.",
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise DeploymentError("Deployment und anschließender Rollback sind fehlgeschlagen.")

    state["last_attempt"] = {
        "status": "failed-rolled-back",
        "attempted_image": attempted_image,
        "rollback_image": rollback_image,
        "error": error,
        "finished_at": utc_now(),
    }
    write_state(args.state_file, state)
    raise DeploymentError(
        "Deployment-Verifikation fehlgeschlagen; bekannte gute Version wurde erfolgreich wiederhergestellt."
    )


def deploy(args: argparse.Namespace) -> int:
    image_policy, deploy_policy = validate_common(args)
    validate_image(args.target_image, image_policy)
    compose_config_for_image(args, args.target_image)

    print(f"PREFLIGHT: Zielimage {args.target_image}")
    pull_image(args.target_image)

    state = load_json(
        args.state_file,
        {
            "version": 1,
            "service": args.service,
            "project": args.project_name,
            "current": None,
            "previous": [],
        },
    )

    if state.get("service") not in (None, args.service):
        raise DeploymentError(
            f"State gehört zu anderem Service: {state.get('service')!r}"
        )
    if state.get("project") not in (None, args.project_name):
        raise DeploymentError(
            f"State gehört zu anderem Compose-Projekt: {state.get('project')!r}"
        )

    current = state.get("current")
    current_image = (
        str(current.get("image") or "") or None
        if isinstance(current, dict)
        else None
    )

    try:
        deploy_image(args, args.target_image)
        if not wait_for_verification(args, args.target_image):
            raise DeploymentError("Post-Deployment-Verifikation ist fehlgeschlagen.")
    except DeploymentError as exc:
        if args.rollback_mode == "automatic" and current_image:
            automatic_rollback(args, state, args.target_image, str(exc))

        state["last_attempt"] = {
            "status": "failed-manual-intervention-required",
            "attempted_image": args.target_image,
            "error": str(exc),
            "backup_reference": args.backup_reference,
            "restore_plan_reference": args.restore_plan_reference,
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise

    new_current = release_record(args, args.target_image)
    state["previous"] = prior_releases(
        current if isinstance(current, dict) else None,
        state.get("previous") or [],
        exclude_image=args.target_image,
        limit=int(deploy_policy["state"]["protected_previous_versions"]),
    )
    state["current"] = new_current
    state["last_attempt"] = {
        "status": "success",
        "attempted_image": args.target_image,
        "finished_at": utc_now(),
    }
    write_state(args.state_file, state)
    print(f"DEPLOYMENT: erfolgreich -> {args.target_image}")
    return 0


def rollback(args: argparse.Namespace) -> int:
    image_policy, deploy_policy = validate_common(args)
    state = load_json(args.state_file)
    current = state.get("current")
    previous = state.get("previous") or []

    if not isinstance(current, dict) or not current.get("image"):
        raise DeploymentError("Kein aktueller freigegebener Zustand vorhanden.")
    if not previous:
        raise DeploymentError("Keine vorherige bekannte gute Version vorhanden.")

    target = previous[0]
    target_image = str(target["image"])
    validate_image(target_image, image_policy)
    compose_config_for_image(args, target_image)
    try:
        pull_image(target_image)
        deploy_image(args, target_image)
        rollback_verified = wait_for_verification(args, target_image)
    except DeploymentError as exc:
        state["last_attempt"] = {
            "status": "manual-rollback-failed",
            "rollback_from": current["image"],
            "rollback_image": target_image,
            "error": str(exc),
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise

    if not rollback_verified:
        state["last_attempt"] = {
            "status": "manual-rollback-failed",
            "rollback_from": current["image"],
            "rollback_image": target_image,
            "error": "Rollback-Verifikation ist fehlgeschlagen.",
            "finished_at": utc_now(),
        }
        write_state(args.state_file, state)
        raise DeploymentError("Manueller Rollback konnte nicht erfolgreich verifiziert werden.")

    state["current"] = {
        **target,
        "deployed_at": utc_now(),
        "rollback_from": current["image"],
        "approval_reference": args.approval_reference,
    }
    state["previous"] = prior_releases(
        current,
        previous[1:],
        exclude_image=target_image,
        limit=int(deploy_policy["state"]["protected_previous_versions"]),
    )
    state["last_attempt"] = {
        "status": "manual-rollback-success",
        "rollback_from": current["image"],
        "rollback_image": target_image,
        "finished_at": utc_now(),
    }
    write_state(args.state_file, state)
    print(f"ROLLBACK: erfolgreich -> {target_image}")
    return 0


def status(args: argparse.Namespace) -> int:
    state = load_json(args.state_file)
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Kontrolliertes Digest-basiertes Compose Deployment."
    )
    parser.add_argument("action", choices=("deploy", "rollback", "status"))
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--project-name")
    parser.add_argument("--service")
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--release-env", type=Path)
    parser.add_argument(
        "--image-policy",
        type=Path,
        default=Path("configuration/container-image-policy.json"),
    )
    parser.add_argument(
        "--deployment-policy",
        type=Path,
        default=Path("configuration/deployment-policy.json"),
    )
    parser.add_argument(
        "--environment",
        choices=("development", "staging", "production"),
        default="development",
    )
    parser.add_argument("--target-image")
    parser.add_argument(
        "--image-env-key",
        default=DEFAULT_IMAGE_ENV_KEY,
        help=(
            "Environment-Variable, über die das Compose-Manifest den freigegebenen "
            "Image-Digest erhält."
        ),
    )
    parser.add_argument(
        "--data-change",
        choices=("none", "compatible", "destructive"),
        default="none",
    )
    parser.add_argument(
        "--rollback-mode",
        choices=("automatic", "manual"),
        default="automatic",
    )
    parser.add_argument("--backup-reference")
    parser.add_argument("--restore-plan-reference")
    parser.add_argument("--source-revision", default="unknown")
    parser.add_argument("--release-reference", default="unknown")
    parser.add_argument("--approval-reference")
    parser.add_argument("--verify-url")
    parser.add_argument("--verify-exec")
    parser.add_argument("--verify-arg", action="append", default=[])
    parser.add_argument("--verify-attempts", type=int, default=30)
    parser.add_argument("--verify-interval", type=float, default=1.0)
    parser.add_argument("--verify-timeout", type=float, default=2.0)
    parser.add_argument("--expected-status", type=int, default=200)
    return parser


def validate_required_args(args: argparse.Namespace) -> None:
    if args.action == "status":
        if args.state_file is None:
            raise DeploymentError("--state-file ist für status erforderlich.")
        return

    required = {
        "--compose-file": args.compose_file,
        "--project-name": args.project_name,
        "--service": args.service,
        "--state-file": args.state_file,
        "--release-env": args.release_env,
    }
    if args.action == "deploy":
        required["--target-image"] = args.target_image

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise DeploymentError(f"Fehlende Argumente: {', '.join(missing)}")

    if args.verify_attempts < 1:
        raise DeploymentError("--verify-attempts muss >= 1 sein.")
    if args.verify_interval < 0:
        raise DeploymentError("--verify-interval darf nicht negativ sein.")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_required_args(args)
        if args.action == "status":
            return status(args)

        assert args.state_file is not None
        lock_path = args.state_file.parent / ".deployment.lock"
        lock_path.parent.mkdir(parents=True, mode=0o750, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock_handle:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise DeploymentError(
                    f"Für {args.service} läuft bereits ein Deployment."
                ) from exc

            if args.action == "deploy":
                return deploy(args)
            if args.action == "rollback":
                return rollback(args)
            raise DeploymentError(f"Unbekannte Aktion: {args.action}")
    except DeploymentError as exc:
        print(f"DEPLOYMENT-FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
