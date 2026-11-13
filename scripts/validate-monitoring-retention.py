#!/usr/bin/env python3
"""Read-only #96 retention contract audit; never modifies retention or stored data."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3
MIB = 1024 ** 2


def estimated_metric_gib(series: int, interval_seconds: int, days: int, bytes_per_sample: float) -> float:
    """TSDB sample payload estimate only (excludes WAL, head, index and filesystem overhead)."""
    if min(series, interval_seconds, days) <= 0 or bytes_per_sample <= 0:
        raise ValueError("all metric estimate parameters must be positive")
    return (series * (86400 / interval_seconds) * days * bytes_per_sample) / GIB


def estimated_loki_gib(daily_ingested_mib: float, days: int) -> float:
    """Illustrative stored MiB/day forecast; includes no index/compactor overhead."""
    if daily_ingested_mib < 0 or days <= 0:
        raise ValueError("log estimate parameters must be nonnegative, days positive")
    return daily_ingested_mib * days / 1024


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    config = root / "configuration"
    logging = json.loads((config / "logging-policy.json").read_text(encoding="utf-8"))
    monitoring = json.loads((config / "monitoring-stack.json").read_text(encoding="utf-8"))
    prom = (root / "deployment/monitoring/prometheus/compose.yaml").read_text(encoding="utf-8")
    loki = (root / "monitoring/loki/loki.yaml").read_text(encoding="utf-8")
    node = (root / "monitoring/prometheus/rules/node-exporter.yml").read_text(encoding="utf-8")

    metrics = monitoring["metrics"]
    logs = monitoring["logs"]
    loki_component = monitoring["components"]["loki"]
    central = logging["central_retention"]
    classes = {
        "debug_days": 7, "standard_days": 30, "error_days": 90,
        "security_days": 365, "audit_days": 365, "deployment_backup_days": 365,
    }

    for key, value in classes.items():
        if central.get(key) != value:
            errors.append(f"central retention drift: {key} should be {value} days")

    if metrics.get("raw_retention_baseline") != "30d" or "--storage.tsdb.retention.time=${PROMETHEUS_RETENTION_TIME:-30d}" not in prom:
        errors.append("Prometheus 30-day runtime retention mismatch")
    if metrics.get("raw_retention_size_baseline") != "8GiB" or "--storage.tsdb.retention.size=${PROMETHEUS_RETENTION_SIZE:-8GiB}" not in prom:
        errors.append("Prometheus 8-GiB runtime size-retention mismatch")
    if metrics.get("retention_size_cap_required") is not True:
        errors.append("Prometheus size retention must remain enabled")

    if (logs.get("development_retention_baseline") != "168h"
            or loki_component.get("retention_period") != "168h"
            or not re.search(r"(?m)^\s*retention_period:\s*168h\s*$", loki)):
        errors.append("Loki development 168h retention mismatch")
    if not re.search(r"(?m)^\s*retention_enabled:\s*true\s*$", loki):
        errors.append("Loki compactor retention is not enabled")
    if not re.search(r"(?m)^\s*retention_delete_delay:\s*2h\s*$", loki):
        errors.append("Loki delayed deletion changed: review retention lifecycle")
    if logs.get("development_capacity_target") != "4GiB" or logs.get("capacity_target_is_hard_limit") is not False:
        errors.append("Loki 4-GiB target is NOT an enforced filesystem quota")

    disk = logging["disk_alerting"]
    if disk.get("warning_percent") != 75 or disk.get("critical_percent") != 85:
        errors.append("Host disk capacity thresholds should be 75/85 percent")
    if "HostFilesystemSpaceLow" not in node:
        errors.append("Node Exporter host filesystem alert missing")
    container = logging["container_logs"]
    if (container.get("driver") != "local" or container.get("max_size") != "20m"
            or container.get("max_files") != 5):
        errors.append("local Docker rotation baseline mismatch")
    journal = logging["system_journal"]
    if journal.get("system_max_use") != "512M" or journal.get("max_retention_sec") != "30day":
        errors.append("journald rotation baseline mismatch")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline monitoring retention verification and capacity estimates")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--series", type=int, default=5000, help="illustrative active metric series")
    parser.add_argument("--scrape-seconds", type=int, default=30)
    parser.add_argument("--bytes-per-sample", type=float, default=2.0)
    parser.add_argument("--daily-loki-mib", type=float, default=100.0,
                        help="illustrative Loki disk growth, not raw log bytes")
    args = parser.parse_args()
    failures = validate(args.root)
    if failures:
        for problem in failures:
            print(f"ERROR: {problem}")
        return 1
    try:
        prom = estimated_metric_gib(args.series, args.scrape_seconds, 30, args.bytes_per_sample)
        loki = estimated_loki_gib(args.daily_loki_mib, 7)
    except ValueError as exc:
        parser.error(str(exc))
    print("Retention contract: OK (static config only; no VPS measurement)")
    print(f"Prometheus 30d sample payload estimate: {prom:.2f} GiB; WAL/head/index NOT included")
    print(f"Loki 7d disk-growth estimate: {loki:.2f} GiB; index/compactor overhead NOT included")
    print("Runtime usage, actual cardinality and peak log ingestion must be verified on Development.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
