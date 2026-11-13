#!/usr/bin/env python3
"""Safe Docker retention cleanup for the Merchfactory container platform."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_POLICY = Path("configuration/docker-cleanup-policy.json")
DEFAULT_IMAGE_POLICY = Path("configuration/container-image-policy.json")
DEFAULT_LOCK = Path("/run/lock/merchfactory-docker-cleanup.lock")


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text or text.startswith("0001-"):
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def run(command: list[str], *, check: bool = True) -> CommandResult:
    proc = subprocess.run(command, text=True, capture_output=True)
    result = CommandResult(proc.returncode, proc.stdout, proc.stderr)
    if check and proc.returncode != 0:
        raise CleanupError(
            f"Befehl fehlgeschlagen ({proc.returncode}): {' '.join(command)}\n"
            f"{proc.stderr.strip()}"
        )
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CleanupError(f"JSON kann nicht gelesen werden ({path}): {exc}") from exc
    if not isinstance(document, dict):
        raise CleanupError(f"JSON-Objekt erwartet: {path}")
    return document


def atomic_write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o640)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def canonical_repository(ref: str) -> str | None:
    value = ref.strip()
    if not value or value in ("<none>", "<none>:<none>"):
        return None

    if "@" in value:
        name = value.split("@", 1)[0]
    else:
        slash = value.rfind("/")
        colon = value.rfind(":")
        name = value[:colon] if colon > slash else value

    parts = name.split("/")
    first = parts[0]
    if "." in first or ":" in first or first == "localhost":
        registry = first.lower()
        repository_parts = parts[1:]
    else:
        registry = "docker.io"
        repository_parts = parts

    if not repository_parts:
        return None
    if registry == "docker.io" and len(repository_parts) == 1:
        repository_parts = ["library", repository_parts[0]]

    return f"{registry}/{'/'.join(repository_parts)}".lower()


def allowed_repositories(image_policy: dict[str, Any]) -> tuple[str, set[str]]:
    first_party = image_policy["first_party"]
    prefix = (
        f"{str(first_party['registry']).lower()}/"
        f"{str(first_party['namespace']).lower()}/"
    )
    third_party = {
        str(item["repository"]).lower()
        for item in image_policy.get("third_party", [])
        if isinstance(item, dict) and item.get("repository")
    }
    return prefix, third_party


def repository_is_allowed(
    repository: str | None,
    first_party_prefix: str,
    third_party: set[str],
) -> bool:
    if repository is None:
        return False
    return repository.startswith(first_party_prefix) or repository in third_party


def docker_json(command: list[str]) -> Any:
    result = run(command)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CleanupError(
            f"Docker lieferte ungültiges JSON: {' '.join(command)}"
        ) from exc


def inspect_containers() -> list[dict[str, Any]]:
    ids = [
        line.strip()
        for line in run(["docker", "ps", "-aq", "--no-trunc"]).stdout.splitlines()
        if line.strip()
    ]
    if not ids:
        return []
    document = docker_json(["docker", "inspect", *ids])
    if not isinstance(document, list):
        raise CleanupError("docker inspect Container lieferte keine Liste.")
    return document


def inspect_images() -> list[dict[str, Any]]:
    ids = [
        line.strip()
        for line in run(["docker", "image", "ls", "-aq", "--no-trunc"]).stdout.splitlines()
        if line.strip()
    ]
    ids = list(dict.fromkeys(ids))
    if not ids:
        return []
    document = docker_json(["docker", "image", "inspect", *ids])
    if not isinstance(document, list):
        raise CleanupError("docker image inspect lieferte keine Liste.")
    return document


def scan_release_states(
    state_root: Path,
    stable_statuses: set[str],
    protected_previous_versions: int,
) -> tuple[set[str], list[str], list[dict[str, Any]]]:
    protected_refs: set[str] = set()
    blockers: list[str] = []
    states: list[dict[str, Any]] = []

    if not state_root.exists():
        return protected_refs, blockers, states

    for path in sorted(state_root.glob("*/state.json")):
        document = load_json(path)
        states.append({"path": str(path), "state": document})

        current = document.get("current")
        if isinstance(current, dict) and current.get("image"):
            protected_refs.add(str(current["image"]))

        previous = document.get("previous") or []
        if isinstance(previous, list):
            for item in previous[:protected_previous_versions]:
                if isinstance(item, dict) and item.get("image"):
                    protected_refs.add(str(item["image"]))

        last_attempt = document.get("last_attempt")
        status = (
            str(last_attempt.get("status"))
            if isinstance(last_attempt, dict) and last_attempt.get("status")
            else None
        )
        if status not in stable_statuses:
            blockers.append(
                f"{path}: last_attempt.status={status!r} ist nicht cleanup-stabil."
            )

        lock_path = path.parent / ".deployment.lock"
        if lock_path.exists():
            with lock_path.open("a+", encoding="utf-8") as lock_handle:
                try:
                    fcntl.flock(
                        lock_handle.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                except BlockingIOError:
                    blockers.append(
                        f"{lock_path}: Deployment-Lock ist aktiv."
                    )
                else:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    return protected_refs, blockers, states


def image_ids_for_refs(refs: set[str]) -> tuple[set[str], list[str]]:
    protected_ids: set[str] = set()
    unresolved: list[str] = []
    for ref in sorted(refs):
        result = run(["docker", "image", "inspect", ref], check=False)
        if result.returncode != 0:
            unresolved.append(ref)
            continue
        try:
            document = json.loads(result.stdout)
            protected_ids.add(str(document[0]["Id"]))
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            unresolved.append(ref)
    return protected_ids, unresolved


def age_at_least(timestamp: datetime | None, cutoff: datetime) -> bool:
    return timestamp is not None and timestamp <= cutoff


def build_plan(
    *,
    policy: dict[str, Any],
    image_policy: dict[str, Any],
    state_root: Path,
    now: datetime,
) -> dict[str, Any]:
    scope = policy["scope"]
    retention = policy["retention"]
    deployment = policy["deployment_state"]
    safety = policy["safety"]

    stable_statuses = set(deployment["stable_last_attempt_statuses"])
    protected_refs, state_blockers, states = scan_release_states(
        state_root,
        stable_statuses,
        int(deployment["protected_previous_versions"]),
    )

    if (
        safety["require_stable_deployment_state"]
        and not states
        and not scope["cleanup_allowed_without_release_state"]
    ):
        state_blockers.append(
            f"{state_root}: kein erfolgreicher Release-State vorhanden."
        )

    protected_image_ids, unresolved_refs = image_ids_for_refs(protected_refs)

    containers = inspect_containers()
    managed_label = str(scope["managed_container_label"])
    managed_value = str(scope["managed_container_value"])
    protect_label = str(scope["protected_container_label"])
    protect_value = str(scope["protected_container_value"])

    container_cutoff = now - timedelta(
        days=float(retention["stopped_managed_containers_days"])
    )

    remove_containers: list[dict[str, Any]] = []
    remaining_container_image_ids: set[str] = set()
    running_image_ids: set[str] = set()

    for container in containers:
        state = container.get("State") or {}
        labels = (container.get("Config") or {}).get("Labels") or {}
        image_id = str(container.get("Image") or "")
        container_id = str(container.get("Id") or "")
        name = str(container.get("Name") or "").lstrip("/")
        running = state.get("Running") is True
        status = str(state.get("Status") or "")
        managed = str(labels.get(managed_label) or "").lower() == managed_value.lower()
        protected = str(labels.get(protect_label) or "").lower() == protect_value.lower()

        if running:
            if image_id:
                running_image_ids.add(image_id)
                remaining_container_image_ids.add(image_id)
            continue

        finished = parse_timestamp(state.get("FinishedAt"))
        created = parse_timestamp(container.get("Created"))
        timestamp = finished or created

        eligible = (
            managed
            and not protected
            and status in {"created", "exited", "dead"}
            and age_at_least(timestamp, container_cutoff)
        )
        if eligible:
            remove_containers.append(
                {
                    "id": container_id,
                    "name": name,
                    "status": status,
                    "image_id": image_id,
                    "timestamp": timestamp.isoformat() if timestamp else None,
                }
            )
        elif image_id:
            remaining_container_image_ids.add(image_id)

    all_protected_ids = (
        protected_image_ids
        | running_image_ids
        | remaining_container_image_ids
    )

    first_party_prefix, third_party = allowed_repositories(image_policy)
    unused_cutoff = now - timedelta(days=float(retention["unused_allowed_images_days"]))
    dangling_cutoff = now - timedelta(days=float(retention["dangling_images_days"]))

    remove_images: list[dict[str, Any]] = []

    for image in inspect_images():
        image_id = str(image.get("Id") or "")
        if not image_id or image_id in all_protected_ids:
            continue

        created = parse_timestamp(image.get("Created"))
        repo_tags = [
            str(item)
            for item in (image.get("RepoTags") or [])
            if item and str(item) != "<none>:<none>"
        ]
        repo_digests = [
            str(item)
            for item in (image.get("RepoDigests") or [])
            if item and str(item) != "<none>@<none>"
        ]

        references = repo_digests + repo_tags
        repositories = {
            repo
            for repo in (canonical_repository(ref) for ref in references)
            if repo
        }

        dangling = not repo_tags and not repo_digests
        allowed = any(
            repository_is_allowed(repo, first_party_prefix, third_party)
            for repo in repositories
        )

        reason: str | None = None
        if dangling and age_at_least(created, dangling_cutoff):
            reason = "dangling"
        elif allowed and age_at_least(created, unused_cutoff):
            reason = "unused-allowed-repository"

        if reason:
            remove_images.append(
                {
                    "id": image_id,
                    "created": created.isoformat() if created else None,
                    "reason": reason,
                    "repositories": sorted(repositories),
                    "references": references,
                }
            )

    return {
        "version": 1,
        "generated_at": now.isoformat(),
        "cleanup_allowed": not state_blockers,
        "blockers": state_blockers,
        "deployment_states": [item["path"] for item in states],
        "protected_image_references": sorted(protected_refs),
        "protected_image_ids": sorted(protected_image_ids),
        "unresolved_protected_image_references": unresolved_refs,
        "running_image_ids": sorted(running_image_ids),
        "containers": {
            "remove": remove_containers,
            "count": len(remove_containers),
        },
        "images": {
            "remove": remove_images,
            "count": len(remove_images),
        },
        "build_cache": {
            "command": [
                "docker",
                "builder",
                "prune",
                "--force",
                "--filter",
                f"until={retention['build_cache_retention']}",
            ],
            "retention": str(retention["build_cache_retention"]),
            "executed": False,
        },
        "volumes": {
            "action": "none",
            "reason": "Automatisches Volume-Pruning ist verboten.",
        },
    }


def apply_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for item in plan["containers"]["remove"]:
        result = run(["docker", "container", "rm", item["id"]], check=False)
        if result.returncode != 0:
            errors.append(
                f"Container {item['name'] or item['id']} konnte nicht entfernt werden: "
                f"{result.stderr.strip()}"
            )

    for item in plan["images"]["remove"]:
        result = run(["docker", "image", "rm", item["id"]], check=False)
        if result.returncode != 0:
            errors.append(
                f"Image {item['id']} konnte nicht entfernt werden: "
                f"{result.stderr.strip()}"
            )

    command = list(plan["build_cache"]["command"])
    result = run(command, check=False)
    plan["build_cache"]["executed"] = True
    plan["build_cache"]["returncode"] = result.returncode
    plan["build_cache"]["stdout"] = result.stdout.strip()
    plan["build_cache"]["stderr"] = result.stderr.strip()
    if result.returncode != 0:
        errors.append(
            f"Build-Cache-Cleanup fehlgeschlagen: {result.stderr.strip()}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sicheres Docker-Retention-Cleanup mit Rollback-Schutz."
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY,
    )
    parser.add_argument(
        "--image-policy",
        type=Path,
        default=DEFAULT_IMAGE_POLICY,
    )
    parser.add_argument(
        "--deployment-state-root",
        type=Path,
    )
    parser.add_argument(
        "--report",
        type=Path,
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=DEFAULT_LOCK,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Cleanup tatsächlich ausführen. Ohne --apply nur Dry-Run.",
    )
    args = parser.parse_args()

    try:
        policy = load_json(args.policy)
        image_policy = load_json(args.image_policy)

        state_root = (
            args.deployment_state_root
            if args.deployment_state_root
            else Path(policy["deployment_state"]["root"])
        )

        args.lock_file.parent.mkdir(parents=True, exist_ok=True)
        with args.lock_file.open("a+", encoding="utf-8") as lock_handle:
            try:
                fcntl.flock(
                    lock_handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError as exc:
                raise CleanupError("Ein Docker-Cleanup läuft bereits.") from exc

            plan = build_plan(
                policy=policy,
                image_policy=image_policy,
                state_root=state_root,
                now=now_utc(),
            )
            plan["mode"] = "apply" if args.apply else "dry-run"

            if args.apply and not plan["cleanup_allowed"]:
                plan["status"] = "skipped-safety-gate"
                if args.report:
                    atomic_write(args.report, plan)
                print(json.dumps(plan, indent=2, sort_keys=True))
                return 0

            if args.apply:
                errors = apply_plan(plan)
                plan["errors"] = errors
                plan["status"] = "failed" if errors else "success"
            else:
                plan["errors"] = []
                plan["status"] = "dry-run"

            if args.report:
                atomic_write(args.report, plan)

            print(json.dumps(plan, indent=2, sort_keys=True))
            return 1 if plan["errors"] else 0

    except CleanupError as exc:
        print(f"CLEANUP-FEHLER: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
