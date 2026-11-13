#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$repo_root/deployment/monitoring/alertmanager/compose.yaml"
network="alertmanager-monitoring-${GITHUB_RUN_ID:-local}-$$"
egress_network="alertmanager-egress-${GITHUB_RUN_ID:-local}-$$"
project="alertmanager-integration-$$"
workspace="$(mktemp -d)"

diagnose() {
  docker compose -p "$project" -f "$compose_file" ps -a || true
  docker compose -p "$project" -f "$compose_file" logs --no-color alertmanager || true
}

cleanup() {
  docker compose -p "$project" -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$network" "$egress_network" >/dev/null 2>&1 || true
  sudo rm -rf "$workspace"
}
trap diagnose ERR
trap cleanup EXIT

test -f "$compose_file"
test -f "$repo_root/monitoring/alertmanager/alertmanager.yml"

install -d -m 0750 "$workspace/data"
sudo chown 65534:65534 "$workspace/data"
printf '%s' 'https://discord.invalid/api/webhooks/integration-test/token' > "$workspace/discord-webhook-url"
chmod 0400 "$workspace/discord-webhook-url"
sudo chown 65534:65534 "$workspace/discord-webhook-url"
docker network create --internal --subnet 172.30.250.0/24 --gateway 172.30.250.1 "$network" >/dev/null
docker network create --subnet 172.30.251.0/29 --gateway 172.30.251.1 "$egress_network" >/dev/null

export ALERTMANAGER_DATA_DIR="$workspace/data"
export ALERTMANAGER_DISCORD_WEBHOOK_FILE="$workspace/discord-webhook-url"
export MERCHFACTORY_MONITORING_NETWORK="$network"
export MERCHFACTORY_ALERTING_EGRESS_NETWORK="$egress_network"

python3 "$repo_root/scripts/validate-compose-standards.py" "$compose_file"
python3 "$repo_root/scripts/validate-image-policy.py" "$compose_file"
docker compose -p "$project" -f "$compose_file" config >/dev/null

image_ref="$(docker compose -p "$project" -f "$compose_file" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["alertmanager"]["image"])')"
docker pull "$image_ref" >/dev/null
docker run --rm --entrypoint /bin/amtool \
  -v "$repo_root/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
  -v "$workspace/discord-webhook-url:/run/secrets/discord-webhook-url:ro" \
  "$image_ref" check-config /etc/alertmanager/alertmanager.yml

# Route selection is tested against the actual Alertmanager binary/config,
# using the invalid local webhook fixture and without delivering anything.
for entry in \
  "high discord-critical" \
  "critical discord-critical" \
  "warning discord-warning" \
  "info discord-info" \
  "unknown discord-default"; do
  read -r severity receiver <<< "$entry"
  docker run --rm --entrypoint /bin/amtool \
    -v "$repo_root/monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" \
    -v "$workspace/discord-webhook-url:/run/secrets/discord-webhook-url:ro" \
    "$image_ref" config routes test \
    --config.file=/etc/alertmanager/alertmanager.yml \
    --verify.receivers="$receiver" \
    severity="$severity" environment=development service=monitoring-e2e-test
done

docker compose -p "$project" -f "$compose_file" up -d alertmanager
container_id="$(docker compose -p "$project" -f "$compose_file" ps -q alertmanager)"
test -n "$container_id"
monitoring_ip="$(docker inspect "$container_id" --format "{{with index .NetworkSettings.Networks \"$network\"}}{{.IPAddress}}{{end}}")"
egress_ip="$(docker inspect "$container_id" --format "{{with index .NetworkSettings.Networks \"$egress_network\"}}{{.IPAddress}}{{end}}")"
test -n "$monitoring_ip"
test -n "$egress_ip"

for _ in {1..60}; do
  curl --max-time 3 -fsS "http://$monitoring_ip:9093/-/ready" >/dev/null && break
  sleep 1
done
curl --max-time 3 -fsS "http://$monitoring_ip:9093/-/ready" >/dev/null

test "$(docker inspect "$container_id" --format '{{.Config.User}}')" = 65534:65534
test "$monitoring_ip" = 172.30.250.30
[[ "$egress_ip" == 172.30.251.* ]]
default_gateway_hex="$(docker exec "$container_id" cat /proc/net/route | awk '$2 == "00000000" {print $3}')"
test "$default_gateway_hex" = 01FB1EAC
port_bindings="$(docker inspect "$container_id" --format '{{json .HostConfig.PortBindings}}')"
[[ "$port_bindings" == null || "$port_bindings" == "{}" ]]
networks="$(docker inspect "$container_id" | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin)[0]["NetworkSettings"]["Networks"])))')"
test "$networks" = "$egress_network"$'\n'"$network"

silence_id="$(docker exec "$container_id" amtool --alertmanager.url=http://127.0.0.1:9093 silence add service=integration-probe --duration=1h --author=ci --comment='persistence probe')"
test -n "$silence_id"

docker compose -p "$project" -f "$compose_file" up -d --force-recreate alertmanager
container_id="$(docker compose -p "$project" -f "$compose_file" ps -q alertmanager)"
for _ in {1..60}; do
  docker exec "$container_id" amtool --alertmanager.url=http://127.0.0.1:9093 silence query 2>/dev/null | grep -q "$silence_id" && break
  sleep 1
done
docker exec "$container_id" amtool --alertmanager.url=http://127.0.0.1:9093 silence query | grep -q "$silence_id"

owner="$(stat -c '%u:%g' "$workspace/data")"
test "$owner" = 65534:65534
echo "Alertmanager ist privat, persistent, gehärtet und nur über das dedizierte Netz ausgehend erreichbar."
