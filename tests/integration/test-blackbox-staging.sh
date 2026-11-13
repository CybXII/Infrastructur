#!/usr/bin/env bash
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
compose="deployment/monitoring/blackbox/compose.staging.yaml"
project="blackbox-staging-integration-${GITHUB_RUN_ID:-local}-$$"
export MERCHFACTORY_MONITORING_NETWORK="blackbox-staging-integration-${GITHUB_RUN_ID:-local}-$$"
export MERCHFACTORY_MONITORING_SUBNET="172.30.250.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.250.1"
export MERCHFACTORY_MONITORING_BRIDGE="mf-monitoring0"

cleanup() {
  docker compose -p "$project" -f "$compose" down --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

bash platform/network/scripts/prepare-monitoring-network.sh "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null
python3 scripts/validate-compose-standards.py "$compose"
python3 scripts/validate-image-policy.py "$compose"

image="$(docker compose -p "$project" -f "$compose" config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["services"]["blackbox-exporter"]["image"])')"
docker pull "$image" >/dev/null
docker compose -p "$project" -f "$compose" up -d --no-build --pull never blackbox-exporter
container="$(docker compose -p "$project" -f "$compose" ps -q blackbox-exporter)"
test -n "$container"

health=""
for attempt in {1..45}; do
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container")"
  if [[ "$health" == "healthy" ]]; then break; fi
  if [[ "$health" == "unhealthy" ]]; then
    docker inspect "$container" >&2 || true
    docker compose -p "$project" -f "$compose" logs >&2 || true
    exit 1
  fi
  sleep 1
done
[[ "$health" == "healthy" ]] || {
  docker compose -p "$project" -f "$compose" logs >&2 || true
  echo "Staging exporter not healthy: $health" >&2
  exit 1
}

docker inspect "$container" | python3 -c '
import json,sys
v=json.load(sys.stdin)[0]
assert v["Config"]["Image"]==sys.argv[1]
assert not (v["HostConfig"].get("PortBindings") or {})
networks=v["NetworkSettings"]["Networks"]
assert set(networks)=={sys.argv[2]}, networks
assert networks[sys.argv[2]]["IPAddress"]=="172.30.250.40"
assert v["State"]["Health"]["Status"]=="healthy"
' "$image" "$MERCHFACTORY_MONITORING_NETWORK"

[[ "$(docker network inspect --format '{{.Internal}}' "$MERCHFACTORY_MONITORING_NETWORK")" == "true" ]]
curl --noproxy '*' -fsS --connect-timeout 3 --max-time 10 http://172.30.250.40:9115/-/healthy >/dev/null
echo "Blackbox internal-only staging healthy, no public egress and no host ports."
