#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

version="1.19.2"
archive="alloy-linux-amd64.zip"
url="https://github.com/grafana/alloy/releases/download/v$version/$archive"
sha256="3694ea4e1044b367e1c21ffe28117f209c5989fa5e604d000321809f871ab701"

test_root="$(mktemp -d)"
project="alloy-loki-integration-$$"
fixture="mf-alloy-fixture-$$"
marker_suffix="${GITHUB_RUN_ID:-local}-$$"

export LOKI_DATA_DIR="$test_root/loki"
export MERCHFACTORY_MONITORING_NETWORK="alloy-ci-$marker_suffix"
export MERCHFACTORY_MONITORING_SUBNET="172.30.253.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.253.1"
export MERCHFACTORY_MONITORING_BRIDGE="mfalloy$((RANDOM % 9000 + 1000))"
export LOKI_MONITORING_IP="172.30.253.10"
export MERCHFACTORY_ENVIRONMENT="ci"
export ALLOY_LOKI_ENDPOINT="http://$LOKI_MONITORING_IP:3100/loki/api/v1/push"

alloy_pid=""
container_marker="alloy-docker-marker-$marker_suffix"
journal_marker="alloy-journal-marker-$marker_suffix"

cleanup() {
  docker rm -f "$fixture" >/dev/null 2>&1 || true
  if [[ -n "$alloy_pid" ]]; then
    sudo -n kill "$alloy_pid" >/dev/null 2>&1 || kill "$alloy_pid" >/dev/null 2>&1 || true
    wait "$alloy_pid" >/dev/null 2>&1 || true
  fi
  docker compose -p "$project" -f deployment/monitoring/loki/compose.yaml \
    down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
  sudo rm -rf "$test_root"
}
trap cleanup EXIT

command -v unzip >/dev/null
command -v logger >/dev/null
command -v journalctl >/dev/null

curl --fail --location --silent --show-error \
  "$url" \
  --output "$test_root/$archive"
printf '%s  %s\n' "$sha256" "$test_root/$archive" | sha256sum --check -

mkdir -p "$test_root/alloy"
unzip -q "$test_root/$archive" -d "$test_root/alloy"
binary="$test_root/alloy/alloy-linux-amd64"
chmod +x "$binary"
[[ -x "$binary" ]]
"$binary" --version 2>&1 | grep -q "$version"

config_file="$repo_root/monitoring/alloy/config.alloy"
test -f "$config_file"
"$binary" validate "$config_file"

mkdir -p "$LOKI_DATA_DIR" "$test_root/state"
sudo chown 10001:10001 "$LOKI_DATA_DIR"
sudo chmod 0750 "$LOKI_DATA_DIR"

bash platform/network/scripts/prepare-monitoring-network.sh \
  "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null

docker compose -p "$project" -f deployment/monitoring/loki/compose.yaml up -d

loki_id="$(docker compose -p "$project" -f deployment/monitoring/loki/compose.yaml ps -q loki)"
[[ -n "$loki_id" ]]

for attempt in {1..45}; do
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$loki_id")"
  [[ "$health" == "healthy" ]] && break
  if [[ "$attempt" -eq 45 ]]; then
    docker compose -p "$project" -f deployment/monitoring/loki/compose.yaml logs >&2 || true
    exit 1
  fi
  sleep 1
done

sudo -n env \
  MERCHFACTORY_ENVIRONMENT="$MERCHFACTORY_ENVIRONMENT" \
  ALLOY_LOKI_ENDPOINT="$ALLOY_LOKI_ENDPOINT" \
  "$binary" run \
  --server.http.listen-addr="$MERCHFACTORY_MONITORING_GATEWAY:12345" \
  --storage.path="$test_root/state" \
  --disable-reporting \
  "$config_file" \
  >"$test_root/alloy.log" 2>&1 &
alloy_pid="$!"

for attempt in {1..45}; do
  if curl --fail --silent --show-error --noproxy '*' \
    "http://$MERCHFACTORY_MONITORING_GATEWAY:12345/metrics" \
    > "$test_root/alloy-metrics.txt"; then
    break
  fi
  if ! kill -0 "$alloy_pid" >/dev/null 2>&1; then
    cat "$test_root/alloy.log" >&2
    echo "Alloy wurde unerwartet beendet." >&2
    exit 1
  fi
  if [[ "$attempt" -eq 45 ]]; then
    cat "$test_root/alloy.log" >&2
    echo "Alloy wurde nicht erreichbar." >&2
    exit 1
  fi
  sleep 1
done

