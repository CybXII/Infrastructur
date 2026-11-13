# Alertmanager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Alertmanager 0.34.0 as a private, persistent alert-processing service and connect Prometheus to it without enabling external notifications.

**Architecture:** Alertmanager runs as one hardened container at `172.30.250.30:9093` on `merchfactory-monitoring`. Prometheus sends rule results to it by Docker DNS; versioned null receivers exercise grouping and inhibition until #92 adds real notification channels.

**Tech Stack:** Docker Compose, Alertmanager 0.34.0, Prometheus 3.14.0, Bash integration tests, Python policy validation, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-17-alertmanager-design.md`

## Global Constraints

- Alertmanager has no DNS, Traefik labels, host port, or public ingress.
- Runtime identity is `65534:65534`.
- Address is `172.30.250.30:9093` on `merchfactory-monitoring`.
- Persistence is `/srv/merchfactory/persistent/monitoring/alertmanager`.
- Resources are CPU `0.25`, shares `256`, memory `256m/128m`, and `128` PIDs.
- Root filesystem is read-only; all capabilities are dropped; `no-new-privileges` is enabled.
- All receivers remain null receivers in #91; notification credentials and outbound delivery belong to #92.
- HA remains disabled while the platform has one VPS.
- Production changes follow red-green-refactor: tests must fail for the missing behavior before implementation.

---

### Task 1: Lock the Alertmanager platform contract

**Files:**
- Modify: `tests/unit/test_monitoring_stack.py`
- Modify: `tests/unit/test_resource_policy.py`
- Modify: `tests/unit/test_validate_image_policy.py`
- Modify: `configuration/monitoring-stack.json`
- Modify: `configuration/resource-policy.json`
- Modify: `configuration/container-image-policy.json`
- Modify: `scripts/validate-monitoring-stack.py`

**Interfaces:**
- Consumes: the existing monitoring policy validator and resource/image policy schemas.
- Produces: a machine-validated Alertmanager contract used by Compose, CI, and deployment tasks.

- [ ] **Step 1: Add failing policy tests**

Add assertions equivalent to:

```python
def test_alertmanager_private_runtime_contract(self) -> None:
    alertmanager = self.policy["components"]["alertmanager"]
    self.assertEqual(alertmanager["version"], "0.34.0")
    self.assertEqual(alertmanager["image_repository"], "quay.io/prometheus/alertmanager")
    self.assertRegex(alertmanager["image_digest"], r"^sha256:[0-9a-f]{64}$")
    self.assertEqual(alertmanager["runtime_uid"], 65534)
    self.assertEqual(alertmanager["runtime_gid"], 65534)
    self.assertEqual(alertmanager["monitoring_ip"], "172.30.250.30")
    self.assertEqual(alertmanager["http_port"], 9093)
    self.assertFalse(alertmanager["public_ingress"])
    self.assertFalse(alertmanager["high_availability"])
    self.assertEqual(alertmanager["notification_mode"], "null-receivers-until-issue-92")
```

Extend resource-policy tests to require the exact resource limits, and image-policy tests to classify `quay.io/prometheus/alertmanager` as third-party runtime.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
python3 -m unittest tests.unit.test_monitoring_stack tests.unit.test_resource_policy tests.unit.test_validate_image_policy
```

Expected: failures for missing Alertmanager runtime fields, resource entry, validator rules, and allowed image repository.

- [ ] **Step 3: Resolve and pin the official image digest**

Run:

```bash
docker pull quay.io/prometheus/alertmanager:v0.34.0
docker image inspect quay.io/prometheus/alertmanager:v0.34.0 --format '{{index .RepoDigests 0}}'
```

Record the returned full `sha256:<64 hex>` digest in `configuration/monitoring-stack.json`. Do not use a mutable tag in runtime Compose.

- [ ] **Step 4: Implement the policy contract**

Add Alertmanager fields for image, UID/GID, IP, port, persistence, notification mode, and HA decision. Add its critical resource profile and complete third-party image-policy metadata. Extend `validate-monitoring-stack.py` to reject a mutable/missing digest, public ingress, wrong identity/address, enabled HA, or a notification mode other than `null-receivers-until-issue-92`.

- [ ] **Step 5: Run tests and verify GREEN**

Run the command from Step 2 plus:

```bash
python3 scripts/validate-monitoring-stack.py
```

Expected: all tests pass and the policy validator exits 0.

- [ ] **Step 6: Commit**

```bash
git add configuration scripts/validate-monitoring-stack.py tests/unit
git commit -m "feat(alertmanager): define private runtime contract"
```

### Task 2: Add versioned routing, inhibition, and hardened Compose

**Files:**
- Create: `monitoring/alertmanager/alertmanager.yml`
- Create: `deployment/monitoring/alertmanager/compose.yaml`
- Create: `tests/integration/test-alertmanager-deployment.sh`
- Modify: `.github/workflows/reusable-static-validation.yml`

