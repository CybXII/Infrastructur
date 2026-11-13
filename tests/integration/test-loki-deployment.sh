#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

compose_file="deployment/monitoring/loki/compose.yaml"
project="loki-integration-$$"
test_root="$(mktemp -d)"

export LOKI_DATA_DIR="$test_root/data"
export MERCHFACTORY_MONITORING_NETWORK="merchfactory-monitoring-loki-${GITHUB_RUN_ID:-local}-$$"
export MERCHFACTORY_MONITORING_SUBNET="172.30.252.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.252.1"
export LOKI_MONITORING_IP="172.30.252.10"
export MERCHFACTORY_MONITORING_BRIDGE="mfloki$((RANDOM % 9000 + 1000))"

cleanup() {
  docker compose -p "$project" -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
  sudo rm -rf "$test_root"
}
trap cleanup EXIT

mkdir -p "$LOKI_DATA_DIR"
sudo chown 10001:10001 "$LOKI_DATA_DIR"
sudo chmod 0750 "$LOKI_DATA_DIR"

bash platform/network/scripts/prepare-monitoring-network.sh "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null

python3 scripts/validate-compose-standards.py "$compose_file"
python3 scripts/validate-image-policy.py "$compose_file"

docker compose -p "$project" -f "$compose_file" config >/dev/null

image_ref="$(
  docker compose -p "$project" -f "$compose_file" config --format json     | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["loki"]["image"])'
)"

docker pull "$image_ref" >/dev/null

actual_repo_digest="$(
  docker image inspect "$image_ref"     --format '{{range .RepoDigests}}{{println .}}{{end}}'     | grep '^grafana/loki@sha256:'     | head -n1
)"
[[ "$actual_repo_digest" == "grafana/loki@sha256:d70e4659623f3e109af669cae76fe2a5dd5be54e2298fe8aed380d982fbc2500" ]]

runtime_uid="$(docker image inspect "$image_ref" --format '{{.Config.User}}')"
[[ "$runtime_uid" == "10001" || "$runtime_uid" == "10001:10001" ]]

docker compose -p "$project" -f "$compose_file" up -d

container_id="$(docker compose -p "$project" -f "$compose_file" ps -q loki)"
[[ -n "$container_id" ]]

for attempt in {1..45}; do
  state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
  if [[ "$state" == "running" && "$health" == "healthy" ]]; then
    break
  fi
  if [[ "$attempt" -eq 45 ]]; then
    echo "Loki wurde nicht healthy: state=$state health=$health" >&2
    docker inspect "$container_id" >&2 || true
    docker compose -p "$project" -f "$compose_file" logs >&2 || true
    exit 1
  fi
  sleep 1
done

published_ports="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$container_id")"
if [[ "$published_ports" != "null" && "$published_ports" != "{}" ]]; then
  echo "Loki darf keine direkten Host-Ports besitzen: $published_ports" >&2
  exit 1
fi

networks="$(
  docker inspect "$container_id"     | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin)[0]["NetworkSettings"]["Networks"])))'
)"
[[ "$networks" == "$MERCHFACTORY_MONITORING_NETWORK" ]]

loki_ip="$(
  docker inspect "$container_id"     | python3 -c 'import json,sys; d=json.load(sys.stdin)[0]["NetworkSettings"]["Networks"]; print(next(iter(d.values()))["IPAddress"])'
)"
[[ "$loki_ip" == "$LOKI_MONITORING_IP" ]] || {
  echo "Loki besitzt unerwartete Monitoring-IP: $loki_ip" >&2
  exit 1
}

prometheus_image="$(
  docker compose -f deployment/monitoring/prometheus/compose.yaml config --format json     | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["prometheus"]["image"])'
)"
docker pull "$prometheus_image" >/dev/null

for attempt in {1..45}; do
  ready="$(
    docker run --rm       --network "$MERCHFACTORY_MONITORING_NETWORK"       --entrypoint /bin/sh       "$prometheus_image"       -c 'wget -q -O - http://loki:3100/ready' 2>/dev/null || true
  )"
  if grep -qi 'ready' <<<"$ready"; then
    break
  fi
  if [[ "$attempt" -eq 45 ]]; then
    echo "Loki Readiness-Endpunkt wurde nicht bereit." >&2
    docker compose -p "$project" -f "$compose_file" logs >&2 || true
    exit 1
  fi
  sleep 1
done

timestamp_ns="$(date +%s%N)"
payload="{\"streams\":[{\"stream\":{\"environment\":\"ci\",\"host\":\"github-runner\",\"service\":\"integration\",\"component\":\"loki-test\"},\"values\":[[\"$timestamp_ns\",\"merchfactory-loki-integration\"]]}]}"

docker run --rm   --network "$MERCHFACTORY_MONITORING_NETWORK"   --entrypoint /bin/sh   "$prometheus_image"   -c "wget -q -O /dev/null --header='Content-Type: application/json' --post-data='$payload' http://loki:3100/loki/api/v1/push"

query_result="$test_root/query.json"
for attempt in {1..30}; do
  docker run --rm     --network "$MERCHFACTORY_MONITORING_NETWORK"     --entrypoint /bin/sh     "$prometheus_image"     -c "wget -q -O - 'http://loki:3100/loki/api/v1/query_range?query=%7Bservice%3D%22integration%22%7D&limit=10'"     > "$query_result"

  if python3 - "$query_result" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
result = document.get("data", {}).get("result", [])
ok = any(
    any("merchfactory-loki-integration" in value[1] for value in stream.get("values", []))
    for stream in result
)
raise SystemExit(0 if ok else 1)
PY
  then
    break
  fi

  if [[ "$attempt" -eq 30 ]]; then
    echo "Geschriebener Testlog ist nicht über Loki abfragbar." >&2
    cat "$query_result" >&2
    exit 1
  fi
  sleep 1
done

sudo test -d "$LOKI_DATA_DIR/chunks"
owner="$(stat -c '%u:%g' "$LOKI_DATA_DIR")"
[[ "$owner" == "10001:10001" ]]

old_container="$container_id"
docker compose -p "$project" -f "$compose_file" up -d --force-recreate loki
container_id="$(docker compose -p "$project" -f "$compose_file" ps -q loki)"
[[ -n "$container_id" ]]
[[ "$container_id" != "$old_container" ]]

for attempt in {1..45}; do
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
  [[ "$health" == "healthy" ]] && break
  [[ "$attempt" -eq 45 ]] && { docker compose -p "$project" -f "$compose_file" logs >&2; exit 1; }
  sleep 1
done

docker run --rm   --network "$MERCHFACTORY_MONITORING_NETWORK"   --entrypoint /bin/sh   "$prometheus_image"   -c "wget -q -O - 'http://loki:3100/loki/api/v1/query_range?query=%7Bservice%3D%22integration%22%7D&limit=10'"   > "$query_result"

python3 - "$query_result" <<'PY'
import json
import pathlib
import sys

document = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
values = [
    value[1]
    for stream in document.get("data", {}).get("result", [])
    for value in stream.get("values", [])
]
assert any("merchfactory-loki-integration" in value for value in values), document
print("Loki-Log bleibt nach Container-Recreate persistent und abfragbar.")
PY

echo "Loki erfolgreich intern, persistent, single-tenant und mit TSDB-Filesystem bereitgestellt."
