#!/usr/bin/env python3
"""Safe development-only backup telemetry probe.

Writes a dedicated synthetic .prom fixture; never modifies real backup files.
No direct alert injection, no production support.
"""
import argparse
import grp
import os
from pathlib import Path
import sys
import tempfile
import time

FILENAME = "merchfactory-backup-e2e-test.prom"
SERVICE = "monitoring-e2e-test"
BACKUP = "synthetic-fixture"
METRICS_GROUP = "merchfactory-backup-metrics"

def metrics(status: int, now: int, stale: bool = False, restore_failed: bool = False, restore_stale: bool = False) -> str:
    labels = '{service="%s",backup="%s"}' % (SERVICE, BACKUP)
    last_ok = now - (7200 if stale else 60)
    return "\n".join([
        "# HELP merchfactory_backup_last_success Last backup execution result",
        "# TYPE merchfactory_backup_last_success gauge",
        f"merchfactory_backup_last_success{labels} {status}",
        f"merchfactory_backup_last_run_timestamp_seconds{labels} {now}",
        f"merchfactory_backup_last_success_timestamp_seconds{labels} {last_ok}",
        f"merchfactory_backup_max_age_seconds{labels} 3600",
        f"merchfactory_backup_duration_seconds{labels} 2",
        f"merchfactory_backup_size_bytes{labels} 1024",
        f"merchfactory_backup_restore_test_last_success{labels} {0 if restore_failed else 1}",
        f"merchfactory_backup_restore_test_last_run_timestamp_seconds{labels} {now}",
        f"merchfactory_backup_restore_test_last_success_timestamp_seconds{labels} {now - (172800 if restore_stale else 60)}",
        f"merchfactory_backup_restore_test_max_age_seconds{labels} 86400",
        "",
    ])

def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["success", "failure", "stale", "restore-failure", "restore-stale", "cleanup"])
    p.add_argument("--directory", required=True, type=Path)
    p.add_argument("--environment", required=True, choices=["development"])
    a = p.parse_args()
    directory = a.directory.resolve(strict=True)
    if not directory.is_dir() or directory.is_symlink():
        p.error("Metric directory must be a real existing directory")
    destination = directory / FILENAME
    if destination.is_symlink():
        p.error("Refusing symlink destination")
    if a.action == "cleanup":
        destination.unlink(missing_ok=True)
        print("Removed synthetic backup fixture")
        return
    status = 0 if a.action == "failure" else 1
    payload = metrics(status, int(time.time()), stale=a.action == "stale", restore_failed=a.action == "restore-failure", restore_stale=a.action == "restore-stale")
    fd, name = tempfile.mkstemp(prefix=".backup-e2e-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o640)
            os.fchown(f.fileno(), -1, grp.getgrnam(METRICS_GROUP).gr_gid)
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, destination)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"Published {a.action} synthetic metrics to {destination}")

if __name__ == "__main__":
    main()
