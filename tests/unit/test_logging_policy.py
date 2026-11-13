#!/usr/bin/env python3
"""Consistency tests for the platform logging policy."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "configuration" / "logging-policy.json"
DOCKER_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "docker_runtime" / "defaults" / "main.yml"
DOCKER_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "docker_runtime" / "templates" / "daemon.json.j2"
JOURNAL_DEFAULTS = REPO_ROOT / "ansible" / "roles" / "system_logging" / "defaults" / "main.yml"
JOURNAL_TEMPLATE = REPO_ROOT / "ansible" / "roles" / "system_logging" / "templates" / "60-merchfactory-retention.conf.j2"
SERVICE_LOGGING = REPO_ROOT / "templates" / "services" / "container-service" / "logging" / "policy.yaml.template"
BOOTSTRAP = REPO_ROOT / "ansible" / "playbooks" / "bootstrap.yml"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-compose-standards.py"

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


class LoggingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.docker_defaults = DOCKER_DEFAULTS.read_text(encoding="utf-8")
        cls.docker_template = DOCKER_TEMPLATE.read_text(encoding="utf-8")
        cls.journal_defaults = JOURNAL_DEFAULTS.read_text(encoding="utf-8")
        cls.journal_template = JOURNAL_TEMPLATE.read_text(encoding="utf-8")
        cls.service_logging = SERVICE_LOGGING.read_text(encoding="utf-8")
        cls.bootstrap = BOOTSTRAP.read_text(encoding="utf-8")

    def test_container_log_policy(self) -> None:
        container = self.policy["container_logs"]
        self.assertEqual(container["driver"], "local")
        self.assertEqual(container["max_size"], "20m")
        self.assertEqual(container["max_files"], 5)
        self.assertTrue(container["compress"])
        self.assertEqual(container["service_override_policy"], "default-deny")

    def test_docker_defaults_match_policy(self) -> None:
        for fragment in (
            "docker_log_driver: local",
            "docker_log_max_size: 20m",
            "docker_log_max_files: 5",
            "docker_log_compress: true",
        ):
            self.assertIn(fragment, self.docker_defaults)

        for fragment in (
            '"max-size": "{{ docker_log_max_size }}"',
            '"max-file": "{{ docker_log_max_files }}"',
            '"compress": "{{ docker_log_compress | bool | lower }}"',
        ):
            self.assertIn(fragment, self.docker_template)

    def test_journald_defaults_match_policy(self) -> None:
        expected = (
            "system_logging_storage: persistent",
            "system_logging_system_max_use: 512M",
            "system_logging_system_keep_free: 1G",
            "system_logging_system_max_file_size: 64M",
            "system_logging_runtime_max_use: 64M",
            "system_logging_runtime_keep_free: 128M",
            "system_logging_runtime_max_file_size: 16M",
            "system_logging_max_retention_sec: 30day",
            "system_logging_max_file_sec: 1day",
        )
        for fragment in expected:
            self.assertIn(fragment, self.journal_defaults)

        self.assertIn("SystemMaxUse={{ system_logging_system_max_use }}", self.journal_template)
        self.assertIn("MaxRetentionSec={{ system_logging_max_retention_sec }}", self.journal_template)
        self.assertIn("- role: system_logging", self.bootstrap)

    def test_service_template_matches_policy(self) -> None:
        for fragment in (
            "driver: local",
            "max_size: 20m",
            "max_files: 5",
            "compress: true",
            "standard_days: 30",
            "security_days: 365",
            "service_logging_override_allowed: false",
        ):
            self.assertIn(fragment, self.service_logging)

    def test_compose_logging_override_is_rejected(self) -> None:
        service = copy.deepcopy(valid_service())
        service["logging"] = {
            "driver": "json-file",
            "options": {"max-size": "1g"},
        }
        errors = validator.validate_service("test", service)
        self.assertTrue(any("logging-Overrides" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
