#!/usr/bin/env python3
"""Tests for the v0.6 monitoring stack architecture policy."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "configuration" / "monitoring-stack.json"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-monitoring-stack.py"

spec = importlib.util.spec_from_file_location("validate_monitoring_stack", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


class MonitoringStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_current_policy_is_valid(self) -> None:
        self.assertEqual(validator.validate(self.policy), [])

    def test_no_monitoring_component_may_have_public_ingress(self) -> None:
        for component in ("prometheus", "grafana", "loki"):
            with self.subTest(component=component):
                document = copy.deepcopy(self.policy)
                document["components"][component]["public_ingress"] = True
                errors = validator.validate(document)
                self.assertTrue(any("keinen öffentlichen Ingress" in error for error in errors))

    def test_grafana_private_runtime_contract(self) -> None:
        grafana = self.policy["components"]["grafana"]
        self.assertEqual(grafana["version"], "13.2.2")
        self.assertEqual(grafana["image_repository"], "docker.io/grafana/grafana")
        self.assertRegex(grafana["image_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(grafana["runtime_uid"], 472)
        self.assertEqual(grafana["runtime_gid"], 472)
        self.assertEqual(grafana["monitoring_ip"], "172.30.250.20")
        self.assertEqual(grafana["access_model"], "ssh-tunnel-then-vpn")
        self.assertFalse(grafana["public_ingress"])
        self.assertFalse(grafana["anonymous_access"])
        self.assertFalse(grafana["self_registration"])
        self.assertEqual(grafana["default_org_role"], "Viewer")

    def test_alertmanager_private_runtime_contract(self) -> None:
        alertmanager = self.policy["components"]["alertmanager"]
        self.assertEqual(alertmanager["version"], "0.34.0")
        self.assertEqual(
            alertmanager["image_repository"],
            "quay.io/prometheus/alertmanager",
        )
        self.assertRegex(alertmanager["image_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(alertmanager["runtime_uid"], 65534)
        self.assertEqual(alertmanager["runtime_gid"], 65534)
        self.assertEqual(alertmanager["monitoring_ip"], "172.30.250.30")
        self.assertEqual(alertmanager["http_port"], 9093)
        self.assertFalse(alertmanager["public_ingress"])
        self.assertFalse(alertmanager["high_availability"])
        self.assertTrue(alertmanager["egress_required"])
        self.assertIn(
            "alertmanager",
            self.policy["networking"]["outbound_egress_services"],
        )
        self.assertEqual(
            alertmanager["notification_mode"],
            "discord-webhook-file",
        )
        self.assertEqual(
            alertmanager["discord_webhook_file"],
            "/srv/merchfactory/secrets/alertmanager/discord-webhook-url",
        )

        egress = self.policy["networking"]["alerting_egress_network"]
        self.assertEqual(egress["name"], "merchfactory-alerting-egress")
        self.assertEqual(egress["driver"], "bridge")
        self.assertFalse(egress["internal"])
        self.assertEqual(egress["bridge_name"], "mf-alert-egress")
        self.assertIs(egress.get("destination_allowlisting"), False)
        self.assertEqual(egress.get("egress_scope"), "unrestricted-internet")

    def test_alertmanager_invalid_contract_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["alertmanager"]["public_ingress"] = True
        document["components"]["alertmanager"]["high_availability"] = True
        document["components"]["alertmanager"]["egress_required"] = False
        document["components"]["alertmanager"]["notification_mode"] = "null"
        document["networking"]["outbound_egress_services"] = ["blackbox_exporter"]
        document["networking"]["alerting_egress_network"] = {
            "name": "wrong",
            "driver": "bridge",
            "internal": True,
            "bridge_name": "wrong",
        }
        errors = validator.validate(document)
        self.assertGreaterEqual(
            sum("Alertmanager" in error or "Alerting-Egress" in error for error in errors),
            4,
        )

    def test_promtail_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["logs"]["promtail_allowed"] = True
        errors = validator.validate(document)
        self.assertTrue(any("Promtail" in error for error in errors))

    def test_prometheus_runtime_contract(self) -> None:
        prometheus = self.policy["components"]["prometheus"]
        self.assertEqual(
            prometheus["image_repository"],
            "quay.io/prometheus/prometheus",
        )
        self.assertRegex(prometheus["image_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(prometheus["runtime_uid"], 65534)
        self.assertEqual(prometheus["runtime_gid"], 65534)
        self.assertEqual(self.policy["metrics"]["raw_retention_baseline"], "30d")
        self.assertEqual(self.policy["metrics"]["raw_retention_size_baseline"], "8GiB")

    def test_prometheus_invalid_digest_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["prometheus"]["image_digest"] = "sha256:broken"
        errors = validator.validate(document)
        self.assertTrue(any("image_digest" in error for error in errors))

    def test_loki_runtime_contract(self) -> None:
        loki = self.policy["components"]["loki"]
        self.assertEqual(loki["version"], "3.7.7")
        self.assertEqual(loki["image_repository"], "docker.io/grafana/loki")
        self.assertRegex(loki["image_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(loki["runtime_uid"], 10001)
        self.assertEqual(loki["runtime_gid"], 10001)
        self.assertEqual(loki["http_port"], 3100)
        self.assertEqual(loki["retention_period"], "168h")
        self.assertFalse(loki["public_ingress"])

        logs = self.policy["logs"]
        self.assertEqual(logs["current_environment"], "development")
        self.assertEqual(logs["development_retention_baseline"], "168h")
        self.assertEqual(logs["development_capacity_target"], "4GiB")
        self.assertFalse(logs["capacity_target_is_hard_limit"])
        self.assertEqual(
            logs["label_contract"]["required"],
            ["environment", "host", "service", "component"],
        )

    def test_loki_invalid_digest_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["loki"]["image_digest"] = "sha256:broken"
        errors = validator.validate(document)
        self.assertTrue(any("Loki image_digest" in error for error in errors))

    def test_loki_hard_size_cap_claim_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["logs"]["capacity_target_is_hard_limit"] = True
        errors = validator.validate(document)
        self.assertTrue(any("Hard Limit" in error for error in errors))

    def test_alloy_runtime_contract(self) -> None:
        alloy = self.policy["components"]["alloy"]
        self.assertEqual(alloy["version"], "1.19.2")
        self.assertEqual(alloy["deployment"], "host-systemd-agent")
        self.assertEqual(
            alloy["archive_sha256"],
            "3694ea4e1044b367e1c21ffe28117f209c5989fa5e604d000321809f871ab701",
        )
        self.assertEqual(alloy["system_user"], "alloy")
        self.assertEqual(alloy["listen_address"], "172.30.250.1:12345")
        self.assertEqual(alloy["docker_unix_socket_path"], "/var/run/docker.sock")
        self.assertEqual(alloy["state_path"], "/var/lib/merchfactory/alloy")
        self.assertEqual(
            alloy["loki_endpoint"],
            "http://172.30.250.10:3100/loki/api/v1/push",
        )
        self.assertFalse(alloy["usage_reporting"])
        self.assertEqual(
            alloy["supplementary_groups"],
            ["docker", "systemd-journal", "adm", "merchfactory-runtime"],
        )
        self.assertEqual(
            self.policy["components"]["loki"]["monitoring_ip"],
            "172.30.250.10",
        )

    def test_alloy_global_listener_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["alloy"]["listen_address"] = "0.0.0.0:12345"
        errors = validator.validate(document)
        self.assertTrue(
            any("Alloy" in error and "Monitoring-Gateway" in error for error in errors)
        )

    def test_alloy_tcp_docker_api_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["alloy"]["docker_tcp_api_allowed"] = True
        errors = validator.validate(document)
        self.assertTrue(any("Docker TCP API" in error for error in errors))

    def test_node_exporter_runtime_contract(self) -> None:
        node_exporter = self.policy["components"]["node_exporter"]
        self.assertEqual(node_exporter["version"], "1.12.1")
        self.assertEqual(node_exporter["deployment"], "host-systemd-agent")
        self.assertEqual(
            node_exporter["archive_sha256"],
            "b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63",
        )
        self.assertEqual(node_exporter["listen_address"], "172.30.250.1:9100")
        self.assertEqual(node_exporter["system_user"], "node_exporter")
        self.assertFalse(node_exporter["public_ingress"])

        network = self.policy["networking"]["monitoring_network"]
        self.assertEqual(network["name"], "merchfactory-monitoring")
        self.assertEqual(network["subnet"], "172.30.250.0/24")
        self.assertEqual(network["gateway"], "172.30.250.1")
        self.assertEqual(network["bridge_name"], "mf-monitoring0")
        self.assertTrue(network["internal"])

    def test_node_exporter_global_listener_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["node_exporter"]["listen_address"] = "0.0.0.0:9100"
        errors = validator.validate(document)
        self.assertTrue(any("Monitoring-Gateway" in error for error in errors))

    def test_monitoring_network_drift_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["networking"]["monitoring_network"]["internal"] = False
        errors = validator.validate(document)
        self.assertTrue(any("Monitoring-Netzwerk" in error for error in errors))

    def test_prometheus_must_remain_pull_based(self) -> None:
        document = copy.deepcopy(self.policy)
        document["metrics"]["prometheus_remote_write_receiver"] = True
        errors = validator.validate(document)
        self.assertTrue(any("Remote-Write-Receiver" in error for error in errors))

    def test_raw_docker_socket_in_containers_is_rejected(self) -> None:
        document = copy.deepcopy(self.policy)
        document["security"]["raw_docker_socket_mount_in_containers_allowed"] = True
        errors = validator.validate(document)
        self.assertTrue(any("raw_docker_socket" in error for error in errors))

    def test_alloy_must_remain_host_agent(self) -> None:
        document = copy.deepcopy(self.policy)
        document["components"]["alloy"]["deployment"] = "container"
        errors = validator.validate(document)
        self.assertTrue(any("Alloy" in error or "alloy" in error for error in errors))

    def test_external_probe_independence_is_required(self) -> None:
        document = copy.deepcopy(self.policy)
        document["networking"]["critical_external_probe_independence_required"] = False
        errors = validator.validate(document)
        self.assertTrue(any("hostunabhängig" in error for error in errors))

    def test_roadmap_mapping_must_not_drift(self) -> None:
        document = copy.deepcopy(self.policy)
        document["implementation_issues"]["prometheus"] = 999
        errors = validator.validate(document)
        self.assertTrue(any("Roadmap" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
