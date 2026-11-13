#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

version="1.12.1"
archive="node_exporter-$version.linux-amd64.tar.gz"
url="https://github.com/prometheus/node_exporter/releases/download/v$version/$archive"
sha256="b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63"

test_root="$(mktemp -d)"
export MERCHFACTORY_MONITORING_NETWORK="node-exporter-ci-${GITHUB_RUN_ID:-local}-$$"
export MERCHFACTORY_MONITORING_SUBNET="172.30.251.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.251.1"
export MERCHFACTORY_MONITORING_BRIDGE="mfnode$$"

node_pid=""

cleanup() {
  if [[ -n "$node_pid" ]]; then
    kill "$node_pid" >/dev/null 2>&1 || true
    wait "$node_pid" >/dev/null 2>&1 || true
  fi
  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

curl --fail --location --silent --show-error \
  "$url" \
  --output "$test_root/$archive"

printf '%s  %s\n' "$sha256" "$test_root/$archive" | sha256sum --check -

mkdir -p "$test_root/extract" "$test_root/textfile"
printf '%s\n' 'merchfactory_backup_last_success{service="ci",backup="fixture"} 1' > "$test_root/textfile/backup.prom"
tar -xzf "$test_root/$archive" \
  --strip-components=1 \
  -C "$test_root/extract"

binary="$test_root/extract/node_exporter"
[[ -x "$binary" ]]

version_output="$("$binary" --version 2>&1)"
grep -q "version $version" <<<"$version_output"

bash platform/network/scripts/prepare-monitoring-network.sh \
  "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null

network_json="$test_root/network.json"
docker network inspect "$MERCHFACTORY_MONITORING_NETWORK" > "$network_json"

python3 - "$network_json" <<'PY'
import json
import pathlib
import sys

network = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))[0]
assert network["Driver"] == "bridge", network
assert network["Internal"] is True, network
assert network["IPAM"]["Config"][0]["Subnet"] == "172.30.251.0/24", network
assert network["IPAM"]["Config"][0]["Gateway"] == "172.30.251.1", network
assert network["Options"]["com.docker.network.bridge.name"].startswith("mfnode"), network
assert network["Labels"]["com.merchfactory.network.class"] == "monitoring", network
assert network["Labels"]["com.merchfactory.managed"] == "true", network
print("Monitoring-Netz besitzt erwartete Isolation, Gateway und Plattformlabels.")
PY

"$binary" \
  --web.listen-address="$MERCHFACTORY_MONITORING_GATEWAY:9100" \
  --no-collector.netdev.netlink \
  --collector.textfile.directory="$test_root/textfile" \
  --collector.filesystem.mount-points-exclude='^/(dev|proc|sys|var/lib/docker/.+)($|/)' \
  >"$test_root/node-exporter.log" 2>&1 &
node_pid="$!"

for attempt in {1..30}; do
  if curl --fail --silent --show-error --noproxy '*' \
    "http://$MERCHFACTORY_MONITORING_GATEWAY:9100/metrics" \
    > "$test_root/metrics.txt"; then
    break
  fi

  if ! kill -0 "$node_pid" >/dev/null 2>&1; then
    cat "$test_root/node-exporter.log" >&2
    echo "Node Exporter wurde unerwartet beendet." >&2
    exit 1
  fi

  if [[ "$attempt" -eq 30 ]]; then
    cat "$test_root/node-exporter.log" >&2
    echo "Node Exporter wurde nicht erreichbar." >&2
    exit 1
  fi
  sleep 1
done

if curl --fail --silent --max-time 1 --noproxy '*' \
  http://127.0.0.1:9100/metrics >/dev/null 2>&1; then
  echo "Node Exporter darf nicht auf 127.0.0.1:9100 lauschen." >&2
  exit 1
fi

listener="$(ss -ltnH 'sport = :9100')"
grep -q "$MERCHFACTORY_MONITORING_GATEWAY:9100" <<<"$listener"
if grep -Eq '(^|[[:space:]])0\.0\.0\.0:9100|\[::\]:9100' <<<"$listener"; then
  echo "Node Exporter lauscht unerwartet global: $listener" >&2
  exit 1
fi

for metric in \
  node_cpu_seconds_total \
  node_memory_MemAvailable_bytes \
  node_filesystem_avail_bytes \
  node_network_receive_bytes_total \
  node_boot_time_seconds \
  node_time_seconds \
  merchfactory_backup_last_success; do
  grep -q "^$metric" "$test_root/metrics.txt" || {
    echo "Kernmetrik fehlt: $metric" >&2
    exit 1
  }
done

grep -Fq 'node_scrape_collector_success{collector="netdev"} 1' "$test_root/metrics.txt" || {
  echo "netdev-Collector liefert keine erfolgreichen Netzwerkmetriken." >&2
  exit 1
}

prometheus_image="$(
  docker compose \
    -f deployment/monitoring/prometheus/compose.yaml \
    config --format json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["prometheus"]["image"])'
)"

docker pull "$prometheus_image" >/dev/null

docker run --rm \
  --network "$MERCHFACTORY_MONITORING_NETWORK" \
  --entrypoint /bin/sh \
  "$prometheus_image" \
  -c "wget -q -O - http://$MERCHFACTORY_MONITORING_GATEWAY:9100/metrics" \
  > "$test_root/container-metrics.txt"

grep -q '^node_cpu_seconds_total' "$test_root/container-metrics.txt"
grep -q '^node_memory_MemAvailable_bytes' "$test_root/container-metrics.txt"

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  check rules /etc/prometheus/rules/node-exporter.yml

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  test rules /etc/prometheus/rules/tests/node-exporter.test.yml

echo "Node Exporter erfolgreich verifiziert: Release, Bind-Isolation, Kernmetriken und Alerts."
