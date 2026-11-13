#!/usr/bin/env python3
"""Verify an internal monitoring Compose service without publishing a host port."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def fail(message: str) -> int:
    print(f"MONITORING-VERIFY-FEHLER: {message}", file=sys.stderr)
    return 1


def run_json(command: list[str]) -> object:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def main() -> int:
    if len(sys.argv) < 4:
        return fail(
            "Verwendung: verify-monitoring-service.py <network> <port> <readiness-path> [expected-status[,expected-status...]] [additional-network ...]"
        )

    network, port_raw, readiness_path = sys.argv[1:4]
    try:
        expected_statuses = {
            int(item.strip())
            for item in (sys.argv[4] if len(sys.argv) >= 5 else "200").split(",")
            if item.strip()
        }
    except ValueError:
        return fail("Erwartete HTTP-Statuscodes müssen numerisch sein.")
    if not expected_statuses:
        return fail("Mindestens ein erwarteter HTTP-Statuscode ist erforderlich.")
    try:
        port = int(port_raw)
    except ValueError:
        return fail("Port muss numerisch sein.")

    additional_networks = [item.strip() for item in sys.argv[5:] if item.strip()]
    allowed_networks = {network, *additional_networks}

    project = os.environ.get("DEPLOY_PROJECT", "").strip()
    service = os.environ.get("DEPLOY_SERVICE", "").strip()
    expected_image = os.environ.get("DEPLOY_IMAGE", "").strip()
    if not project or not service or not expected_image:
        return fail("DEPLOY_PROJECT, DEPLOY_SERVICE und DEPLOY_IMAGE sind erforderlich.")

    result = subprocess.run(
        [
            "docker",
            "ps",
            "-q",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--filter",
            f"label=com.docker.compose.service={service}",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(container_ids) != 1:
        return fail(
            f"Erwartet genau einen laufenden Container für {project}/{service}, "
            f"gefunden: {len(container_ids)}."
        )

    container = run_json(["docker", "inspect", container_ids[0]])[0]
    state = container.get("State") or {}
    if state.get("Running") is not True:
        return fail("Container läuft nicht.")
    health = (state.get("Health") or {}).get("Status")
    if health == "unhealthy":
        return fail("Container-Health ist unhealthy.")

    if (container.get("Config") or {}).get("Image") != expected_image:
        return fail("Laufender Container verwendet nicht den erwarteten Image-Digest.")

    port_bindings = (container.get("HostConfig") or {}).get("PortBindings")
    if port_bindings not in (None, {}):
        return fail(f"Interner Monitoring-Dienst besitzt Host-Portbindings: {port_bindings!r}")

    networks = (container.get("NetworkSettings") or {}).get("Networks") or {}
    if set(networks) != allowed_networks:
        return fail(
            "Unerwartete Netzwerkmitgliedschaften: "
            + ", ".join(sorted(networks))
        )

    ip_address = str((networks.get(network) or {}).get("IPAddress") or "").strip()
    if not ip_address:
        return fail(f"Keine Container-IP im Netzwerk {network} gefunden.")

    url = f"http://{ip_address}:{port}{readiness_path}"
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "merchfactory-monitoring-verifier/1"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            if response.status not in expected_statuses:
                return fail(f"Readiness lieferte HTTP {response.status}: {url}")
    except urllib.error.HTTPError as exc:
        if exc.code not in expected_statuses:
            return fail(f"Readiness lieferte HTTP {exc.code}: {url}")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return fail(f"Readiness nicht erreichbar: {url}: {exc}")

    print(
        f"MONITORING-VERIFY: {project}/{service} intern healthy, "
        f"ohne Host-Port und mit erwartetem Digest."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
