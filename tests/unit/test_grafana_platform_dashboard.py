#!/usr/bin/env python3
"""Contract tests for the provisioned platform overview dashboard."""

from __future__ import annotations

import json
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "monitoring/grafana/dashboards/platform-overview.json"

class GrafanaPlatformOverviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    def test_dashboard_has_stable_identity_and_safe_defaults(self) -> None:
        self.assertEqual(self.dashboard["uid"], "merchfactory-platform-overview")
        self.assertEqual(self.dashboard["title"], "Platform Overview")
        self.assertFalse(self.dashboard["editable"])
        self.assertEqual(self.dashboard["refresh"], "30s")
        self.assertEqual(self.dashboard["time"], {"from": "now-6h", "to": "now"})
        self.assertIn("platform", self.dashboard["tags"])

    def test_job_variable_is_limited_to_scraped_platform_jobs(self) -> None:
        job = {item["name"]: item for item in self.dashboard["templating"]["list"]}["job"]
        self.assertEqual(job["query"]["query"], "label_values(up, job)")
        self.assertEqual(job["regex"], "/^(prometheus|node-exporter|cadvisor|alloy)$/")
        self.assertTrue(job["includeAll"])
        self.assertEqual(job["allValue"], ".*")

    def test_dashboard_covers_platform_target_and_service_health(self) -> None:
        expected = {
            "Plattform-Targets", "Erreichbare Targets", "Ausgefallene Targets",
            "Beobachtete Container-Services", "Target-Verfügbarkeit nach Job",
            "Service-Neustarts (15m)",
        }
        panels = {panel["title"]: panel for panel in self.dashboard["panels"]}
        self.assertEqual(set(panels), expected)
        expressions = {
            title: "\n".join(target["expr"] for target in panel.get("targets", []))
            for title, panel in panels.items()
        }
        self.assertIn('up{job=~"$job"}', expressions["Plattform-Targets"])
        self.assertIn("container_last_seen", expressions["Beobachtete Container-Services"])
        self.assertIn("container:restarts:15m", expressions["Service-Neustarts (15m)"])

    def test_every_target_uses_provisioned_prometheus(self) -> None:
        for panel in self.dashboard["panels"]:
            for target in panel.get("targets", []):
                with self.subTest(panel=panel["title"], ref_id=target.get("refId")):
                    self.assertEqual(target["datasource"]["uid"], "prometheus")
                    self.assertTrue(target["expr"].strip())

if __name__ == "__main__":
    unittest.main()
