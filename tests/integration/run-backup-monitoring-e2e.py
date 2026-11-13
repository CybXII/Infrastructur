#!/usr/bin/env python3
"""Development-only sequential Prometheus backup alert E2E verification.

Requires an explicitly supplied, locally reachable Prometheus URL. This verifies
Prometheus state transitions, NOT delivery to Discord. Never run in production.
"""
import argparse
import os
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CASES = (
    ("failure", "BackupJobFailed", 5 * 60),
    ("stale", "BackupTooOld", 15 * 60),
    ("restore-failure", "RestoreTestFailed", 15 * 60),
    ("restore-stale", "RestoreTestTooOld", 60 * 60),
)
BACKUP = "synthetic-fixture"


def alert_state(base_url, name):
    expression = (
        'ALERTS{alertname="%s",backup="%s",'
        'alertstate="firing"}' % (name, BACKUP)
    )
    url = base_url.rstrip("/") + "/api/v1/query?" + urllib.parse.urlencode({"query": expression})
    if base_url == "docker-prometheus":
        containers = subprocess.check_output(
            ["docker", "ps", "-q", "--filter", "label=com.docker.compose.project=merchfactory-development-prometheus",
             "--filter", "label=com.docker.compose.service=prometheus"], text=True
        ).splitlines()
        if len(containers) != 1:
            raise RuntimeError("Expected exactly one development Prometheus container")
        local_url = "http://127.0.0.1:9090/api/v1/query?" + urllib.parse.urlencode({"query": expression})
        output = subprocess.check_output(
            ["docker", "exec", containers[0], "wget", "-q", "-O", "-", local_url], timeout=15
        )
        payload = json.loads(output)
    else:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = json.load(response)
    if payload.get("status") != "success":
        raise RuntimeError("Prometheus query failed")
    # The scrape target overrides service, but the synthetic backup label is stable.
    return bool(payload["data"]["result"])


def wait_state(base_url, name, expected, timeout, interval):
    deadline = time.monotonic() + timeout
    while True:
        if alert_state(base_url, name) == expected:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("%s did not reach firing=%s within %ss" % (name, expected, timeout))
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=["development"], required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--prometheus-url", required=True, help="Local Prometheus URL, e.g. http://127.0.0.1:9090")
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--grace-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.poll_seconds < 1 or args.grace_seconds < 1:
        parser.error("Polling and grace intervals must be positive")
    parsed = urllib.parse.urlparse(args.prometheus_url)
    if args.prometheus_url != "docker-prometheus" and (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1")):
        parser.error("Only local HTTP Prometheus endpoints are allowed")
    fixture = Path(__file__).with_name("backup-monitoring-e2e.py")
    destination = args.directory / "merchfactory-backup-e2e-test.prom"
    if destination.exists() or destination.is_symlink():
        parser.error("Existing synthetic fixture: refusing to overwrite")

    def publish(action):
        subprocess.run(
            [sys.executable, str(fixture), action, "--directory", str(args.directory),
             "--environment", args.environment], check=True
        )

    try:
        for action, name, duration in CASES:
            print("Testing %s (%s)" % (name, action), flush=True)
            publish("success")
            wait_state(args.prometheus_url, name, False, args.grace_seconds, args.poll_seconds)
            publish(action)
            wait_state(args.prometheus_url, name, True, duration + args.grace_seconds, args.poll_seconds)
            publish("success")
            wait_state(args.prometheus_url, name, False, args.grace_seconds, args.poll_seconds)
            print("PASS: %s FIRING -> RESOLVED in Prometheus" % name, flush=True)
        print("PASS: all four Prometheus alert transitions verified", flush=True)
    finally:
        publish("cleanup")


if __name__ == "__main__":
    main()