**Interfaces:**
- Consumes: Task 1 image digest and resource contract.
- Produces: internal service `alertmanager:9093`, readiness endpoint `/-/ready`, and persistent state at `/alertmanager`.

- [ ] **Step 1: Write the failing integration test**

Create a test that prepares an internal `172.30.250.0/24` network and temporary `65534:65534` data directory, then initially fails because Compose/config files do not exist. It must later assert:

```bash
amtool check-config /etc/alertmanager/alertmanager.yml
test "$(docker inspect "$container_id" --format '{{.Config.User}}')" = 65534:65534
test "$ip" = 172.30.250.30
[[ "$port_bindings" == null || "$port_bindings" == "{}" ]]
test "$networks" = "$MERCHFACTORY_MONITORING_NETWORK"
```

It also queries `/-/ready`, creates a silence through `amtool`, recreates the container, and verifies the silence remains present.

- [ ] **Step 2: Run the test and verify RED**

```bash
bash tests/integration/test-alertmanager-deployment.sh
```

Expected: failure because `deployment/monitoring/alertmanager/compose.yaml` is absent.

- [ ] **Step 3: Create the routing configuration**

Use this configuration contract:

```yaml
global:
  resolve_timeout: 5m
route:
  receiver: default-null
  group_by: [environment, service, alertname, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: critical-null
      matchers: ['severity="critical"']
    - receiver: warning-null
      matchers: ['severity="warning"']
    - receiver: info-null
      matchers: ['severity="info"']
receivers:
  - name: default-null
  - name: critical-null
  - name: warning-null
  - name: info-null
inhibit_rules:
  - source_matchers: ['severity="critical"']
    target_matchers: ['severity=~"warning|info"']
    equal: [environment, service, instance]
  - source_matchers: ['alertname=~".*(Down|Unavailable)$"']
    target_matchers: ['severity=~"warning|info"']
    equal: [environment, service, instance]
```

- [ ] **Step 4: Create hardened Compose**

Follow the existing Prometheus/Loki pattern with pinned digest, `user: "65534:65534"`, read-only root, dropped capabilities, limits, `/tmp` tmpfs, read-only config mount, writable `/alertmanager`, healthcheck against `/-/ready`, fixed IP, and only the external monitoring network. Do not define `ports`, Traefik labels, or an egress network.

- [ ] **Step 5: Add CI validation and verify GREEN**

Add Compose/image validation and the integration test step to `reusable-static-validation.yml`. Run:

```bash
python3 scripts/validate-compose-standards.py deployment/monitoring/alertmanager/compose.yaml
python3 scripts/validate-image-policy.py deployment/monitoring/alertmanager/compose.yaml
bash tests/integration/test-alertmanager-deployment.sh
```

Expected: config valid, container healthy/private, and silence persistent across recreation.

- [ ] **Step 6: Commit**

```bash
git add monitoring/alertmanager deployment/monitoring/alertmanager tests/integration/test-alertmanager-deployment.sh .github/workflows/reusable-static-validation.yml
git commit -m "feat(alertmanager): add private persistent service"
```

### Task 3: Connect Prometheus and prove alert delivery

**Files:**
- Modify: `monitoring/prometheus/prometheus.yml`
- Create: `monitoring/prometheus/rules/tests/alertmanager-delivery.yml`
- Create: `tests/integration/test-prometheus-alertmanager.sh`
- Modify: `.github/workflows/reusable-static-validation.yml`

**Interfaces:**
- Consumes: `alertmanager:9093` from Task 2.
- Produces: Prometheus `alerting.alertmanagers` configuration and an end-to-end delivery test.

- [ ] **Step 1: Write the failing delivery test**

The test starts Alertmanager and a Prometheus test instance on one isolated monitoring network. Mount the existing rules plus `alertmanager-delivery.yml`, wait for both services, and query:

```text
http://PROMETHEUS_IP:9090/api/v1/alertmanagers
http://ALERTMANAGER_IP:9093/api/v2/alerts
```

Assert Prometheus reports one active Alertmanager endpoint and Alertmanager receives an alert named `AlertmanagerDeliveryProbe` with labels `environment=ci`, `service=prometheus`, `severity=info`.

- [ ] **Step 2: Run the test and verify RED**

```bash
bash tests/integration/test-prometheus-alertmanager.sh
```

Expected: failure because Prometheus has no `alerting.alertmanagers` configuration.

- [ ] **Step 3: Add the Prometheus target and test rule**

Add:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: [alertmanager:9093]
```

Use this test-only rule:

```yaml
groups:
  - name: alertmanager-delivery-test
    rules:
      - alert: AlertmanagerDeliveryProbe
        expr: vector(1)
        for: 0m
        labels:
          severity: info
          service: prometheus
        annotations:
          summary: Integration probe for Prometheus to Alertmanager delivery
