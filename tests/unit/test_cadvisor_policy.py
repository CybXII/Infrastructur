#!/usr/bin/env python3
"""Drift tests for the cAdvisor container-metrics host-agent contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import re
import shlex

try:
    import jinja2
except ImportError:
    jinja2 = None
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-monitoring-stack.py"
spec = importlib.util.spec_from_file_location("validate_monitoring_stack", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)

POLICY = json.loads(
    (REPO_ROOT / "configuration" / "monitoring-stack.json").read_text(encoding="utf-8")
)
DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "cadvisor" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
SERVICE = (
    REPO_ROOT / "ansible" / "roles" / "cadvisor" / "templates" / "cadvisor.service.j2"
).read_text(encoding="utf-8")
FIREWALL_DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "firewall" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
PROMETHEUS_CONFIG = (
    REPO_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
).read_text(encoding="utf-8")
TARGET = (
    REPO_ROOT / "monitoring" / "prometheus" / "targets" / "cadvisor.yml"
).read_text(encoding="utf-8")
RULES = (
    REPO_ROOT / "monitoring" / "prometheus" / "rules" / "cadvisor.yml"
).read_text(encoding="utf-8")


class CAdvisorPolicyTests(unittest.TestCase):
    def test_memory_limit_matches_capacity_fix(self) -> None:
        self.assertIn("cadvisor_memory_max: 1028M", DEFAULTS)
        self.assertIn("MemoryMax={{ cadvisor_memory_max }}", SERVICE)

    def test_release_and_checksum_are_pinned(self) -> None:
        cadvisor = POLICY["components"]["cadvisor"]
        self.assertEqual(cadvisor["version"], "0.60.5")
        self.assertEqual(
            cadvisor["binary_sha256"],
            "6f258bed28113218c88729634c47ead8d928b81b1504b75fd911b98d29003a87",
        )
        self.assertIn('cadvisor_version: "0.60.5"', DEFAULTS)
        self.assertIn(cadvisor["binary_sha256"], DEFAULTS)

    def test_privileged_host_agent_contract_is_explicit(self) -> None:
        cadvisor = POLICY["components"]["cadvisor"]
        self.assertEqual(cadvisor["deployment"], "host-systemd-agent")
        self.assertEqual(cadvisor["system_user"], "root")
        self.assertTrue(cadvisor["docker_unix_socket_access"])
        self.assertFalse(cadvisor["docker_tcp_api_allowed"])
        self.assertTrue(POLICY["security"]["cadvisor_is_privileged_trusted_host_agent"])
        self.assertIn("User={{ cadvisor_system_user }}", SERVICE)
        self.assertIn("--docker={{ cadvisor_docker_endpoint }}", SERVICE)
        self.assertNotIn("tcp://", SERVICE)

    def test_listener_is_monitoring_gateway_only(self) -> None:
        self.assertEqual(POLICY["components"]["cadvisor"]["listen_address"], "172.30.250.1:8080")
        self.assertIn("--listen_ip={{ cadvisor_listen_ip }}", SERVICE)
        self.assertIn("IPAddressDeny=any", SERVICE)
        self.assertIn("IPAddressAllow={{ cadvisor_monitoring_subnet }}", SERVICE)
        self.assertNotIn("--listen_ip=0.0.0.0", SERVICE)

    def test_label_cardinality_is_allowlisted(self) -> None:
        cadvisor = POLICY["components"]["cadvisor"]
        self.assertFalse(cadvisor["store_container_labels"])
        self.assertEqual(
            cadvisor["whitelisted_container_labels"],
            [
                "com.merchfactory.managed",
                "com.merchfactory.cleanup.protect",
                "com.docker.compose.project",
                "com.docker.compose.service",
            ],
        )
        self.assertIn("--store_container_labels={{ cadvisor_store_container_labels", SERVICE)
        self.assertIn("--whitelisted_container_labels={{ cadvisor_whitelisted_container_labels }}", SERVICE)

    def test_public_firewall_profile_does_not_open_cadvisor(self) -> None:
        self.assertIn("  monitoring: []", FIREWALL_DEFAULTS)
        self.assertNotIn("8080/tcp", FIREWALL_DEFAULTS)

    def test_prometheus_uses_internal_file_sd_target(self) -> None:
        self.assertIn("job_name: cadvisor", PROMETHEUS_CONFIG)
        self.assertIn("/etc/prometheus/targets/cadvisor.yml", PROMETHEUS_CONFIG)
        self.assertIn("172.30.250.1:8080", TARGET)
        self.assertIn("service: cadvisor", TARGET)
        self.assertIn("component: container-metrics", TARGET)

    def test_validator_rejects_public_or_tcp_cadvisor(self) -> None:
        document = copy.deepcopy(POLICY)
        document["components"]["cadvisor"]["listen_address"] = "0.0.0.0:8080"
        self.assertTrue(any("cAdvisor" in error for error in validator.validate(document)))

        document = copy.deepcopy(POLICY)
        document["components"]["cadvisor"]["docker_tcp_api_allowed"] = True
        self.assertTrue(any("Docker TCP API" in error for error in validator.validate(document)))

        document = copy.deepcopy(POLICY)
        document["components"]["cadvisor"]["store_container_labels"] = True
        self.assertTrue(any("ungefiltert" in error for error in validator.validate(document)))

    def test_required_container_metrics_are_recorded(self) -> None:
        for fragment in (
            "container_cpu_usage_seconds_total",
            "container_memory_working_set_bytes",
            "container_network_receive_bytes_total",
            "container_network_transmit_bytes_total",
            "container_start_time_seconds",
            "record: container:restarts:15m",
            "alert: CAdvisorDown",
        ):
            self.assertIn(fragment, RULES)
        self.assertNotIn("container_fs_usage_bytes", RULES)
        self.assertNotIn("record: container:filesystem_usage_bytes", RULES)
        self.assertIn("disk,diskIO", DEFAULTS)
        self.assertIn("--disable_metrics={{ cadvisor_disable_metrics }}", SERVICE)


    def test_metric_profiles_match_integration_and_validation(self) -> None:
        disabled = re.search(r'^cadvisor_disable_metrics: "([^"]+)"', DEFAULTS, re.M).group(1)
        integration = (REPO_ROOT / "tests/integration/test-cadvisor.sh").read_text()
        tasks = (REPO_ROOT / "ansible/roles/cadvisor/tasks/main.yml").read_text()
        self.assertIn("--disable_metrics=" + disabled, integration)
        self.assertIn("cadvisor_disable_metrics in ['', '" + disabled + "']", tasks)
        self.assertTrue({"disk", "diskIO"}.issubset(disabled.split(",")))
        self.assertTrue({"cpu", "memory", "network"}.isdisjoint(disabled.split(",")))

    @unittest.skipIf(jinja2 is None, "Jinja2 unavailable; render validation requires existing Ansible/Jinja environment")
    def test_rendered_profiles_keep_execstart_contiguous(self) -> None:
        env = jinja2.Environment(trim_blocks=True, undefined=jinja2.StrictUndefined)
        env.filters["ternary"] = lambda value, yes, no: yes if value else no
        # Simple scalar defaults suffice for unit rendering; resolve the listen-IP alias.
        context = {}
        for line in DEFAULTS.splitlines():
            match = re.match(r'^(cadvisor_\w+): (.+)$', line)
            if match:
                context[match[1]] = match[2].strip('"')
        context.update(cadvisor_listen_ip="172.30.250.1", cadvisor_docker_only=True,
                       cadvisor_store_container_labels=False,
                       cadvisor_whitelisted_container_labels="com.merchfactory.managed")
        disabled = context["cadvisor_disable_metrics"]
        for profile in (disabled, ""):
            with self.subTest(profile=profile):
                rendered = env.from_string(SERVICE).render(**dict(context, cadvisor_disable_metrics=profile))
                command = rendered.split("ExecStart=", 1)[1].split("Restart=", 1)[0]
                lines = command.splitlines()
                self.assertTrue(all(line.strip() for line in lines))
                self.assertTrue(all(line.endswith("\\") for line in lines[:-1]))
                args = shlex.split(command.replace("\\\n", " "))
                self.assertIn("--profiling=false", args)
                self.assertEqual(args[-1], "--v=1")
                metric_args = [arg for arg in args if arg.startswith("--disable_metrics=")]
                self.assertEqual(metric_args, ["--disable_metrics=" + profile] if profile else [])


if __name__ == "__main__":
    unittest.main()
