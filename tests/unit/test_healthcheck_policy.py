#!/usr/bin/env python3
"""Consistency tests for the platform healthcheck policy."""

from __future__ import annotations

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "configuration" / "healthcheck-policy.json"
COMPOSE_TEMPLATE = (
    REPO_ROOT / "templates" / "services" / "container-service" / "deployment" / "compose.yaml.template"
)
ROUTE_TEMPLATE = (
    REPO_ROOT / "templates" / "services" / "container-service" / "routing" / "route.yaml.template"
)
MONITORING_TEMPLATE = (
    REPO_ROOT / "templates" / "services" / "container-service" / "monitoring" / "healthcheck.yaml.template"
)


class HealthcheckPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.compose = COMPOSE_TEMPLATE.read_text(encoding="utf-8")
        cls.route = ROUTE_TEMPLATE.read_text(encoding="utf-8")
        cls.monitoring = MONITORING_TEMPLATE.read_text(encoding="utf-8")

    def test_policy_defaults(self) -> None:
        self.assertEqual(self.policy["liveness"]["interval"], "30s")
        self.assertEqual(self.policy["liveness"]["timeout"], "5s")
        self.assertEqual(self.policy["liveness"]["retries"], 3)
        self.assertEqual(self.policy["liveness"]["default_start_period"], "10s")
        self.assertFalse(self.policy["liveness"]["automatic_restart_on_unhealthy"])

        self.assertEqual(self.policy["readiness"]["interval"], "10s")
        self.assertEqual(self.policy["readiness"]["timeout"], "3s")
        self.assertEqual(self.policy["readiness"]["expected_status"], 200)

        self.assertEqual(self.policy["external_probe"]["interval"], "30s")
        self.assertEqual(self.policy["external_probe"]["timeout"], "5s")
        self.assertEqual(self.policy["external_probe"]["warning_after_failures"], 2)
        self.assertEqual(self.policy["external_probe"]["critical_after_failures"], 5)

    def test_compose_template_matches_liveness_policy(self) -> None:
        for fragment in (
            "interval: 30s",
            "timeout: 5s",
            "retries: 3",
            "start_period: 10s",
        ):
            self.assertIn(fragment, self.compose)

    def test_route_template_matches_readiness_policy(self) -> None:
        for fragment in (
            'path: "{{READINESS_PATH}}"',
            'interval: "10s"',
            'timeout: "3s"',
            "status: 200",
        ):
            self.assertIn(fragment, self.route)

    def test_monitoring_template_contains_all_three_signals(self) -> None:
        self.assertIn("liveness:", self.monitoring)
        self.assertIn("readiness:", self.monitoring)
        self.assertIn("external_probe:", self.monitoring)
        self.assertIn("automatic_restart: false", self.monitoring)


if __name__ == "__main__":
    unittest.main()
