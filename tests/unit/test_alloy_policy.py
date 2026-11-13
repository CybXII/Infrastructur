#!/usr/bin/env python3
"""Drift tests for the Grafana Alloy trusted host-agent contract."""

from __future__ import annotations

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

POLICY = json.loads(
    (REPO_ROOT / "configuration" / "monitoring-stack.json").read_text(encoding="utf-8")
)
DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "alloy" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
TASKS = (
    REPO_ROOT / "ansible" / "roles" / "alloy" / "tasks" / "main.yml"
).read_text(encoding="utf-8")
SERVICE = (
    REPO_ROOT / "ansible" / "roles" / "alloy" / "templates" / "alloy.service.j2"
).read_text(encoding="utf-8")
CONFIG = (REPO_ROOT / "monitoring" / "alloy" / "config.alloy").read_text(encoding="utf-8")
PROMETHEUS = (
    REPO_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
).read_text(encoding="utf-8")
TARGET = (
    REPO_ROOT / "monitoring" / "prometheus" / "targets" / "alloy.yml"
).read_text(encoding="utf-8")
RULES = (
    REPO_ROOT / "monitoring" / "prometheus" / "rules" / "alloy.yml"
).read_text(encoding="utf-8")
LOKI_COMPOSE = (
    REPO_ROOT / "deployment" / "monitoring" / "loki" / "compose.yaml"
).read_text(encoding="utf-8")
BOOTSTRAP = (
    REPO_ROOT / "ansible" / "playbooks" / "bootstrap.yml"
).read_text(encoding="utf-8")
BOOTSTRAP_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "bootstrap-managed-host.yml"
).read_text(encoding="utf-8")
FIREWALL_DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "firewall" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
STORAGE_DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "storage_preparation" / "defaults" / "main.yml"
).read_text(encoding="utf-8")


