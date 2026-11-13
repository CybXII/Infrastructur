#!/usr/bin/env python3
"""Send development E2E completion via the existing Alertmanager Discord egress."""
import datetime
import json
import subprocess
import sys

PROJECT = "merchfactory-development-prometheus"
ALERTMANAGER = "http://alertmanager:9093"


def prometheus_container():
    ids = subprocess.check_output([
        "docker", "ps", "-q",
        "--filter", "label=com.docker.compose.project=" + PROJECT,
        "--filter", "label=com.docker.compose.service=prometheus",
    ], text=True).splitlines()
    if len(ids) != 1:
        raise RuntimeError("Expected exactly one development Prometheus container")
    return ids[0]


def check(container):
    # The Prometheus container shares the monitoring network with Alertmanager.
    subprocess.run([
        "docker", "exec", container, "wget", "-q", "-O", "/dev/null",
        ALERTMANAGER + "/-/ready",
    ], check=True, timeout=20)


def main():
    check_only = sys.argv[1:] == ["--check"]
    if not check_only and (len(sys.argv) != 3 or sys.argv[1] not in ("SUCCESS", "FAILED")):
        raise SystemExit("usage: notify-backup-monitoring-e2e.py --check | SUCCESS|FAILED LOG_PATH")
    container = prometheus_container()
    check(container)
    if check_only:
        print("Alertmanager reachable through development monitoring network", flush=True)
        return

    status, path = sys.argv[1:]
    with open(path, encoding="utf-8", errors="replace") as stream:
        lines = stream.read().splitlines()
    passed = [line for line in lines if line.startswith("PASS:")]
    failures = [line for line in lines if "TimeoutError" in line or "ERROR" in line]
    detail = "; ".join(failures[-3:])[:700] if failures else "All four Prometheus transitions verified"
    now = datetime.datetime.now(datetime.timezone.utc)
    end = now + datetime.timedelta(minutes=3)
    payload = json.dumps([{
        "labels": {
            "alertname": "BackupMonitoringE2EReport",
            "environment": "development",
            "service": "monitoring-e2e",
            "severity": "info" if status == "SUCCESS" else "high",
            "backup": "synthetic-fixture",
        },
        "annotations": {
            "summary": "Backup Monitoring E2E (Development) - " + status,
            "description": ("; ".join(passed[-4:]) + " | " + detail)[:1500],
        },
        "startsAt": now.isoformat(),
        "endsAt": end.isoformat(),
    }], ensure_ascii=False)
    # This is a distinct completion notification, never a production backup alert.
    # Alertmanager already owns Discord egress; the host must not contact Discord.
    subprocess.run([
        "docker", "exec", container, "wget", "-q", "-O", "/dev/null",
        "--header=Content-Type: application/json",
        "--post-data=" + payload,
        ALERTMANAGER + "/api/v2/alerts",
    ], check=True, timeout=30)
    print("Submitted E2E " + status + " report to Alertmanager", flush=True)


if __name__ == "__main__":
    main()
