#!/usr/bin/env python3
"""Validate container image references against the Merchfactory registry policy."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DIGEST_RE = re.compile(r"@sha256:([0-9a-fA-F]{64})$")


def fail(message: str) -> None:
    print(f"FEHLER: {message}", file=sys.stderr)


def load_policy(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Image-Policy fehlt: {path}")
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        fail(f"Image-Policy ist ungültiges JSON: {exc}")
        raise SystemExit(2)


def normalized_compose(paths: list[Path]) -> dict[str, Any]:
    command = ["docker", "compose"]
    for path in paths:
        command.extend(["-f", str(path)])
    command.extend(["config", "--format", "json"])

    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        fail("docker wurde nicht gefunden; Image-Policy kann nicht validiert werden.")
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        fail("docker compose config ist fehlgeschlagen.")
        raise SystemExit(exc.returncode or 1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"docker compose lieferte kein gültiges JSON: {exc}")
        raise SystemExit(1)


def canonical_repository(image: str) -> tuple[str, str]:
    if "@" not in image:
        name_part = image
    else:
        name_part = image.split("@", 1)[0]

    slash = name_part.rfind("/")
    colon = name_part.rfind(":")
    if colon > slash:
        name_part = name_part[:colon]

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

    repository = f"{registry}/{'/'.join(repository_parts)}".lower()
    return registry, repository


def classify_image(image: str, policy: dict[str, Any]) -> tuple[str, str]:
    first_party = policy["first_party"]
    _, repository = canonical_repository(image)

    first_party_prefix = (
        f"{first_party['registry'].lower()}/"
        f"{first_party['namespace'].lower()}/"
    )
    if repository.startswith(first_party_prefix):
        return "first-party", repository

    third_party = {
        item["repository"].lower(): item
        for item in policy.get("third_party", [])
    }
    if repository in third_party:
        return "third-party", repository

    return "forbidden", repository


def validate_images(document: dict[str, Any], policy: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    errors: list[str] = []
    inventory: list[dict[str, str]] = []

    for service_name, service in sorted((document.get("services") or {}).items()):
        image = str(service.get("image") or "").strip()
        if not image:
            errors.append(f"{service_name}: image fehlt.")
            continue

        digest_match = DIGEST_RE.search(image)
        if not digest_match:
            errors.append(
                f"{service_name}: Image muss mit vollständigem sha256-Digest gepinnt sein."
            )

        name_part = image.split("@", 1)[0]
        first_component = name_part.split("/", 1)[0]
        if not (
            "." in first_component
            or ":" in first_component
            or first_component == "localhost"
        ):
            errors.append(
                f"{service_name}: Registry muss explizit im Image-Namen angegeben werden."
            )

        classification, repository = classify_image(image, policy)
        if classification == "forbidden":
            errors.append(
                f"{service_name}: Image-Quelle ist nicht allowgelistet: {repository}"
            )

        inventory.append(
            {
                "service": service_name,
                "image": image,
                "repository": repository,
                "classification": classification,
            }
        )

    return errors, inventory


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validiert Compose-Images gegen die Merchfactory Registry-Policy."
    )
    parser.add_argument(
        "compose_files",
        nargs="+",
        type=Path,
        help="Compose-Datei(en), die gemeinsam normalisiert werden.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("configuration/container-image-policy.json"),
        help="Pfad zur Registry-/Image-Policy.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Validiertes Image-Inventar als JSON ausgeben.",
    )
    args = parser.parse_args()

    policy = load_policy(args.policy)
    document = normalized_compose(args.compose_files)
    errors, inventory = validate_images(document, policy)

    if errors:
        for error in errors:
            fail(error)
        return 1

    if args.json:
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        for item in inventory:
            print(
                f"IMAGE-POLICY: {item['service']} -> "
                f"{item['repository']} ({item['classification']})"
            )
        print("IMAGE-POLICY: alle Image-Referenzen entsprechen der Policy.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
