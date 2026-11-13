#!/usr/bin/env python3
"""Contract tests for the provisioned server overview dashboard."""

from __future__ import annotations

import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "monitoring/grafana/dashboards/server-overview.json"


class GrafanaServerOverviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    def test_dashboard_has_stable_identity_and_safe_defaults(self) -> None:
        self.assertEqual(self.dashboard["uid"], "merchfactory-server-overview")
        self.assertEqual(self.dashboard["title"], "Server Overview")
        self.assertFalse(self.dashboard["editable"])
        self.assertEqual(self.dashboard["refresh"], "30s")
        self.assertEqual(self.dashboard["time"], {"from": "now-6h", "to": "now"})
        self.assertIn("merchfactory", self.dashboard["tags"])
        self.assertIn("infrastructure", self.dashboard["tags"])

    def test_server_variable_discovers_hosts_across_exporter_ports(self) -> None:
        variables = {
            item["name"]: item
            for item in self.dashboard["templating"]["list"]
        }
        server = variables["server"]

        self.assertEqual(server["type"], "query")
        self.assertEqual(server["datasource"]["uid"], "prometheus")
        self.assertEqual(
            server["query"]["query"],
            'label_values(up{job="node-exporter"}, instance)',
        )
        self.assertEqual(server["regex"], "/([^:]+):.*/")
        self.assertTrue(server["includeAll"])
        self.assertEqual(server["allValue"], ".*")

    def test_dashboard_covers_host_container_and_target_health(self) -> None:
        expected_titles = {
            "Monitoring-Ziele",
            "CPU-Auslastung",
            "RAM-Auslastung",
            "Freier Speicherplatz",
            "Netzwerkverkehr",
            "Netzwerkfehler",
            "Container CPU",
            "Container RAM",
            "Container-Neustarts (15m)",
        }
        panels = {panel["title"]: panel for panel in self.dashboard["panels"]}
        self.assertEqual(set(panels), expected_titles)

        expressions = {
            title: "\n".join(target["expr"] for target in panel.get("targets", []))
            for title, panel in panels.items()
        }
        self.assertIn('up{instance=~"$server:.*"}', expressions["Monitoring-Ziele"])
        self.assertIn("node_cpu_seconds_total", expressions["CPU-Auslastung"])
        self.assertIn("node_memory_MemAvailable_bytes", expressions["RAM-Auslastung"])
        self.assertIn("node_filesystem_avail_bytes", expressions["Freier Speicherplatz"])
        self.assertIn("node_network_receive_bytes_total", expressions["Netzwerkverkehr"])
        self.assertIn("node_network_receive_errs_total", expressions["Netzwerkfehler"])
        self.assertIn("container:cpu_usage:rate5m", expressions["Container CPU"])
        self.assertIn("container:memory_working_set_bytes", expressions["Container RAM"])
        self.assertIn("container:restarts:15m", expressions["Container-Neustarts (15m)"])


    def test_ephemeral_container_panels_aggregate_by_host_and_service(self) -> None:
        # Each ephemeral runner produces a distinct container-name/image series.
        # Historical samples must not duplicate legend rows.
        panels = {panel["title"]: panel for panel in self.dashboard["panels"]}
        group = (
            "instance, container_label_com_docker_compose_project, "
            "container_label_com_docker_compose_service"
        )
        expected_legend = (
            "{{container_label_com_docker_compose_project}} / "
            "{{container_label_com_docker_compose_service}} ({{instance}})"
        )
        for title, metric in (
            ("Container CPU", "container:cpu_usage:rate5m"),
            ("Container RAM", "container:memory_working_set_bytes"),
            ("Container-Neustarts (15m)", "container:restarts:15m"),
        ):
            with self.subTest(panel=title):
                target = panels[title]["targets"][0]
                self.assertTrue(
                    target["expr"].startswith(f"sum by ({group}) ("),
                    target["expr"],
                )
                self.assertIn(metric, target["expr"])
                self.assertEqual(target["legendFormat"], expected_legend)
                self.assertIn('instance=~"$server:.*"', target["expr"])
                self.assertIn(
                    'container_label_com_docker_compose_service!=""',
                    target["expr"],
                )
        self.assertTrue(panels["Container CPU"]["targets"][0]["expr"].endswith(" * 100"))

    def test_every_prometheus_target_uses_the_provisioned_datasource(self) -> None:
        for panel in self.dashboard["panels"]:
            for target in panel.get("targets", []):
                with self.subTest(panel=panel["title"], ref_id=target.get("refId")):
                    self.assertEqual(target["datasource"]["uid"], "prometheus")
                    self.assertTrue(target["expr"].strip())


if __name__ == "__main__":
    unittest.main()
