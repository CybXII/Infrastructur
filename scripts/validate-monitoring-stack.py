#!/usr/bin/env python3
"""Validate the v0.6 monitoring stack architecture policy."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO_ROOT / "configuration" / "monitoring-stack.json"

REQUIRED_COMPONENTS = {
    "prometheus",
    "alertmanager",
    "grafana",
    "loki",
    "alloy",
    "node_exporter",
    "cadvisor",
    "blackbox_exporter",
}

EXPECTED_IMPLEMENTATION_ISSUES = {
    "prometheus": 85,
    "node_exporter": 86,
    "container_metrics": 87,
    "grafana": 88,
    "loki": 89,
    "alloy": 90,
    "alertmanager": 91,
    "notification_channels": 92,
    "dashboards": 93,
    "backup_monitoring": 94,
    "external_probes": 95,
    "retention_capacity": 96,
    "runbook": 97,
    "alert_tests": 98,
    "review": 99,
}

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def load(path: pathlib.Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Monitoring-Policy kann nicht gelesen werden: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Monitoring-Policy muss ein JSON-Objekt sein.")
    return document


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if document.get("version") != 1:
        errors.append("version muss 1 sein.")
    if document.get("decision_date") != "2026-09-15":
        errors.append("decision_date muss 2026-09-15 sein.")

    architecture = document.get("architecture") or {}
    if architecture.get("metrics_model") != "prometheus-pull":
        errors.append("Metrikmodell muss prometheus-pull sein.")
    if architecture.get("log_model") != "alloy-host-agent-to-loki":
        errors.append("Logmodell muss Alloy Host-Agent -> Loki sein.")
    if architecture.get("trace_backend_in_scope") is not False:
        errors.append("Trace-Backend gehört nicht zum v0.6-Basisscope.")
    if architecture.get("high_availability_in_scope") is not False:
        errors.append("HA darf im v0.6-Basisscope nicht implizit behauptet werden.")

    components = document.get("components")
    if not isinstance(components, dict):
        errors.append("components fehlt oder ist ungültig.")
        components = {}

    missing = REQUIRED_COMPONENTS - set(components)
    if missing:
        errors.append("Pflichtkomponenten fehlen: " + ", ".join(sorted(missing)))

    for name in REQUIRED_COMPONENTS & set(components):
        component = components[name]
        if not isinstance(component, dict):
            errors.append(f"{name}: Komponentendefinition muss Objekt sein.")
            continue

        version = str(component.get("version") or "")
        if not SEMVER.fullmatch(version):
            errors.append(f"{name}: Version muss exakt als X.Y.Z festgelegt sein.")

        if not str(component.get("upstream") or "").strip():
            errors.append(f"{name}: Upstream-Repository fehlt.")

        if component.get("public_ingress") is True:
            errors.append(f"{name}: Monitoring-Komponenten dürfen keinen öffentlichen Ingress besitzen.")

        resources = component.get("resources")
        if not isinstance(resources, dict) or not resources:
            errors.append(f"{name}: Ressourcenbaseline fehlt.")

    for name in ("prometheus", "alertmanager", "grafana", "loki", "blackbox_exporter"):
        if (components.get(name) or {}).get("deployment") != "container":
            errors.append(f"{name}: muss als zentraler Containerdienst definiert sein.")

    for name in ("alloy", "node_exporter", "cadvisor"):
        if (components.get(name) or {}).get("deployment") != "host-systemd-agent":
            errors.append(f"{name}: muss als systemd Host-Agent definiert sein.")

    if (components.get("alloy") or {}).get("docker_unix_socket_access") is not True:
        errors.append("Alloy muss als expliziter lokaler Docker-Socket-Consumer dokumentiert sein.")
    if (components.get("alloy") or {}).get("docker_tcp_api_allowed") is not False:
        errors.append("Docker TCP API darf für Alloy nicht erlaubt sein.")

    alloy = components.get("alloy") or {}
    if alloy.get("archive_url") != (
        "https://github.com/grafana/alloy/releases/download/"
        "v1.19.2/alloy-linux-amd64.zip"
    ):
        errors.append("Alloy muss das offizielle v1.19.2 linux-amd64 Release-Artefakt verwenden.")
    if alloy.get("archive_sha256") != (
        "3694ea4e1044b367e1c21ffe28117f209c5989fa5e604d000321809f871ab701"
    ):
        errors.append("Alloy archive_sha256 muss dem freigegebenen Upstream-Release entsprechen.")
    if alloy.get("system_user") != "alloy":
        errors.append("Alloy muss unter dem dedizierten Systembenutzer alloy laufen.")
    if alloy.get("listen_address") != "172.30.250.1:12345":
        errors.append("Alloy muss ausschließlich am Monitoring-Gateway 172.30.250.1:12345 lauschen.")
    if alloy.get("docker_unix_socket_path") != "/var/run/docker.sock":
        errors.append("Alloy darf nur den lokalen Docker-Unix-Socket verwenden.")
    if alloy.get("state_path") != "/var/lib/merchfactory/alloy":
        errors.append("Alloy State muss unter /var/lib/merchfactory/alloy persistieren.")
    if alloy.get("loki_endpoint") != "http://172.30.250.10:3100/loki/api/v1/push":
        errors.append("Alloy muss Loki ausschließlich über die interne Monitoring-IP erreichen.")
    if alloy.get("usage_reporting") is not False:
        errors.append("Alloy Usage Reporting muss deaktiviert sein.")
    if alloy.get("working_directory") != "/var/lib/merchfactory/alloy":
        errors.append("Alloy WorkingDirectory muss dem persistenten State-Pfad entsprechen.")
    if alloy.get("memory_deny_write_execute") is not False:
        errors.append("Alloy MemoryDenyWriteExecute muss für offizielle Builds explizit false sein.")
    if alloy.get("journal_read_only_paths") != ["/var/log/journal", "/run/log/journal"]:
        errors.append("Alloy Journalpfade müssen explizit read-only freigegeben sein.")
    if alloy.get("runtime_parent_group") != "merchfactory-runtime":
        errors.append("Alloy Runtime-Parent-Gruppe muss merchfactory-runtime sein.")
    expected_alloy_groups = ["docker", "systemd-journal", "adm", "merchfactory-runtime"]
    if alloy.get("supplementary_groups") != expected_alloy_groups:
        errors.append("Alloy Supplementary Groups entsprechen nicht dem Host-Agent-Vertrag.")

    prometheus = components.get("prometheus") or {}
    if prometheus.get("image_repository") != "quay.io/prometheus/prometheus":
        errors.append("Prometheus muss das offizielle quay.io/prometheus/prometheus Repository verwenden.")
    if not DIGEST.fullmatch(str(prometheus.get("image_digest") or "")):
        errors.append("Prometheus image_digest muss ein vollständiger SHA-256-Digest sein.")
    if prometheus.get("runtime_uid") != 65534 or prometheus.get("runtime_gid") != 65534:
        errors.append("Prometheus Runtime-UID/GID muss 65534:65534 sein.")

    alertmanager = components.get("alertmanager") or {}
    if alertmanager.get("image_repository") != "quay.io/prometheus/alertmanager":
        errors.append("Alertmanager muss das offizielle quay.io/prometheus/alertmanager Repository verwenden.")
    if not DIGEST.fullmatch(str(alertmanager.get("image_digest") or "")):
        errors.append("Alertmanager image_digest muss ein vollständiger SHA-256-Digest sein.")
    if alertmanager.get("runtime_uid") != 65534 or alertmanager.get("runtime_gid") != 65534:
        errors.append("Alertmanager Runtime-UID/GID muss 65534:65534 sein.")
    if alertmanager.get("http_port") != 9093 or alertmanager.get("monitoring_ip") != "172.30.250.30":
        errors.append("Alertmanager muss intern auf 172.30.250.30:9093 lauschen.")
    if alertmanager.get("high_availability") is not False:
        errors.append("Alertmanager HA darf auf dem einzelnen VPS nicht aktiviert sein.")
    if alertmanager.get("notification_mode") != "discord-webhook-file":
        errors.append("Alertmanager muss Discord über eine Webhook-Datei benachrichtigen.")
    if alertmanager.get("discord_webhook_file") != (
        "/srv/merchfactory/secrets/alertmanager/discord-webhook-url"
    ):
        errors.append("Alertmanager Discord-Webhook muss aus dem freigegebenen Secret-Pfad gelesen werden.")
    if alertmanager.get("egress_required") is not True:
        errors.append("Alertmanager benötigt für Discord expliziten Egress.")
    outbound_egress = (document.get("networking") or {}).get("outbound_egress_services") or []
    if "alertmanager" not in outbound_egress:
        errors.append("Alertmanager muss als Outbound-Egress-Service geführt werden.")

    grafana = components.get("grafana") or {}
    if grafana.get("image_repository") != "docker.io/grafana/grafana":
        errors.append("Grafana muss das offizielle docker.io/grafana/grafana Repository verwenden.")
    if not DIGEST.fullmatch(str(grafana.get("image_digest") or "")):
        errors.append("Grafana image_digest muss ein vollständiger SHA-256-Digest sein.")
    if grafana.get("runtime_uid") != 472 or grafana.get("runtime_gid") != 472:
        errors.append("Grafana Runtime-UID/GID muss 472:472 sein.")
    if grafana.get("http_port") != 3000 or grafana.get("monitoring_ip") != "172.30.250.20":
        errors.append("Grafana muss intern auf 172.30.250.20:3000 lauschen.")
    if grafana.get("access_model") != "ssh-tunnel-then-vpn":
        errors.append("Grafana Zugriff muss SSH-Tunnel mit späterem VPN-Ziel verwenden.")
    if grafana.get("anonymous_access") is not False or grafana.get("self_registration") is not False:
        errors.append("Anonymer Zugriff und Grafana-Selbstregistrierung müssen deaktiviert sein.")
    if grafana.get("default_org_role") != "Viewer":
        errors.append("Grafana Standardrolle muss Viewer sein.")

    node_exporter = components.get("node_exporter") or {}
    if node_exporter.get("archive_url") != (
        "https://github.com/prometheus/node_exporter/releases/download/"
        "v1.12.1/node_exporter-1.12.1.linux-amd64.tar.gz"
    ):
        errors.append("Node Exporter muss das offizielle v1.12.1 linux-amd64 Release-Artefakt verwenden.")
    if not re.fullmatch(r"[0-9a-f]{64}", str(node_exporter.get("archive_sha256") or "")):
        errors.append("Node Exporter archive_sha256 muss ein vollständiger SHA-256-Wert sein.")
    if node_exporter.get("listen_address") != "172.30.250.1:9100":
        errors.append("Node Exporter muss ausschließlich am Monitoring-Gateway 172.30.250.1:9100 lauschen.")
    if node_exporter.get("system_user") != "node_exporter":
        errors.append("Node Exporter muss unter dem dedizierten Systembenutzer node_exporter laufen.")
    if node_exporter.get("netdev_netlink") is not False:
        errors.append("Node Exporter netdev muss Netlink deaktivieren, damit AF_NETLINK nicht freigegeben werden muss.")
    if node_exporter.get("network_metric_source") != "/proc/net/dev":
        errors.append("Node Exporter Netzwerkmetriken müssen in der gehärteten Baseline aus /proc/net/dev stammen.")

    cadvisor = components.get("cadvisor") or {}
    if cadvisor.get("binary_url") != (
        "https://github.com/google/cadvisor/releases/download/"
        "v0.60.5/cadvisor-v0.60.5-linux-amd64"
    ):
        errors.append("cAdvisor muss das offizielle v0.60.5 linux-amd64 Release-Artefakt verwenden.")
    if cadvisor.get("binary_sha256") != (
        "6f258bed28113218c88729634c47ead8d928b81b1504b75fd911b98d29003a87"
    ):
        errors.append("cAdvisor binary_sha256 muss dem freigegebenen Upstream-Release entsprechen.")
    if cadvisor.get("listen_address") != "172.30.250.1:8080":
        errors.append("cAdvisor muss ausschließlich am Monitoring-Gateway 172.30.250.1:8080 lauschen.")
    if cadvisor.get("system_user") != "root":
        errors.append("cAdvisor muss als explizit privilegierter Host-Agent unter root laufen.")
    if cadvisor.get("docker_unix_socket_access") is not True:
        errors.append("cAdvisor benötigt expliziten lokalen Docker-Socket-Zugriff.")
    if cadvisor.get("docker_tcp_api_allowed") is not False:
        errors.append("Docker TCP API darf für cAdvisor nicht erlaubt sein.")
    if cadvisor.get("store_container_labels") is not False:
        errors.append("cAdvisor darf Container-Labels nicht ungefiltert exportieren.")
    expected_cadvisor_labels = [
        "com.merchfactory.managed",
        "com.merchfactory.cleanup.protect",
        "com.docker.compose.project",
        "com.docker.compose.service",
    ]
    if cadvisor.get("whitelisted_container_labels") != expected_cadvisor_labels:
        errors.append("cAdvisor Label-Allowlist entspricht nicht dem v0.6-Vertrag.")

    loki = components.get("loki") or {}
    if loki.get("mode") != "monolithic-single-binary":
        errors.append("Loki muss im v0.6-Basisscope monolithisch laufen.")
    if loki.get("tenant_model") != "single-tenant":
        errors.append("Loki-Tenantmodell muss für v0.6 explizit single-tenant sein.")
    if loki.get("storage") != "tsdb-filesystem":
        errors.append("Loki muss im aktuellen v0.6-Scope TSDB mit Filesystem-Storage verwenden.")
    if loki.get("image_repository") != "docker.io/grafana/loki":
        errors.append("Loki muss das offizielle docker.io/grafana/loki Repository verwenden.")
    if not DIGEST.fullmatch(str(loki.get("image_digest") or "")):
        errors.append("Loki image_digest muss ein vollständiger SHA-256-Digest sein.")
    if loki.get("runtime_uid") != 10001 or loki.get("runtime_gid") != 10001:
        errors.append("Loki Runtime-UID/GID muss 10001:10001 sein.")
    if loki.get("http_port") != 3100:
        errors.append("Loki interner HTTP-Port muss 3100 sein.")
    if loki.get("monitoring_ip") != "172.30.250.10":
        errors.append("Loki muss die reservierte interne Monitoring-IP 172.30.250.10 verwenden.")
    if loki.get("retention_period") != "168h":
        errors.append("Loki Development-Retention muss bis #96 168h betragen.")

    metrics = document.get("metrics") or {}
    if metrics.get("prometheus_remote_write_receiver") is not False:
        errors.append("Prometheus Remote-Write-Receiver muss in der Baseline deaktiviert sein.")
    if metrics.get("raw_retention_baseline") != "30d":
        errors.append("Prometheus Rohmetrik-Baseline muss 30d sein.")
    if metrics.get("retention_size_cap_required") is not True:
        errors.append("Prometheus benötigt zusätzlich ein Size-Cap.")
    if metrics.get("raw_retention_size_baseline") != "8GiB":
        errors.append("Prometheus Size-Cap-Baseline muss bis #96 8GiB sein.")
    if metrics.get("final_capacity_issue") != 96:
        errors.append("Finale Kapazitätsentscheidung muss Issue #96 zugeordnet sein.")

    logs = document.get("logs") or {}
    if logs.get("docker_driver_remains") != "local":
        errors.append("Docker local Logging Driver muss erhalten bleiben.")
    if logs.get("collector") != "alloy" or logs.get("storage") != "loki":
        errors.append("Logpipeline muss Alloy -> Loki sein.")
    if logs.get("promtail_allowed") is not False:
        errors.append("Promtail darf nicht Teil der neuen Baseline sein.")
    if logs.get("alloy_state_path") != "/var/lib/merchfactory/alloy":
        errors.append("Alloy-Statepfad muss verbindlich definiert sein.")
    if logs.get("current_environment") != "development":
        errors.append("Aktuelle Loki-Retention muss ausdrücklich dem Development-Scope zugeordnet sein.")
    if logs.get("development_retention_baseline") != "168h":
        errors.append("Development-Loki-Retention muss bis #96 168h sein.")
    if logs.get("development_capacity_target") != "4GiB":
        errors.append("Development-Loki-Kapazitätsziel muss bis #96 4GiB dokumentieren.")
    if logs.get("capacity_target_is_hard_limit") is not False:
        errors.append("Loki Filesystem-Kapazitätsziel darf nicht fälschlich als Hard Limit bezeichnet werden.")
    label_contract = logs.get("label_contract") or {}
    if label_contract.get("required") != ["environment", "host", "service", "component"]:
        errors.append("Loki Pflichtlabels entsprechen nicht dem v0.6-Logvertrag.")
    forbidden_labels = set(label_contract.get("forbidden_high_cardinality") or [])
    if not {"request_id", "order_id", "user_id", "email", "dynamic_url", "stacktrace", "free_message"}.issubset(forbidden_labels):
        errors.append("Loki High-Cardinality-Labelverbote sind unvollständig.")

    networking = document.get("networking") or {}
    monitoring_network = networking.get("monitoring_network") or {}
    expected_monitoring_network = {
        "name": "merchfactory-monitoring",
        "driver": "bridge",
        "internal": True,
        "subnet": "172.30.250.0/24",
        "gateway": "172.30.250.1",
        "bridge_name": "mf-monitoring0",
    }
    if monitoring_network != expected_monitoring_network:
        errors.append("Monitoring-Netzwerk muss exakt dem internen v0.6 Host-Scrape-Vertrag entsprechen.")
    alerting_egress_network = networking.get("alerting_egress_network") or {}
    expected_alerting_egress_network = {
        "name": "merchfactory-alerting-egress",
        "driver": "bridge",
        "internal": False,
        "subnet": "172.30.251.0/29",
        "gateway": "172.30.251.1",
        "bridge_name": "mf-alert-egress",
        "destination_allowlisting": False,
        "egress_scope": "unrestricted-internet",
    }
    if alerting_egress_network != expected_alerting_egress_network:
        errors.append("Alerting-Egress-Netzwerk entspricht nicht dem dedizierten Discord-Vertrag.")
    if networking.get("grafana_private_access_only") is not True:
        errors.append("Grafana muss ausschließlich privat per SSH-Tunnel oder VPN erreichbar sein.")
    if networking.get("exporter_ports_publicly_open") is not False:
        errors.append("Exporter-Ports dürfen nicht öffentlich geöffnet werden.")
    if networking.get("docker_daemon_tcp_exposure_allowed") is not False:
        errors.append("Docker-Daemon-TCP-Exposure ist verboten.")
    if networking.get("critical_external_probe_independence_required") is not True:
        errors.append("Kritische External Probes müssen hostunabhängig sein.")

    security = document.get("security") or {}
    required_false = (
        "anonymous_grafana_access",
        "prometheus_public_ui_allowed",
        "alertmanager_public_ui_allowed",
        "loki_public_api_allowed",
        "raw_docker_socket_mount_in_containers_allowed",
    )
    for key in required_false:
        if security.get(key) is not False:
            errors.append(f"security.{key} muss false sein.")

    required_true = (
        "grafana_authentication_required",
        "alloy_is_privileged_trusted_host_agent",
        "cadvisor_is_privileged_trusted_host_agent",
        "secrets_via_files",
        "immutable_container_digests_required",
        "vulnerability_scan_required",
    )
    for key in required_true:
        if security.get(key) is not True:
            errors.append(f"security.{key} muss true sein.")

    persistence = document.get("persistence") or {}
    for name in ("prometheus", "grafana", "loki", "alertmanager", "alloy"):
        path = str(persistence.get(name) or "")
        if not path.startswith("/"):
            errors.append(f"persistence.{name} muss ein absoluter Pfad sein.")

    issues = document.get("implementation_issues")
    if issues != EXPECTED_IMPLEMENTATION_ISSUES:
        errors.append("implementation_issues muss exakt #85 bis #99 der v0.6-Roadmap abbilden.")

    return errors


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_POLICY
    document = load(path)
    errors = validate(document)

    if errors:
        for error in errors:
            print(f"FEHLER: {error}", file=sys.stderr)
        return 1

    print(
        "Monitoring-Stack validiert: Prometheus/Grafana/Loki/Alloy/Alertmanager "
        "sowie Host-Exporter, Probe- und Security-Verträge sind konsistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
