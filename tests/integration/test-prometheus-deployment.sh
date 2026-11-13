#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

compose_file="deployment/monitoring/prometheus/compose.yaml"
project="prometheus-integration-$$"
test_root="$(mktemp -d)"

export PROMETHEUS_DATA_DIR="$test_root/data"
export MERCHFACTORY_MONITORING_NETWORK="merchfactory-monitoring-${GITHUB_RUN_ID:-local}-$$"
export PROMETHEUS_ENVIRONMENT="ci"
export PROMETHEUS_HOST="github-runner"
export PROMETHEUS_RETENTION_TIME="30d"
export PROMETHEUS_RETENTION_SIZE="8GiB"
export MERCHFACTORY_MONITORING_SUBNET="172.30.250.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.250.1"
export MERCHFACTORY_MONITORING_BRIDGE="mf-monitoring0"

cleanup() {
  docker compose \
    -p "$project" \
    -f "$compose_file" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true

  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
  sudo rm -rf "$test_root"
}
trap cleanup EXIT

mkdir -p "$PROMETHEUS_DATA_DIR"
sudo chown 65534:65534 "$PROMETHEUS_DATA_DIR"
sudo chmod 0750 "$PROMETHEUS_DATA_DIR"

bash platform/network/scripts/prepare-monitoring-network.sh \
  "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null

network_internal="$(
  docker network inspect \
    --format '{{.Internal}}' \
    "$MERCHFACTORY_MONITORING_NETWORK"
)"
[[ "$network_internal" == "true" ]]

network_class="$(
  docker network inspect \
    --format '{{ index .Labels "com.merchfactory.network.class" }}' \
    "$MERCHFACTORY_MONITORING_NETWORK"
)"
[[ "$network_class" == "monitoring" ]]

network_subnet="$(docker network inspect --format '{{ (index .IPAM.Config 0).Subnet }}' "$MERCHFACTORY_MONITORING_NETWORK")"
network_gateway="$(docker network inspect --format '{{ (index .IPAM.Config 0).Gateway }}' "$MERCHFACTORY_MONITORING_NETWORK")"
network_bridge="$(docker network inspect --format '{{ index .Options "com.docker.network.bridge.name" }}' "$MERCHFACTORY_MONITORING_NETWORK")"
[[ "$network_subnet" == "$MERCHFACTORY_MONITORING_SUBNET" ]]
[[ "$network_gateway" == "$MERCHFACTORY_MONITORING_GATEWAY" ]]
[[ "$network_bridge" == "$MERCHFACTORY_MONITORING_BRIDGE" ]]

python3 scripts/validate-compose-standards.py "$compose_file"
python3 scripts/validate-image-policy.py "$compose_file"

docker compose \
  -p "$project" \
  -f "$compose_file" \
  config >/dev/null

image_ref="$(
  docker compose \
    -p "$project" \
    -f "$compose_file" \
    config --format json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["prometheus"]["image"])'
)"

docker pull "$image_ref" >/dev/null

runtime_uid="$(
  docker run --rm \
    --entrypoint /bin/sh \
    "$image_ref" \
    -c 'id -u nobody'
)"
runtime_gid="$(
  docker run --rm \
    --entrypoint /bin/sh \
    "$image_ref" \
    -c 'id -g nobody'
)"

[[ "$runtime_uid" == "65534" ]]
[[ "$runtime_gid" == "65534" ]]

docker run --rm \
  --entrypoint /bin/promtool \
  -e PROMETHEUS_ENVIRONMENT="$PROMETHEUS_ENVIRONMENT" \
  -e PROMETHEUS_HOST="$PROMETHEUS_HOST" \
  -v "$repo_root/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  -v "$repo_root/monitoring/prometheus/targets:/etc/prometheus/targets:ro" \
  "$image_ref" \
  check config /etc/prometheus/prometheus.yml

docker compose \
  -p "$project" \
  -f "$compose_file" \
  up -d

container_id="$(
  docker compose \
    -p "$project" \
    -f "$compose_file" \
    ps -q prometheus
)"

