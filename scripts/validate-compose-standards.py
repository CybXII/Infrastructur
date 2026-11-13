#!/usr/bin/env python3
"""Validiert Compose-Manifeste gegen die Merchfactory-Service-Baseline."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

DIGEST_RE = re.compile(r"@sha256:[0-9a-fA-F]{64}$")
ALLOWED_RESTART = "unless-stopped"
MEMORY_RE = re.compile(r"^(\d+(?:\.\d+)?)([kmgt]i?b?|b)?$", re.IGNORECASE)


def parse_memory_bytes(value: object) -> int:
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip()
    match = MEMORY_RE.fullmatch(text)
    if not match:
        raise ValueError(f"Ungültiger Memory-Wert: {value!r}")

    number = float(match.group(1))
    unit = (match.group(2) or "b").lower()
    multipliers = {
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "mib": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "gib": 1024**3,
        "t": 1024**4,
        "tb": 1024**4,
        "tib": 1024**4,
    }
    return int(number * multipliers[unit])


def fail(message: str) -> None:
    print(f"FEHLER: {message}", file=sys.stderr)


def normalized_compose(path: Path) -> dict:
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(path), "config", "--format", "json"],
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        fail("docker wurde nicht gefunden; Compose-Validierung kann nicht ausgeführt werden.")
        raise SystemExit(2)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        fail(f"docker compose config ist für {path} fehlgeschlagen.")
        raise SystemExit(exc.returncode or 1)

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(f"docker compose lieferte kein gültiges JSON: {exc}")
        raise SystemExit(1)


def port_is_globally_bound(port: object) -> bool:
    if isinstance(port, str):
        value = port.strip()
        if value.startswith("127.0.0.1:") or value.startswith("[::1]:"):
            return False
        # Ein Eintrag ohne explizite Host-IP bindet standardmäßig global.
        return True

    if isinstance(port, dict):
        host_ip = str(port.get("host_ip") or "").strip()
        return host_ip not in {"127.0.0.1", "::1"}

    return True


def validate_service(name: str, service: dict) -> list[str]:
    errors: list[str] = []

    if "build" in service:
        errors.append(f"{name}: build ist im Deployment-Manifest nicht zulässig.")

    image = str(service.get("image") or "")
    if not image:
        errors.append(f"{name}: image fehlt.")
    elif not DIGEST_RE.search(image):
        errors.append(f"{name}: image muss per sha256-Digest unveränderlich gepinnt sein.")

    if "container_name" in service:
        errors.append(f"{name}: container_name ist nicht zulässig.")

    if service.get("restart") != ALLOWED_RESTART:
        errors.append(f"{name}: restart muss '{ALLOWED_RESTART}' sein.")

    labels = service.get("labels") or {}
    if not isinstance(labels, dict):
        errors.append(f"{name}: labels muss als Mapping definiert sein.")
    elif str(labels.get("com.merchfactory.managed") or "").lower() != "true":
        errors.append(
            f"{name}: Label com.merchfactory.managed=true fehlt."
        )

    if service.get("privileged") is True:
        errors.append(f"{name}: privileged=true ist verboten.")

    if service.get("network_mode") == "host":
        errors.append(f"{name}: network_mode=host ist verboten.")

    if service.get("read_only") is not True:
        errors.append(f"{name}: read_only=true fehlt.")

    cap_drop = {str(value).upper() for value in service.get("cap_drop") or []}
    if "ALL" not in cap_drop:
        errors.append(f"{name}: cap_drop muss ALL enthalten.")

    security_opt = {str(value).lower() for value in service.get("security_opt") or []}
    if "no-new-privileges:true" not in security_opt:
        errors.append(f"{name}: security_opt no-new-privileges:true fehlt.")

    try:
        cpus = float(service.get("cpus", 0))
    except (TypeError, ValueError):
        cpus = 0
    if cpus <= 0:
        errors.append(f"{name}: cpus muss als hartes CPU-Limit > 0 gesetzt sein.")

    try:
        cpu_shares = int(service.get("cpu_shares", 0))
    except (TypeError, ValueError):
        cpu_shares = 0
    if cpu_shares < 2:
        errors.append(f"{name}: cpu_shares muss als relative CPU-Priorität >= 2 gesetzt sein.")

    try:
        memory_limit = parse_memory_bytes(service.get("mem_limit", 0))
    except ValueError:
        memory_limit = 0
    if memory_limit <= 0:
        errors.append(f"{name}: mem_limit muss als hartes Memory-Limit gesetzt sein.")

    try:
        memory_reservation = parse_memory_bytes(service.get("mem_reservation", 0))
    except ValueError:
        memory_reservation = 0
    if memory_reservation <= 0:
        errors.append(f"{name}: mem_reservation muss als Memory-Soft-Limit gesetzt sein.")
    elif memory_limit > 0 and memory_reservation >= memory_limit:
        errors.append(f"{name}: mem_reservation muss kleiner als mem_limit sein.")

    try:
        pids_limit = int(service.get("pids_limit", 0))
    except (TypeError, ValueError):
        pids_limit = 0
    if pids_limit <= 0:
        errors.append(f"{name}: pids_limit muss positiv und begrenzt sein.")

    if service.get("oom_kill_disable") is True:
        errors.append(f"{name}: oom_kill_disable=true ist verboten.")

    if "logging" in service:
        errors.append(
            f"{name}: servicebezogene logging-Overrides sind in der Plattform-Baseline nicht zulässig."
        )

    healthcheck = service.get("healthcheck")
    if not isinstance(healthcheck, dict) or healthcheck.get("disable") is True:
        errors.append(f"{name}: aktiver healthcheck fehlt.")
    else:
        for key in ("test", "interval", "timeout", "retries", "start_period"):
            if key not in healthcheck:
                errors.append(f"{name}: healthcheck.{key} fehlt.")

    for port in service.get("ports") or []:
        if port_is_globally_bound(port):
            errors.append(
                f"{name}: veröffentlichter Port ist nicht explizit an localhost gebunden."
            )

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Verwendung: scripts/validate-compose-standards.py <compose-datei>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        fail(f"Compose-Datei existiert nicht: {path}")
        return 2

    document = normalized_compose(path)

    if "version" in document:
        fail("Top-Level-Feld version ist nicht zulässig.")
        return 1

    services = document.get("services")
    if not isinstance(services, dict) or not services:
        fail("Keine Services im Compose-Manifest gefunden.")
        return 1

    errors: list[str] = []
    for name, service in services.items():
        if not isinstance(service, dict):
            errors.append(f"{name}: ungültige Service-Definition.")
            continue
        errors.extend(validate_service(name, service))

    if errors:
        for error in errors:
            fail(error)
        return 1

    print(f"Compose-Standard erfüllt: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