class AlloyPolicyTests(unittest.TestCase):
    def test_release_and_checksum_are_pinned(self) -> None:
        alloy = POLICY["components"]["alloy"]
        self.assertEqual(alloy["version"], "1.19.2")
        self.assertEqual(
            alloy["archive_sha256"],
            "3694ea4e1044b367e1c21ffe28117f209c5989fa5e604d000321809f871ab701",
        )
        self.assertIn('alloy_version: "1.19.2"', DEFAULTS)
        self.assertIn(alloy["archive_sha256"], DEFAULTS)

    def test_docker_refresh_is_bounded(self) -> None:
        self.assertEqual(CONFIG.count('refresh_interval = "5s"'), 2)

    def test_docker_access_is_local_and_explicit(self) -> None:
        alloy = POLICY["components"]["alloy"]
        self.assertTrue(alloy["docker_unix_socket_access"])
        self.assertFalse(alloy["docker_tcp_api_allowed"])
        self.assertEqual(alloy["docker_unix_socket_path"], "/var/run/docker.sock")
        self.assertIn('"unix:///var/run/docker.sock"', CONFIG)
        self.assertNotIn("tcp://", CONFIG)
        self.assertNotIn("tcp://", SERVICE)

    def test_journal_and_docker_groups_are_explicit(self) -> None:
        self.assertEqual(
            POLICY["components"]["alloy"]["supplementary_groups"],
            ["docker", "systemd-journal", "adm", "merchfactory-runtime"],
        )
        self.assertIn("SupplementaryGroups={{ alloy_supplementary_groups | join(' ') }}", SERVICE)
        self.assertIn("Alloy-Journalzugriff als Servicebenutzer prüfen", TASKS)
        self.assertIn("Alloy-Docker-Zugriff als Servicebenutzer prüfen", TASKS)
        self.assertIn("Alloy-Statepfad als Servicebenutzer prüfen", TASKS)
        self.assertEqual(
            POLICY["components"]["alloy"]["runtime_parent_group"],
            "merchfactory-runtime",
        )
        self.assertIn("storage_runtime_group: merchfactory-runtime", STORAGE_DEFAULTS)
        self.assertIn('group: "{{ storage_runtime_group }}"', STORAGE_DEFAULTS)

    def test_systemd_runtime_contract(self) -> None:
        alloy = POLICY["components"]["alloy"]
        self.assertEqual(alloy["working_directory"], "/var/lib/merchfactory/alloy")
        self.assertFalse(alloy["memory_deny_write_execute"])
        self.assertEqual(
            alloy["journal_read_only_paths"],
            ["/var/log/journal", "/run/log/journal"],
        )
        self.assertIn("WorkingDirectory={{ alloy_state_path }}", SERVICE)
        self.assertIn("MemoryDenyWriteExecute=no", SERVICE)
        self.assertNotIn("MemoryDenyWriteExecute=yes", SERVICE)
        self.assertIn(
            "ReadOnlyPaths=-/var/log/journal -/run/log/journal",
            SERVICE,
        )
        self.assertIn("Alloy-Journal bei Startfehler erfassen", TASKS)
        self.assertIn("Alloy-Startfehler mit Diagnose abbrechen", TASKS)
        self.assertIn("Alloy-Journal bei Metrics-Fehler erfassen", TASKS)
        self.assertIn("Alloy-Metrics-Fehler mit Diagnose abbrechen", TASKS)

    def test_systemd_hardening_and_resources(self) -> None:
        for fragment in (
            "NoNewPrivileges=yes",
            "PrivateTmp=yes",
            "PrivateDevices=yes",
            "ProtectSystem=strict",
            "ProtectHome=yes",
            "ProtectKernelTunables=yes",
            "ProtectKernelModules=yes",
            "ProtectKernelLogs=yes",
            "CapabilityBoundingSet=",
            "AmbientCapabilities=",
            "IPAddressDeny=any",
            "IPAddressAllow={{ alloy_monitoring_subnet }}",
            "CPUQuota={{ alloy_cpu_quota }}",
            "MemoryMax={{ alloy_memory_max }}",
            "TasksMax={{ alloy_tasks_max }}",
        ):
            self.assertIn(fragment, SERVICE)

    def test_alloy_listener_is_internal_only(self) -> None:
        self.assertEqual(
            POLICY["components"]["alloy"]["listen_address"],
            "172.30.250.1:12345",
        )
        self.assertIn(
            "--server.http.listen-addr={{ alloy_listen_address }}",
            SERVICE,
        )
        self.assertNotIn("12345/tcp", FIREWALL_DEFAULTS)

    def test_loki_uses_reserved_internal_ip(self) -> None:
        self.assertEqual(
            POLICY["components"]["loki"]["monitoring_ip"],
            "172.30.250.10",
        )
        self.assertIn(
            'ipv4_address: ${LOKI_MONITORING_IP:-172.30.250.10}',
            LOKI_COMPOSE,
        )
        self.assertEqual(
            POLICY["components"]["alloy"]["loki_endpoint"],
            "http://172.30.250.10:3100/loki/api/v1/push",
        )

    def test_required_log_labels_are_bounded(self) -> None:
        for label in ("environment", "host", "service", "component"):
            self.assertIn(label, CONFIG)
        for forbidden in (
            "request_id",
            "order_id",
            "user_id",
            "email",
            "dynamic_url",
            "stacktrace",
            "free_message",
        ):
            self.assertNotIn(forbidden, CONFIG)

    def test_prometheus_scrapes_alloy_and_has_core_alerts(self) -> None:
        self.assertIn("job_name: alloy", PROMETHEUS)
        self.assertIn("/etc/prometheus/targets/alloy.yml", PROMETHEUS)
        self.assertIn("172.30.250.1:12345", TARGET)
        for alert in (
            "AlloyDown",
            "AlloyLogDrops",
            "AlloyWriteRetries",
            "AlloyMemoryNearLimit",
        ):
            self.assertIn(f"alert: {alert}", RULES)

    def test_bootstrap_installs_alloy_after_docker_agents(self) -> None:
        self.assertIn("- role: alloy", BOOTSTRAP)
        self.assertGreater(
            BOOTSTRAP.index("- role: alloy"),
            BOOTSTRAP.index("- role: cadvisor"),
        )
        self.assertIn("'monitoring/alloy/**'", BOOTSTRAP_WORKFLOW)

    def test_state_path_is_persistent_and_reporting_is_disabled(self) -> None:
        alloy = POLICY["components"]["alloy"]
        self.assertEqual(alloy["state_path"], "/var/lib/merchfactory/alloy")
        self.assertFalse(alloy["usage_reporting"])
        self.assertIn("--storage.path={{ alloy_state_path }}", SERVICE)
        self.assertIn("--disable-reporting", SERVICE)
        self.assertIn("mode: '0750'", TASKS)


if __name__ == "__main__":
    unittest.main()
