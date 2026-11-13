#!/usr/bin/env python3
"""Issue #96: retention drift and conservative capacity planning."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("retention_audit", ROOT / "scripts/validate-monitoring-retention.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class RetentionCapacityTests(unittest.TestCase):
    def test_current_runtime_and_retention_contract(self):
        self.assertEqual(audit.validate(ROOT), [])

    def test_estimates_exclude_unmeasured_overhead(self):
        self.assertAlmostEqual(audit.estimated_metric_gib(5000, 30, 30, 2.0), 0.80466, places=3)
        self.assertAlmostEqual(audit.estimated_loki_gib(100, 7), 700 / 1024)
        with self.assertRaises(ValueError):
            audit.estimated_metric_gib(5000, 0, 30, 2.0)
        with self.assertRaises(ValueError):
            audit.estimated_loki_gib(-1, 7)

    def test_wrong_loki_retention_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for path in ("configuration/logging-policy.json", "configuration/monitoring-stack.json",
                         "deployment/monitoring/prometheus/compose.yaml", "monitoring/loki/loki.yaml",
                         "monitoring/prometheus/rules/node-exporter.yml"):
                dest = base / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / path).read_bytes())
            loki = base / "monitoring/loki/loki.yaml"
            loki.write_text(loki.read_text().replace("retention_period: 168h", "retention_period: 24h"))
            self.assertTrue(any("Loki" in x for x in audit.validate(base)))

    def test_no_fake_loki_hard_size_cap(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for path in ("configuration/logging-policy.json", "configuration/monitoring-stack.json",
                         "deployment/monitoring/prometheus/compose.yaml", "monitoring/loki/loki.yaml",
                         "monitoring/prometheus/rules/node-exporter.yml"):
                dest = base / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / path).read_bytes())
            path = base / "configuration/monitoring-stack.json"
            data = json.loads(path.read_text())
            data["logs"]["capacity_target_is_hard_limit"] = True
            path.write_text(json.dumps(data))
            self.assertTrue(any("NOT an enforced" in x for x in audit.validate(base)))


LIVE_SPEC = importlib.util.spec_from_file_location(
    "capacity_live", ROOT / "scripts/audit-monitoring-capacity-dev.py"
)
assert LIVE_SPEC and LIVE_SPEC.loader
capacity = importlib.util.module_from_spec(LIVE_SPEC)
LIVE_SPEC.loader.exec_module(capacity)


class LiveCapacitySnapshotTests(unittest.TestCase):
    def test_capture_read_only_counts_store_blocks_and_not_symlinks(self):
        import datetime as dt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prometheus").mkdir()
            (root / "loki").mkdir()
            file = root / "prometheus" / "block"
            file.write_bytes(b"x" * 8192)
            (root / "prometheus" / "hard-link").hardlink_to(file)
            (root / "prometheus" / "symlink").symlink_to(file)
            time = dt.datetime(2026, 10, 20, 12, tzinfo=dt.timezone.utc)
            result = capacity.capture(root, ROOT, timestamp=time)
            self.assertEqual(result["schema"], capacity.SCHEMA)
            self.assertEqual(result["captured_at"], "2026-10-20T12:00:00Z")
            self.assertEqual(result["stores"]["prometheus"]["files"], 1)
            self.assertEqual(result["stores"]["loki"]["files"], 0)
            self.assertGreater(result["stores"]["prometheus"]["allocated_bytes"], 0)
            self.assertEqual(result["contract"]["prometheus_retention_days"], 30)
            self.assertEqual(result["contract"]["loki_retention_hours"], 168)
            self.assertFalse(result["contract"]["loki_hard_quota"])

            output = root / "baseline.json"
            capacity.write_exclusive(output, result)
            self.assertEqual(json.loads(output.read_text())["schema"], capacity.SCHEMA)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                capacity.write_exclusive(output, result)

    def make_snapshots(self):
        import datetime as dt

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prometheus").mkdir()
            (root / "loki").mkdir()
            before = capacity.capture(
                root, ROOT, timestamp=dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
            )
        before["filesystem"].update({
            "total_bytes": 100 * capacity.GIB,
            "free_bytes": 30 * capacity.GIB,
            "available_bytes": 29 * capacity.GIB,
            "used_bytes": 70 * capacity.GIB,
            "used_percent": 70.0,
        })
        before["stores"]["prometheus"]["allocated_bytes"] = 2 * capacity.GIB
        before["stores"]["loki"]["allocated_bytes"] = 1 * capacity.GIB
        after = copy.deepcopy(before)
        after["captured_at"] = "2026-10-21T00:00:00Z"
        after["filesystem"]["used_bytes"] += 1 * capacity.GIB
        after["filesystem"]["free_bytes"] -= 1 * capacity.GIB
        after["filesystem"]["available_bytes"] -= 1 * capacity.GIB
        after["filesystem"]["used_percent"] = 71.0
        after["stores"]["prometheus"]["allocated_bytes"] += 256 * capacity.MIB
        after["stores"]["loki"]["allocated_bytes"] += 128 * capacity.MIB
        return before, after

    def test_24h_growth_forecast_respects_soft_and_hard_budgets(self):
        before, after = self.make_snapshots()
        report = capacity.compare(before, after)
        self.assertEqual(report["hours"], 24)
        self.assertEqual(report["host_net_growth_mib_per_day"], 1024)
        self.assertEqual(report["stores"]["prometheus"]["delta_mib_per_day"], 256)
        self.assertEqual(report["stores"]["loki"]["delta_mib_per_day"], 128)
        self.assertIn("NOT an enforced quota", report["stores"]["loki"]["budget_type"])
        self.assertEqual(report["thresholds"]["warning"]["days_if_net_growth_persists"], 4)
        self.assertEqual(report["thresholds"]["critical"]["days_if_net_growth_persists"], 14)

    def test_invalid_or_incomplete_measurements_are_rejected(self):
        before, after = self.make_snapshots()
        cases = (
            ("too_short", lambda s: s.update(captured_at="2026-10-20T12:00:00Z")),
            ("schema", lambda s: s.update(schema="unknown")),
            ("root", lambda s: s.update(data_root="/other-location")),
            ("host", lambda s: s["filesystem"].update(device=-1)),
            ("store_device", lambda s: s["stores"]["loki"].update(device=-1)),
            ("contract", lambda s: s["contract"].update(loki_hard_quota=True)),
        )
        for name, mutate in cases:
            with self.subTest(name=name):
                altered = copy.deepcopy(after)
                mutate(altered)
                with self.assertRaises(ValueError):
                    capacity.compare(before, altered)

    def test_no_growth_does_not_invent_forecast(self):
        before, after = self.make_snapshots()
        after["filesystem"]["used_bytes"] = before["filesystem"]["used_bytes"]
        after["stores"]["loki"]["allocated_bytes"] = before["stores"]["loki"]["allocated_bytes"]
        report = capacity.compare(before, after)
        self.assertIsNone(report["thresholds"]["warning"]["days_if_net_growth_persists"])
        self.assertIsNone(report["stores"]["loki"]["days_to_budget_if_net_growth_persists"])


if __name__ == "__main__":
    unittest.main()
