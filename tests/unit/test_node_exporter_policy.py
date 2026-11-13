#!/usr/bin/env python3
"""Drift tests for the Node Exporter host-agent contract."""

from __future__ import annotations

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = json.loads(
    (REPO_ROOT / "configuration" / "monitoring-stack.json").read_text(encoding="utf-8")
)
DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "node_exporter" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
SERVICE = (
    REPO_ROOT
    / "ansible"
    / "roles"
    / "node_exporter"
    / "templates"
    / "node_exporter.service.j2"
).read_text(encoding="utf-8")
FIREWALL_DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "firewall" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
NETWORK_SCRIPT = (
    REPO_ROOT / "platform" / "network" / "scripts" / "prepare-monitoring-network.sh"
).read_text(encoding="utf-8")
PROMETHEUS_CONFIG = (
    REPO_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
).read_text(encoding="utf-8")
TARGET = (
    REPO_ROOT / "monitoring" / "prometheus" / "targets" / "node-exporter.yml"
).read_text(encoding="utf-8")
RULES = (
    REPO_ROOT / "monitoring" / "prometheus" / "rules" / "node-exporter.yml"
).read_text(encoding="utf-8")


class NodeExporterPolicyTests(unittest.TestCase):
    def test_release_and_checksum_are_pinned(self) -> None:
        node = POLICY["components"]["node_exporter"]
        self.assertEqual(node["version"], "1.12.1")
        self.assertEqual(
            node["archive_sha256"],
            "b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63",
        )
        self.assertIn('node_exporter_version: "1.12.1"', DEFAULTS)
        self.assertIn(node["archive_sha256"], DEFAULTS)

    def test_listener_is_monitoring_gateway_only(self) -> None:
        self.assertEqual(
            POLICY["components"]["node_exporter"]["listen_address"],
            "172.30.250.1:9100",
        )
        self.assertIn(
            "--web.listen-address={{ node_exporter_listen_address }}",
            SERVICE,
        )
        self.assertNotIn("--web.listen-address=0.0.0.0", SERVICE)
        self.assertIn("IPAddressDeny=any", SERVICE)
        self.assertIn(
            "IPAddressAllow={{ node_exporter_monitoring_subnet }}",
            SERVICE,
        )

    def test_netdev_uses_procfs_without_af_netlink(self) -> None:
        node = POLICY["components"]["node_exporter"]
        self.assertFalse(node["netdev_netlink"])
        self.assertEqual(node["network_metric_source"], "/proc/net/dev")
        self.assertIn("node_exporter_netdev_use_netlink: false", DEFAULTS)
        self.assertIn("--no-collector.netdev.netlink", SERVICE)
        self.assertIn(
            "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
            SERVICE,
        )
        self.assertNotIn("AF_NETLINK", SERVICE)

    def test_textfile_collector_is_read_only_for_node_exporter(self) -> None:
        self.assertIn("node_exporter_textfile_directory: /var/lib/merchfactory/node_exporter/textfile", DEFAULTS)
        self.assertIn("node_exporter_textfile_group: merchfactory-backup-metrics", DEFAULTS)
        self.assertIn("--collector.textfile.directory={{ node_exporter_textfile_directory }}", SERVICE)
        self.assertIn("ReadOnlyPaths={{ node_exporter_textfile_directory }}", SERVICE)

    def test_systemd_resource_and_privilege_hardening(self) -> None:
        for fragment in (
            "User={{ node_exporter_user }}",
            "NoNewPrivileges=yes",
            "ProtectSystem=strict",
            "ProtectHome=yes",
            "CapabilityBoundingSet=",
            "AmbientCapabilities=",
            "CPUQuota={{ node_exporter_cpu_quota }}",
            "MemoryMax={{ node_exporter_memory_max }}",
            "TasksMax={{ node_exporter_tasks_max }}",
        ):
            self.assertIn(fragment, SERVICE)

    def test_monitoring_network_contract(self) -> None:
        network = POLICY["networking"]["monitoring_network"]
        self.assertEqual(network["subnet"], "172.30.250.0/24")
        self.assertEqual(network["gateway"], "172.30.250.1")
        self.assertTrue(network["internal"])

        for fragment in (
            "--internal",
            '--subnet "$expected_subnet"',
            '--gateway "$expected_gateway"',
            'com.docker.network.bridge.name=$expected_bridge',
        ):
            self.assertIn(fragment, NETWORK_SCRIPT)

    def test_public_firewall_profile_does_not_open_exporter(self) -> None:
        self.assertIn("  monitoring: []", FIREWALL_DEFAULTS)
        self.assertNotIn("9100/tcp", FIREWALL_DEFAULTS)

    def test_prometheus_uses_file_sd_target(self) -> None:
        self.assertIn("job_name: node-exporter", PROMETHEUS_CONFIG)
        self.assertIn("/etc/prometheus/targets/node-exporter.yml", PROMETHEUS_CONFIG)
        self.assertIn("172.30.250.1:9100", TARGET)
        self.assertIn("service: node-exporter", TARGET)
        self.assertIn("component: host-metrics", TARGET)

    def test_core_alerts_are_present(self) -> None:
        for alert in (
            "NodeExporterDown",
            "HostHighCPUUtilization",
            "HostMemoryPressure",
            "HostFilesystemSpaceLow",
            "HostFilesystemInodesLow",
            "HostNetworkErrors",
            "HostClockSkew",
        ):
            self.assertIn(f"alert: {alert}", RULES)


if __name__ == "__main__":
    unittest.main()
