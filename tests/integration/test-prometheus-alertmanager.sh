#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
workspace="$(mktemp -d)"
network="alertmanager-delivery-${GITHUB_RUN_ID:-local}-$$"
alertmanager_container="alertmanager"
prometheus_container="prometheus-alertmanager-delivery-$$"
alertmanager_image="quay.io/prometheus/alertmanager@sha256:690c7b525f4367aa91f73e2f91c632206d32e97c6384bdbf2fb7a861b420340d"
prometheus_image="quay.io/prometheus/prometheus@sha256:5ce7540c3c00ef4ab0c9d2c995c6a5b9c421f44b4a115d97a2c7af3b1c21cbb0"

diagnose() {
  docker logs "$prometheus_container" >&2 || true
  docker logs "$alertmanager_container" >&2 || true
}

cleanup() {
  docker rm -f "$prometheus_container" "$alertmanager_container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  sudo rm -rf "$workspace"
}
trap diagnose ERR
trap cleanup EXIT

install -d -m 0750 "$workspace/prometheus-data" "$workspace/alertmanager-data"
install -d -m 0755 "$workspace/rules"
printf '%s' 'https://discord.invalid/api/webhooks/integration-test/token' > "$workspace/discord-webhook-url"
cp "$repo_root"/monitoring/prometheus/rules/*.yml "$workspace/rules/"
cp "$repo_root/monitoring/prometheus/rules/tests/alertmanager-delivery.yml" "$workspace/rules/"
sudo chown 65534:65534 "$workspace/prometheus-data" "$workspace/alertmanager-data"
chmod 0400 "$workspace/discord-webhook-url"
sudo chown 65534:65534 "$workspace/discord-webhook-url"
docker network create --internal --subnet 172.30.254.0/24 --gateway 172.30.254.1 "$network" >/dev/null

docker pull "$alertmanager_image" >/dev/null
docker pull "$prometheus_image" >/dev/null

docker run -d \
  --name "$alertmanager_container" \
  --network "$network" \
  --ip 172.30.254.30 \
  --user 65534:65534 \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp \
  -v "$repo_root/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
  -v "$workspace/discord-webhook-url:/run/secrets/discord-webhook-url:ro" \
  -v "$workspace/alertmanager-data:/alertmanager" \
  "$alertmanager_image" \
  --config.file=/etc/alertmanager/alertmanager.yml \
  --storage.path=/alertmanager \
  --web.listen-address=0.0.0.0:9093 >/dev/null

docker run -d \
  --name "$prometheus_container" \
  --network "$network" \
  --ip 172.30.254.40 \
  --user 65534:65534 \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --tmpfs /tmp \
  -e PROMETHEUS_ENVIRONMENT=ci \
  -e PROMETHEUS_HOST=github-runner \
  -v "$repo_root/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$workspace/rules:/etc/prometheus/rules:ro" \
  -v "$repo_root/monitoring/prometheus/targets:/etc/prometheus/targets:ro" \
  -v "$workspace/prometheus-data:/prometheus" \
  "$prometheus_image" \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address=0.0.0.0:9090 >/dev/null

for _ in {1..60}; do
  curl --max-time 3 -fsS http://172.30.254.30:9093/-/ready >/dev/null \
    && curl --max-time 3 -fsS http://172.30.254.40:9090/-/ready >/dev/null \
    && break
  sleep 1
done
curl --max-time 3 -fsS http://172.30.254.30:9093/-/ready >/dev/null
curl --max-time 3 -fsS http://172.30.254.40:9090/-/ready >/dev/null

alertmanagers_json="$workspace/alertmanagers.json"
curl --max-time 3 -fsS http://172.30.254.40:9090/api/v1/alertmanagers > "$alertmanagers_json"
python3 - "$alertmanagers_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
active = document["data"]["activeAlertmanagers"]
assert len(active) == 1, document
assert active[0]["url"].startswith("http://alertmanager:9093"), active
PY

alerts_json="$workspace/alerts.json"
for attempt in {1..75}; do
  curl --max-time 3 -fsS http://172.30.254.30:9093/api/v2/alerts > "$alerts_json"
  if python3 - "$alerts_json" <<'PY'
import json
import pathlib
import sys

alerts = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
ok = any(
    alert.get("labels", {}).get("alertname") == "AlertmanagerDeliveryProbe"
    and alert.get("labels", {}).get("environment") == "ci"
    and alert.get("labels", {}).get("service") == "prometheus"
    and alert.get("labels", {}).get("severity") == "info"
    for alert in alerts
)
raise SystemExit(0 if ok else 1)
PY
  then
    echo "Prometheus hat den Integrationsalarm an Alertmanager zugestellt."
    exit 0
  fi
  if [[ "$attempt" -eq 75 ]]; then
    cat "$alerts_json" >&2
    exit 1
  fi
  sleep 1
done