```

Ensure the test-only rule is mounted only by the integration fixture and is not loaded by production deployment.

- [ ] **Step 4: Verify RED becomes GREEN**

Run `promtool check config`, the existing Prometheus integration test, and the new delivery test:

```bash
bash tests/integration/test-prometheus-deployment.sh
bash tests/integration/test-prometheus-alertmanager.sh
```

Expected: both pass; the probe is delivered with required labels.

- [ ] **Step 5: Commit**

```bash
git add monitoring/prometheus tests/integration/test-prometheus-alertmanager.sh .github/workflows/reusable-static-validation.yml
git commit -m "feat(prometheus): route alerts to Alertmanager"
```

### Task 4: Integrate deployment, verification, rollback, and image scanning

**Files:**
- Modify: `scripts/deploy-development-monitoring-core.sh`
- Modify: `.github/workflows/deploy-development-monitoring.yml`
- Modify: `.github/workflows/image-security.yml`
- Modify: `tests/unit/test_validate_image_policy.py`

**Interfaces:**
- Consumes: Alertmanager Compose from Task 2 and generic `verify-monitoring-service.py`.
- Produces: repeatable development deployment with automatic rollback and security scanning.

- [ ] **Step 1: Add failing deployment/static assertions**

Extend tests or shell assertions to require:

```text
/srv/merchfactory/deployments/development-alertmanager
/srv/merchfactory/persistent/monitoring/alertmanager
ALERTMANAGER_IMAGE_REFERENCE
merchfactory-development-alertmanager
--verify-arg 9093
--verify-arg /-/ready
```

Extend image tests/workflow expectations to require an `alertmanager_image` output and scan job.

- [ ] **Step 2: Run targeted tests and verify RED**

```bash
python3 -m unittest discover -s tests/unit -p 'test_validate_image_policy.py'
bash -n scripts/deploy-development-monitoring-core.sh
```

Expected: the new assertions fail because Alertmanager deployment/scanning is absent.

- [ ] **Step 3: Implement deployment and rollback**

Add Alertmanager compose/state variables, persistent directory preparation as `65534:65534 0750`, target image resolution, state backup/restore loops, previous-release restoration, initial cleanup, deployment-controller invocation, and final status output. Deploy Alertmanager before Prometheus so the configured destination exists when Prometheus starts.

- [ ] **Step 4: Add workflow paths and image scan**

Include Alertmanager directories in deployment path filters and release artifact validation. Resolve its pinned image via Compose and scan it through `reusable-image-security.yml`.

- [ ] **Step 5: Verify GREEN**

```bash
bash -n scripts/deploy-development-monitoring-core.sh
shellcheck scripts/deploy-development-monitoring-core.sh
python3 -m unittest discover -s tests/unit -p 'test_validate_image_policy.py'
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/deploy-development-monitoring-core.sh .github/workflows tests/unit/test_validate_image_policy.py
git commit -m "feat(alertmanager): integrate deployment and image scanning"
```

### Task 5: Document operations and run full verification

**Files:**
- Modify: `monitoring/README.md`
- Modify: `docs/61-monitoring-stack.md`
- Modify: `docs/superpowers/specs/2026-09-17-alertmanager-design.md` only if implementation reveals a required correction.

**Interfaces:**
- Consumes: completed runtime and deployment behavior.
- Produces: operator-facing documentation and merge evidence.

- [ ] **Step 1: Document the implemented service**

Document internal address, persistence, null-receiver boundary, HA decision, Prometheus path, and SSH tunnel example:

```powershell
ssh -N -L 9093:172.30.250.30:9093 BENUTZER@SERVER-IP
```

State clearly that #92 owns real receivers and egress.

- [ ] **Step 2: Run full repository verification**

```bash
python3 scripts/validate-monitoring-stack.py
python3 -m unittest discover -s tests/unit
bash tests/integration/test-alertmanager-deployment.sh
bash tests/integration/test-prometheus-alertmanager.sh
bash tests/integration/test-prometheus-deployment.sh
bash -n scripts/deploy-development-monitoring-core.sh
shellcheck scripts/deploy-development-monitoring-core.sh
```

Expected: every command exits 0 with no warnings caused by the change.

- [ ] **Step 3: Review the final diff**

Confirm:

- no secret values;
- no `ports:` entry;
- no Traefik labels;
- no public DNS;
- no real notification receivers;
- pinned image digest;
- tests cover readiness, persistence, isolation, delivery, deployment, and rollback.

- [ ] **Step 4: Commit documentation**

```bash
git add monitoring/README.md docs/61-monitoring-stack.md
git commit -m "docs(monitoring): document Alertmanager operations"
```

- [ ] **Step 5: Open the pull request**

Use title:

```text
feat(monitoring): privaten Alertmanager integrieren
```

Use a body that references `Closes #91`, `Refs #83`, and `Refs #92`, and summarizes private networking, persistence, routing/inhibition, Prometheus delivery, HA decision, rollback, and verification.
