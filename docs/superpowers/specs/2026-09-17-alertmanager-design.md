# Alertmanager Design for Issue #91

**Date:** 2026-09-17  
**Issue:** #91  
**Epic:** #83  
**Status:** Approved design

## Goal

Deploy Alertmanager as the private, central processing layer for Prometheus alerts. It groups alerts, applies severity-aware routing and inhibition, persists operational state, and provides a stable contract for notification channels added later in #92.

## Scope

This issue includes:

- Alertmanager 0.34.0 as a pinned container image.
- Internal-only service discovery from Prometheus to Alertmanager.
- Persistent storage for silences and notification state.
- Versioned routing and inhibition configuration.
- Prometheus delivery to Alertmanager.
- Deployment, rollback, policy validation, image scanning, and integration tests.
- A documented high-availability decision.

This issue excludes:

- E-mail, webhook, Slack, Teams, or other real notification delivery. Those belong to #92.
- Public DNS, Traefik routing, published host ports, or anonymous Internet access.
- A second instance on the same VPS.
- WireGuard configuration.

## Architecture

Alertmanager runs as one hardened container on the existing external Docker network `merchfactory-monitoring`. It receives alerts only from Prometheus at `alertmanager:9093` and does not publish port 9093 to the host.

The service uses the fixed monitoring address `172.30.250.30`. Its UI and API remain internal. Administrative access, when necessary, uses an SSH tunnel initially and WireGuard later.

Alertmanager runs as UID/GID `65534:65534`, with a read-only root filesystem, all Linux capabilities dropped, `no-new-privileges`, bounded CPU, memory, PIDs, and a writable bind mount only at `/alertmanager`.

## Image and resources

- Version: `0.34.0`
- Repository: `quay.io/prometheus/alertmanager`
- Image: immutable SHA-256 digest recorded in the monitoring policy
- CPU limit: `0.25`
- CPU shares: `256`
- Memory limit: `256m`
- Memory reservation: `128m`
- PID limit: `128`
- Persistent host path: `/srv/merchfactory/persistent/monitoring/alertmanager`

The final digest is resolved from the official upstream image and validated by the repository image policy and security workflow.

## Routing contract

The root route groups alerts by:

- `environment`
- `service`
- `alertname`
- `severity`

Timing defaults:

- `group_wait: 30s`
- `group_interval: 5m`
- `repeat_interval: 4h`

Three child routes explicitly classify `critical`, `warning`, and `info`. In #91 all routes terminate at named null receivers. This exercises the complete routing tree without sending messages. Issue #92 replaces or extends those receiver definitions without changing the classification contract.

Alerts without a valid severity use the root null receiver and remain visible in Alertmanager rather than being discarded by an unmatched route.

## Inhibition contract

Two versioned inhibition rules are used:

1. A `critical` alert suppresses `warning` and `info` alerts for the same `environment`, `service`, and `instance`.
2. A source alert whose name ends in `Down` or `Unavailable` suppresses downstream `warning` and `info` alerts for the same `environment`, `service`, and `instance`.

This prevents cascades while preserving the causal alert. Inhibition affects notification delivery only; inhibited alerts remain visible in Alertmanager.

## Prometheus integration

Prometheus gains an `alerting.alertmanagers` target for `alertmanager:9093` using the existing monitoring network. The integration test verifies that:

- Prometheus loads the target configuration.
- Alertmanager reports ready.
- A synthetic test alert sent through Prometheus reaches Alertmanager.
- Labels and severity survive the path.
- The alert resolves and disappears after cleanup.

Existing production alert rules are not changed merely to test transport.

## Persistence and rollback

Alertmanager stores silences and notification log state in `/alertmanager`. Deployment uses the existing release controller and automatic rollback pattern used by Prometheus, Loki, and Grafana.

The deployment script:

- prepares the persistent directory as `65534:65534` with mode `0750`;
- records Alertmanager deployment state and release environment;
- deploys and verifies Alertmanager before completing the monitoring release;
- includes Alertmanager state in backup and rollback handling;
- restores the previous Alertmanager release when a later monitoring-core deployment step fails.

No notification credentials exist in #91.

## High availability decision

The platform currently has one primary VPS. Two Alertmanager containers on the same host would not survive a host, network, storage, or Docker failure and would therefore provide misleading high availability.

Issue #91 deliberately deploys one persistent instance. Real Alertmanager HA requires at least two independent failure domains and is deferred until the infrastructure has multiple hosts. This decision satisfies the issue requirement to evaluate HA without adding ineffective complexity.

## Networking and security

- No public ingress.
- No host port publishing.
- No DNS record.
- No Traefik labels.
- Only the internal monitoring network is attached.
- No secrets are introduced.
- Outbound notification egress is not enabled in #91; controlled egress is designed together with the receivers in #92.
- Alertmanager configuration is mounted read-only.
- Persistent runtime state is the only writable host bind mount.

## Failure behavior

- Invalid configuration fails validation before deployment.
- An unhealthy or unreachable Alertmanager fails deployment verification and triggers rollback.
- Prometheus keeps evaluating rules if Alertmanager is temporarily unavailable and exposes delivery failures through its own metrics.
- Alertmanager restarts automatically and reloads persisted operational state.
- A notification receiver cannot accidentally send during #91 because every configured receiver is a null receiver.

## Testing

Tests cover:

- Monitoring policy contract for version, digest, UID/GID, address, resources, persistence, and private exposure.
- Alertmanager configuration syntax using `amtool check-config`.
- Routing and inhibition structure through deterministic configuration assertions.
- Compose hardening and image-policy validation.
- Container readiness and persistence across recreation.
- Absence of host port bindings and unexpected networks.
- Prometheus-to-Alertmanager delivery with a synthetic alert and subsequent resolution.
- Deployment state, verification, and rollback inclusion.
- Container image vulnerability scanning.

## Follow-up contract for #92

Issue #92 may add file-backed receiver credentials and controlled outbound egress. It must preserve:

- the severity labels and three route classes;
- internal-only UI/API access;
- secrets outside Git;
- least-privilege file permissions;
- tested failure handling for unavailable notification providers.
