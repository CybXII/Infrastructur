#!/usr/bin/env python3
"""Tests for the platform container resource policy."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "configuration" / "resource-policy.json"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-compose-standards.py"
TEMPLATE_PATH = (
    REPO_ROOT / "templates" / "services" / "container-service" / "deployment" / "compose.yaml.template"
)
TRAEFIK_PATH = REPO_ROOT / "platform" / "traefik" / "compose.yaml"
PROMETHEUS_PATH = (
    REPO_ROOT / "deployment" / "monitoring" / "prometheus" / "compose.yaml"
)
LOKI_PATH = (
    REPO_ROOT / "deployment" / "monitoring" / "loki" / "compose.yaml"
)
GRAFANA_PATH = (
    REPO_ROOT / "deployment" / "monitoring" / "grafana" / "compose.yaml"
)
ALERTMANAGER_PATH = (
    REPO_ROOT / "deployment" / "monitoring" / "alertmanager" / "compose.yaml"
)

spec = importlib.util.spec_from_file_location("validate_compose_standards", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


def valid_service() -> dict:
    return {
        "image": "ghcr.io/merchfactory/test@sha256:" + "a" * 64,
        "restart": "unless-stopped",
        "labels": {"com.merchfactory.managed": "true"},
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "cpus": 1.0,
        "cpu_shares": 512,
        "mem_limit": "512m",
        "mem_reservation": "256m",
        "pids_limit": 256,
        "healthcheck": {
            "test": ["CMD", "true"],
            "interval": "30s",
            "timeout": "5s",
            "retries": 3,
            "start_period": "10s",
        },
    }


class ResourcePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.template = TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.traefik = TRAEFIK_PATH.read_text(encoding="utf-8")
        cls.prometheus = PROMETHEUS_PATH.read_text(encoding="utf-8")
        cls.loki = LOKI_PATH.read_text(encoding="utf-8")
        cls.grafana = GRAFANA_PATH.read_text(encoding="utf-8")
        cls.alertmanager = ALERTMANAGER_PATH.read_text(encoding="utf-8")

    def test_baseline_values(self) -> None:
        baseline = self.policy["baseline"]
        self.assertEqual(baseline["cpus"], 1.0)
        self.assertEqual(baseline["memory_limit"], "512m")
        self.assertEqual(baseline["memory_reservation"], "256m")
        self.assertEqual(baseline["pids_limit"], 256)
        self.assertEqual(baseline["cpu_shares"], 512)

    def test_priority_classes(self) -> None:
        priorities = self.policy["priority_classes"]
        self.assertEqual(priorities["critical"]["cpu_shares"], 1024)
        self.assertEqual(priorities["standard"]["cpu_shares"], 512)
        self.assertEqual(priorities["background"]["cpu_shares"], 256)

    def test_template_matches_standard_profile(self) -> None:
        for fragment in (
            "${SERVICE_CPU_LIMIT:-1.0}",
            "${SERVICE_CPU_SHARES:-512}",
            "${SERVICE_MEMORY_LIMIT:-512m}",
            "${SERVICE_MEMORY_RESERVATION:-256m}",
            "${SERVICE_PIDS_LIMIT:-256}",
        ):
            self.assertIn(fragment, self.template)

    def test_traefik_matches_critical_profile(self) -> None:
        for fragment in (
            "${TRAEFIK_CPU_LIMIT:-1.0}",
            "${TRAEFIK_CPU_SHARES:-1024}",
            "${TRAEFIK_MEMORY_LIMIT:-512m}",
            "${TRAEFIK_MEMORY_RESERVATION:-256m}",
            "${TRAEFIK_PIDS_LIMIT:-128}",
        ):
            self.assertIn(fragment, self.traefik)

    def test_prometheus_matches_critical_profile(self) -> None:
        prometheus = self.policy["platform_services"]["prometheus"]
        self.assertEqual(prometheus["priority_class"], "critical")
        self.assertEqual(prometheus["cpus"], 1.0)
        self.assertEqual(prometheus["memory_limit"], "1536m")
        self.assertEqual(prometheus["memory_reservation"], "768m")
        self.assertEqual(prometheus["pids_limit"], 256)
        self.assertEqual(prometheus["cpu_shares"], 1024)

        for fragment in (
            "${PROMETHEUS_CPU_LIMIT:-1.0}",
            "${PROMETHEUS_CPU_SHARES:-1024}",
            "${PROMETHEUS_MEMORY_LIMIT:-1536m}",
            "${PROMETHEUS_MEMORY_RESERVATION:-768m}",
            "${PROMETHEUS_PIDS_LIMIT:-256}",
        ):
            self.assertIn(fragment, self.prometheus)

    def test_loki_matches_critical_profile(self) -> None:
        loki = self.policy["platform_services"]["loki"]
        self.assertEqual(loki["priority_class"], "critical")
        self.assertEqual(loki["cpus"], 1.0)
        self.assertEqual(loki["memory_limit"], "1536m")
        self.assertEqual(loki["memory_reservation"], "768m")
        self.assertEqual(loki["pids_limit"], 256)
        self.assertEqual(loki["cpu_shares"], 1024)

        for fragment in (
            "${LOKI_CPU_LIMIT:-1.0}",
            "${LOKI_CPU_SHARES:-1024}",
            "${LOKI_MEMORY_LIMIT:-1536m}",
            "${LOKI_MEMORY_RESERVATION:-768m}",
            "${LOKI_PIDS_LIMIT:-256}",
        ):
            self.assertIn(fragment, self.loki)

    def test_alertmanager_matches_critical_profile(self) -> None:
        alertmanager = self.policy["platform_services"]["alertmanager"]
        self.assertEqual(alertmanager["priority_class"], "critical")
        self.assertEqual(alertmanager["cpus"], 0.25)
        self.assertEqual(alertmanager["memory_limit"], "256m")
        self.assertEqual(alertmanager["memory_reservation"], "128m")
        self.assertEqual(alertmanager["pids_limit"], 128)
        self.assertEqual(alertmanager["cpu_shares"], 256)

        for fragment in (
            "${ALERTMANAGER_CPU_LIMIT:-0.25}",
            "${ALERTMANAGER_CPU_SHARES:-256}",
            "${ALERTMANAGER_MEMORY_LIMIT:-256m}",
            "${ALERTMANAGER_MEMORY_RESERVATION:-128m}",
            "${ALERTMANAGER_PIDS_LIMIT:-128}",
        ):
            self.assertIn(fragment, self.alertmanager)

    def test_grafana_matches_standard_profile(self) -> None:
        grafana = self.policy["platform_services"]["grafana"]
        self.assertEqual(grafana["priority_class"], "standard")
        self.assertEqual(grafana["cpus"], 0.5)
        self.assertEqual(grafana["cpu_shares"], 512)
        for fragment in (
            "${GRAFANA_CPU_LIMIT:-0.5}",
            "${GRAFANA_CPU_SHARES:-512}",
            "${GRAFANA_MEMORY_LIMIT:-512m}",
            "${GRAFANA_MEMORY_RESERVATION:-256m}",
            "${GRAFANA_PIDS_LIMIT:-256}",
        ):
            self.assertIn(fragment, self.grafana)

    def test_valid_service_passes(self) -> None:
        self.assertEqual(validator.validate_service("test", valid_service()), [])

    def test_missing_managed_label_fails(self) -> None:
        service = valid_service()
        service.pop("labels")
        errors = validator.validate_service("test", service)
        self.assertTrue(any("com.merchfactory.managed" in error for error in errors))

    def test_missing_resource_limit_fails(self) -> None:
        for key in ("cpus", "cpu_shares", "mem_limit", "mem_reservation", "pids_limit"):
            with self.subTest(key=key):
                service = copy.deepcopy(valid_service())
                service.pop(key)
                errors = validator.validate_service("test", service)
                self.assertTrue(errors)

    def test_memory_reservation_must_be_lower_than_limit(self) -> None:
        service = valid_service()
        service["mem_reservation"] = "512m"
        errors = validator.validate_service("test", service)
        self.assertTrue(any("mem_reservation" in error for error in errors))

    def test_oom_killer_must_not_be_disabled(self) -> None:
        service = valid_service()
        service["oom_kill_disable"] = True
        errors = validator.validate_service("test", service)
        self.assertTrue(any("oom_kill_disable" in error for error in errors))

    def test_memory_parser(self) -> None:
        self.assertEqual(validator.parse_memory_bytes("512m"), 512 * 1024 * 1024)
        self.assertEqual(validator.parse_memory_bytes("1g"), 1024 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