[[ -n "$container_id" ]]

wait_for_healthy() {
  local cid="$1"
  for attempt in {1..45}; do
    health="$(
      docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$cid"
    )"
    if [[ "$health" == "healthy" ]]; then
      return 0
    fi

    if [[ "$attempt" -eq 45 ]]; then
      echo "Prometheus wurde nicht healthy; letzter Status: $health" >&2
      docker inspect "$cid" >&2 || true
      docker compose -p "$project" -f "$compose_file" logs >&2 || true
      return 1
    fi

    sleep 1
  done
}

wait_for_healthy "$container_id"

published_ports="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$container_id")"
if [[ "$published_ports" != "null" && "$published_ports" != "{}" ]]; then
  echo "Prometheus darf keine direkten Host-Ports besitzen: $published_ports" >&2
  exit 1
fi

networks="$(
  docker inspect "$container_id" \
    | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin)[0]["NetworkSettings"]["Networks"])))'
)"

if [[ "$networks" != "$MERCHFACTORY_MONITORING_NETWORK" ]]; then
  echo "Prometheus besitzt unerwartete Netzwerkmitgliedschaften:" >&2
  printf '%s\n' "$networks" >&2
  exit 1
fi

ready="$(
  docker exec "$container_id" \
    wget -q -O - http://127.0.0.1:9090/-/ready
)"
grep -q 'Prometheus Server is Ready' <<<"$ready"

targets_json="$test_root/targets.json"
for attempt in {1..45}; do
  docker exec "$container_id" \
    wget -q -O - http://127.0.0.1:9090/api/v1/targets \
    > "$targets_json"

  if python3 - "$targets_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
targets = document["data"]["activeTargets"]
ok = any(
    target.get("labels", {}).get("job") == "prometheus"
    and target.get("labels", {}).get("service") == "prometheus"
    and target.get("labels", {}).get("component") == "metrics"
    and target.get("health") == "up"
    for target in targets
)
raise SystemExit(0 if ok else 1)
PY
  then
    break
  fi

  if [[ "$attempt" -eq 45 ]]; then
    echo "Prometheus Self-Scrape wurde nicht healthy." >&2
    cat "$targets_json" >&2
    exit 1
  fi

  sleep 1
done

node_target_json="$test_root/node-target.json"
docker exec "$container_id" \
  wget -q -O - http://127.0.0.1:9090/api/v1/targets \
  > "$node_target_json"

python3 - "$node_target_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
matches = [
    target
    for target in document["data"]["activeTargets"]
    if target.get("labels", {}).get("job") == "node-exporter"
]
assert len(matches) == 1, matches
target = matches[0]
assert target["scrapeUrl"] == "http://172.30.250.1:9100/metrics", target
assert target["labels"]["service"] == "node-exporter", target
assert target["labels"]["component"] == "host-metrics", target
print("Node-Exporter-Target ist im Prometheus-Pullmodell registriert.")
PY

cadvisor_target_json="$test_root/cadvisor-target.json"
docker exec "$container_id" \
  wget -q -O - http://127.0.0.1:9090/api/v1/targets \
  > "$cadvisor_target_json"

python3 - "$cadvisor_target_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
matches = [
    target
    for target in document["data"]["activeTargets"]
    if target.get("labels", {}).get("job") == "cadvisor"
]
assert len(matches) == 1, matches
target = matches[0]
assert target["scrapeUrl"] == "http://172.30.250.1:8080/metrics", target
assert target["labels"]["service"] == "cadvisor", target
assert target["labels"]["component"] == "container-metrics", target
print("cAdvisor-Target ist im Prometheus-Pullmodell registriert.")
PY

alloy_target_json="$test_root/alloy-target.json"
docker exec "$container_id" \
  wget -q -O - http://127.0.0.1:9090/api/v1/targets \
  > "$alloy_target_json"