listener="$(ss -ltnH 'sport = :12345')"
grep -q "$MERCHFACTORY_MONITORING_GATEWAY:12345" <<<"$listener"
if grep -Eq '(^|[[:space:]])0\.0\.0\.0:12345|\[::\]:12345' <<<"$listener"; then
  echo "Alloy lauscht unerwartet global: $listener" >&2
  exit 1
fi

for metric in \
  process_cpu_seconds_total \
  loki_write_sent_entries_total \
  loki_write_dropped_entries_total \
  loki_write_batch_retries_total; do
  grep -q "^$metric" "$test_root/alloy-metrics.txt" || {
    echo "Alloy-Metrik fehlt: $metric" >&2
    exit 1
  }
done

prometheus_image="$(
  docker compose -f deployment/monitoring/prometheus/compose.yaml config --format json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["prometheus"]["image"])'
)"
docker pull "$prometheus_image" >/dev/null

docker run -d \
  --name "$fixture" \
  --label com.docker.compose.project=alloy-ci \
  --label com.docker.compose.service=fixture \
  --entrypoint /bin/sh \
  "$prometheus_image" \
  -c "while :; do echo '$container_marker'; sleep 2; done" >/dev/null

logger -t merchfactory-alloy-ci "$journal_marker"

journal_marker_found=0
for attempt in {1..15}; do
  if journalctl --no-pager -n 1000 | grep -q "$journal_marker"; then
    journal_marker_found=1
    break
  fi
  sleep 1
done

if [[ "$journal_marker_found" != "1" ]]; then
  echo "Journal-Testmarker wurde lokal nach 15 Sekunden nicht gefunden." >&2
  journalctl --no-pager -n 100 >&2 || true
  exit 1
fi

query_loki() {
  local query="$1"
  curl --fail --silent --show-error --noproxy '*' \
    --get \
    --data-urlencode "query=$query" \
    --data-urlencode "limit=200" \
    "http://$LOKI_MONITORING_IP:3100/loki/api/v1/query_range"
}

docker_result="$test_root/docker-query.json"
for attempt in {1..45}; do
  query_loki '{component="docker",service="fixture"}' > "$docker_result" || true
  if grep -q "$container_marker" "$docker_result"; then
    break
  fi
  if [[ "$attempt" -eq 45 ]]; then
    cat "$test_root/alloy.log" >&2 || true
    cat "$docker_result" >&2 || true
    echo "Docker-Testlog wurde nicht in Loki gefunden." >&2
    exit 1
  fi
  sleep 1
done

python3 - "$docker_result" "$container_marker" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
marker = sys.argv[2]
matches = []
for stream in document.get("data", {}).get("result", []):
    labels = stream.get("stream", {})
    values = stream.get("values", [])
    if any(marker in value[1] for value in values):
        matches.append(labels)

assert matches, document
labels = matches[0]
assert labels["environment"] == "ci", labels
assert labels["component"] == "docker", labels
assert labels["service"] == "fixture", labels
assert labels["project"] == "alloy-ci", labels
assert labels["container"].startswith("mf-alloy-fixture-"), labels
print("Docker-Log mit begrenzten Compose-Labels in Loki gefunden.")
PY

journal_result="$test_root/journal-query.json"
for attempt in {1..45}; do
  query_loki '{component="journal",service="systemd-journal"}' > "$journal_result" || true
  if grep -q "$journal_marker" "$journal_result"; then
    break
  fi
  if [[ "$attempt" -eq 45 ]]; then
    cat "$test_root/alloy.log" >&2 || true
    cat "$journal_result" >&2 || true
    echo "Journal-Testlog wurde nicht in Loki gefunden." >&2
    exit 1
  fi
  sleep 1
done

python3 - "$journal_result" "$journal_marker" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
marker = sys.argv[2]
matches = []
for stream in document.get("data", {}).get("result", []):
    labels = stream.get("stream", {})
    values = stream.get("values", [])
    if any(marker in value[1] for value in values):
        matches.append(labels)

assert matches, document
labels = matches[0]
assert labels["environment"] == "ci", labels
assert labels["component"] == "journal", labels
assert labels["service"] == "systemd-journal", labels
print("journald-Log mit Pflichtlabels in Loki gefunden.")
PY

sudo find "$test_root/state" -type f -print -quit | grep -q . || {
  echo "Alloy hat keinen persistenten Komponentenstate geschrieben." >&2
  exit 1
}

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  check rules /etc/prometheus/rules/alloy.yml

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  test rules /etc/prometheus/rules/tests/alloy.test.yml

echo "Alloy erfolgreich verifiziert: Release, Docker/journald -> Loki, State, Isolation und Alerts."
