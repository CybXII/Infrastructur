#!/usr/bin/env python3
"""Read-only, reproducible Development disk snapshots for monitoring issue #96.

The reported 'allocated_bytes' counts filesystem blocks (st_blocks*512),
similar to du; it does NOT prove retention, account for shared/reflink blocks,
or measure ingestion volume. Never deletes or alters monitoring data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import stat
from pathlib import Path

GIB = 1024 ** 3
MIB = 1024 ** 2
SCHEMA = "merchfactory-monitoring-capacity-v1"
STORES = ("prometheus", "loki")
DEFAULT_DATA_ROOT = Path("/srv/merchfactory/persistent/monitoring")
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]


def contract(repo_root: Path) -> dict:
    monitoring = json.loads((repo_root / "configuration/monitoring-stack.json").read_text())
    logging = json.loads((repo_root / "configuration/logging-policy.json").read_text())
    return {
        "prometheus_retention_days": int(monitoring["metrics"]["raw_retention_baseline"].removesuffix("d")),
        "prometheus_size_target_bytes": int(monitoring["metrics"]["raw_retention_size_baseline"].removesuffix("GiB")) * GIB,
        "loki_retention_hours": int(monitoring["logs"]["development_retention_baseline"].removesuffix("h")),
        "loki_size_target_bytes": int(monitoring["logs"]["development_capacity_target"].removesuffix("GiB")) * GIB,
        "loki_hard_quota": bool(monitoring["logs"]["capacity_target_is_hard_limit"]),
        "host_warn_percent": int(logging["disk_alerting"]["warning_percent"]),
        "host_critical_percent": int(logging["disk_alerting"]["critical_percent"]),
    }


def allocated_tree_bytes(path: Path) -> tuple[int, int]:
    """Count allocated blocks without following links or counting hard links twice."""
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"monitoring store must be a real directory: {path}")
    counted: set[tuple[int, int]] = set()
    allocated = 0
    files = 0

    def count(entry: Path) -> None:
        nonlocal allocated, files
        info = entry.lstat()
        if stat.S_ISLNK(info.st_mode):
            return
        key = (info.st_dev, info.st_ino)
        if key in counted:
            return
        counted.add(key)
        if stat.S_ISREG(info.st_mode):
            files += 1
        allocated += info.st_blocks * 512

    for directory, subdirs, filenames in os.walk(path, followlinks=False):
        current = Path(directory)
        count(current)
        subdirs[:] = sorted(name for name in subdirs if not (current / name).is_symlink())
        for name in filenames:
            count(current / name)
    return allocated, files


def capture(data_root: Path, repo_root: Path, *, timestamp: dt.datetime | None = None) -> dict:
    if data_root.is_symlink() or not data_root.is_dir():
        raise ValueError(f"monitoring data root does not exist or is a symlink: {data_root}")
    stores: dict[str, dict] = {}
    for name in STORES:
        path = data_root / name
        bytes_used, files = allocated_tree_bytes(path)
        stores[name] = {
            "allocated_bytes": bytes_used,
            "files": files,
            "device": path.stat().st_dev,
        }
    fs = os.statvfs(data_root)
    total = fs.f_frsize * fs.f_blocks
    available = fs.f_frsize * fs.f_bavail  # usable by unprivileged services
    free = fs.f_frsize * fs.f_bfree
    if not total or available > total:
        raise ValueError("invalid filesystem size")
    recorded_at = timestamp or dt.datetime.now(dt.timezone.utc)
    if recorded_at.tzinfo is None:
        raise ValueError("snapshot timestamp must be timezone aware")
    return {
        "schema": SCHEMA,
        "captured_at": recorded_at.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "data_root": str(data_root.resolve()),
        "filesystem": {
            "device": data_root.stat().st_dev,
            "total_bytes": total,
            "available_bytes": available,
            "free_bytes": free,
            "used_bytes": total - free,
            "used_percent": round(100 * (total - free) / total, 2),
        },
        "stores": stores,
        "contract": contract(repo_root),
        "caveats": [
            "Read-only filesystem block accounting, not Loki ingestion or Prometheus TSDB cardinality",
            "Loki 4 GiB is a planning target, not an enforced filesystem quota",
            "File timestamps and usage alone do not prove retention/deletion",
        ],
    }


def compare(before: dict, after: dict, *, min_hours: float = 24) -> dict:
    for snapshot in (before, after):
        if snapshot.get("schema") != SCHEMA:
            raise ValueError("unsupported snapshot schema")
    if before["data_root"] != after["data_root"]:
        raise ValueError("different monitoring data roots")
    if before["contract"] != after["contract"]:
        raise ValueError("retention/capacity contract changed: investigate before comparing")
    bf, af = before["filesystem"], after["filesystem"]
    if bf["device"] != af["device"] or bf["total_bytes"] != af["total_bytes"]:
        raise ValueError("filesystem device or capacity changed: investigate before comparing")
    for name in STORES:
        if before["stores"][name]["device"] != after["stores"][name]["device"]:
            raise ValueError(f"{name} store moved to a different filesystem")
    def read_time(snapshot: dict) -> dt.datetime:
        return dt.datetime.fromisoformat(snapshot["captured_at"].replace("Z", "+00:00"))
    hours = (read_time(after) - read_time(before)).total_seconds() / 3600
    if hours < min_hours or hours <= 0:
        raise ValueError(f"snapshot interval {hours:.2f}h is below required {min_hours:.2f}h")
    days = hours / 24.0
    daily_host_delta = (af["used_bytes"] - bf["used_bytes"]) / days
    contracts = after["contract"]
    store_results = {}
    for name in STORES:
        used = after["stores"][name]["allocated_bytes"]
        previous = before["stores"][name]["allocated_bytes"]
        daily_delta = (used - previous) / days
        budget = contracts[name + "_size_target_bytes"]
        store_results[name] = {
            "allocated_gib": round(used / GIB, 3),
            "delta_mib_per_day": round(daily_delta / MIB, 2),
            "budget_gib": round(budget / GIB, 2),
            "budget_type": "retention-size setting (not an absolute disk quota)" if name == "prometheus" else "planning target, NOT an enforced quota",
            "days_to_budget_if_net_growth_persists": (
                round(max(0.0, budget - used) / daily_delta, 2) if daily_delta > 0 else None
            ),
        }
    warnings = {}
    for kind, threshold in (
        ("warning", contracts["host_warn_percent"]),
        ("critical", contracts["host_critical_percent"]),
    ):
        remaining = af["total_bytes"] * (threshold / 100) - af["used_bytes"]
        warnings[kind] = {
            "used_percent_threshold": threshold,
            "days_if_net_growth_persists": (
                round(max(0.0, remaining) / daily_host_delta, 2) if daily_host_delta > 0 else None
            ),
            "already_reached": remaining <= 0,
        }
    return {
        "schema": "merchfactory-monitoring-capacity-comparison-v1",
        "hours": round(hours, 3),
        "host_used_percent": af["used_percent"],
        "host_net_growth_mib_per_day": round(daily_host_delta / MIB, 2),
        "stores": store_results,
        "thresholds": warnings,
        "interpretation": (
            "Observed NET filesystem deltas only; cleanup and compaction can mask ingestion spikes. "
            "Forecasts are conditional linear extrapolations, NOT guaranteed deadlines. "
            "A retention/deletion proof and peak ingestion measurements are separate acceptance steps."
        ),
    }


def write_exclusive(path: Path, snapshot: dict) -> None:
    # Prevent accidental overwrites of historic evidence and protect host metadata.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(snapshot, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    take = subs.add_parser("capture", help="create a new read-only measurement snapshot")
    take.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    take.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    take.add_argument("--output", type=Path, required=True, help="new JSON file (must not already exist)")
    check = subs.add_parser("compare", help="compare two snapshots at least 24 hours apart")
    check.add_argument("--before", type=Path, required=True)
    check.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "capture":
            result = capture(args.data_root, args.repo_root)
            write_exclusive(args.output, result)
            print(f"Snapshot saved: {args.output}")
            print(f"Host filesystem used: {result['filesystem']['used_percent']}%")
            for name in STORES:
                print(f"{name}: {result['stores'][name]['allocated_bytes'] / GIB:.3f} GiB allocated")
            print("One snapshot does NOT establish a 24-hour growth rate or retention compliance.")
        else:
            before = json.loads(args.before.read_text(encoding="utf-8"))
            after = json.loads(args.after.read_text(encoding="utf-8"))
            print(json.dumps(compare(before, after), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