python3 - "$alloy_target_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
matches = [
    target
    for target in document["data"]["activeTargets"]
    if target.get("labels", {}).get("job") == "alloy"
]
assert len(matches) == 1, matches
target = matches[0]
assert target["scrapeUrl"] == "http://172.30.250.1:12345/metrics", target
assert target["labels"]["service"] == "alloy", target
assert target["labels"]["component"] == "log-collector", target
print("Alloy-Target ist im Prometheus-Pullmodell registriert.")
PY

config_json="$test_root/config.json"
docker exec "$container_id" \
  wget -q -O - http://127.0.0.1:9090/api/v1/status/config \
  > "$config_json"

python3 - "$config_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
config = document["data"]["yaml"]
assert 'environment: ci' in config, config
assert 'host: github-runner' in config, config
assert 'service: prometheus' in config, config
assert 'component: metrics' in config, config
print("Prometheus Runtime-Konfiguration enthält die erwarteten stabilen Labels.")
PY

flags_json="$test_root/flags.json"
docker exec "$container_id" \
  wget -q -O - http://127.0.0.1:9090/api/v1/status/flags \
  > "$flags_json"

python3 - "$flags_json" <<'PY'
import json
import pathlib
import sys

flags = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["data"]
assert flags["storage.tsdb.retention.time"] == "30d", flags
assert flags["storage.tsdb.retention.size"] == "8GiB", flags
assert flags["web.enable-admin-api"] == "false", flags
assert flags["web.enable-remote-write-receiver"] == "false", flags
assert flags["web.enable-lifecycle"] == "false", flags
print("Retention sowie deaktivierte Admin-/Remote-Write-Funktionen sind wirksam.")
PY

rules_json="$test_root/rules.json"
docker exec "$container_id" \
  wget -q -O - 'http://127.0.0.1:9090/api/v1/rules?type=alert' \
  > "$rules_json"

python3 - "$rules_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
names = {
    rule["name"]
    for group in document["data"]["groups"]
    for rule in group["rules"]
}
expected = {
    "PrometheusConfigurationReloadFailure",
    "PrometheusRuleEvaluationFailures",
    "PrometheusTSDBCompactionsFailing",
    "PrometheusSelfScrapeDown",
}
missing = expected - names
assert not missing, missing
print("Prometheus Self-Monitoring-Rules sind geladen.")
PY

sample_json="$test_root/sample.json"
for attempt in {1..45}; do
  docker exec "$container_id" \
    wget -q -O - \
    'http://127.0.0.1:9090/api/v1/query?query=prometheus_build_info' \
    > "$sample_json"

  if python3 - "$sample_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
result = document["data"]["result"]
raise SystemExit(0 if result else 1)
PY
  then
    break
  fi

  if [[ "$attempt" -eq 45 ]]; then
    echo "Keine prometheus_build_info Probe gespeichert." >&2
    exit 1
  fi
  sleep 1
done

sample_timestamp="$(
  python3 - "$sample_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print(document["data"]["result"][0]["value"][0])
PY
)"

sudo test -d "$PROMETHEUS_DATA_DIR/wal"

old_container="$container_id"

docker compose \
  -p "$project" \
  -f "$compose_file" \
  up -d --force-recreate prometheus

container_id="$(
  docker compose \
    -p "$project" \
    -f "$compose_file" \
    ps -q prometheus
)"

[[ -n "$container_id" ]]
[[ "$container_id" != "$old_container" ]]

wait_for_healthy "$container_id"

historic_json="$test_root/historic.json"
docker exec "$container_id" \
  wget -q -O - \
  "http://127.0.0.1:9090/api/v1/query?query=prometheus_build_info%20%40%20$sample_timestamp" \
  > "$historic_json"

python3 - "$historic_json" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
result = document["data"]["result"]
assert result, document
print("Vor dem Container-Recreate gespeicherte TSDB-Probe ist weiterhin abfragbar.")
PY

owner="$(
  stat -c '%u:%g' "$PROMETHEUS_DATA_DIR"
)"
[[ "$owner" == "65534:65534" ]]

echo "Prometheus erfolgreich persistent, intern und mit Self-Monitoring bereitgestellt."
