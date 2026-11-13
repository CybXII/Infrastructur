#!/usr/bin/env python3
"""Render the standard container-service template with explicit placeholders."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
SERVICE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z]{2,63}$"
)
DIGEST_RE = re.compile(r"^[^@\s]+@sha256:[0-9a-fA-F]{64}$")
READINESS_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")


def parse_sets(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"--set erwartet KEY=VALUE: {value}")
        key, item_value = value.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"Ungültiger Platzhaltername: {key}")
        if not item_value:
            raise ValueError(f"Leerer Platzhalterwert: {key}")
        result[key] = item_value
    return result


def validate_values(values: dict[str, str]) -> None:
    service = values.get("SERVICE_NAME", "")
    if service and not SERVICE_RE.fullmatch(service):
        raise ValueError("SERVICE_NAME muss kebab-case ohne führenden/abschließenden Bindestrich sein.")

    hostname = values.get("PUBLIC_HOSTNAME", "")
    if hostname and not HOST_RE.fullmatch(hostname):
        raise ValueError("PUBLIC_HOSTNAME ist kein gültiger DNS-Hostname.")

    image = values.get("IMAGE_REFERENCE", "")
    if image and not DIGEST_RE.fullmatch(image):
        raise ValueError("IMAGE_REFERENCE muss eine vollständige sha256-Digest-Referenz sein.")

    readiness_path = values.get("READINESS_PATH", "")
    if readiness_path and not READINESS_PATH_RE.fullmatch(readiness_path):
        raise ValueError(
            "READINESS_PATH muss ein absoluter HTTP-Pfad ohne Query oder Fragment sein."
        )

    port = values.get("CONTAINER_PORT", "")
    if port:
        try:
            numeric_port = int(port)
        except ValueError as exc:
            raise ValueError("CONTAINER_PORT muss numerisch sein.") from exc
        if not 1 <= numeric_port <= 65535:
            raise ValueError("CONTAINER_PORT muss zwischen 1 und 65535 liegen.")

    for key in ("SERVICE_UID", "SERVICE_GID"):
        if key in values and not values[key].isdigit():
            raise ValueError(f"{key} muss numerisch sein.")


def render_text(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        return values[key]

    return PLACEHOLDER_RE.sub(replace, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rendert das Standard-Service-Template.")
    parser.add_argument(
        "--template-root",
        type=Path,
        default=Path("templates/services/container-service"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--set", action="append", default=[], dest="sets")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    template_root = args.template_root.resolve()
    manifest_path = template_root / "template.json"

    if not manifest_path.is_file():
        print(f"Template-Manifest fehlt: {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = set(manifest["placeholders"])
    values = parse_sets(args.sets)
    validate_values(values)

    missing = sorted(required - values.keys())
    extra = sorted(values.keys() - required)
    if missing:
        print(f"Fehlende Platzhalter: {', '.join(missing)}", file=sys.stderr)
        return 2
    if extra:
        print(f"Unbekannte Platzhalter: {', '.join(extra)}", file=sys.stderr)
        return 2

    output = args.output.resolve()
    if output.exists():
        if not args.force:
            print(f"Ziel existiert bereits: {output}", file=sys.stderr)
            return 2
        shutil.rmtree(output)

    output.mkdir(parents=True)

    unresolved: list[str] = []

    for source in sorted(template_root.rglob("*")):
        if not source.is_file() or source.name == "template.json":
            continue

        relative = source.relative_to(template_root)
        target_name = relative.name.removesuffix(".template")
        target = output / relative.parent / target_name
        target.parent.mkdir(parents=True, exist_ok=True)

        text = source.read_text(encoding="utf-8")
        rendered = render_text(text, values)
        found = sorted(set(PLACEHOLDER_RE.findall(rendered)))
        if found:
            unresolved.append(f"{relative}: {', '.join(found)}")

        target.write_text(rendered, encoding="utf-8")

    if unresolved:
        shutil.rmtree(output)
        print("Unaufgelöste Platzhalter:", file=sys.stderr)
        for item in unresolved:
            print(f"- {item}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
