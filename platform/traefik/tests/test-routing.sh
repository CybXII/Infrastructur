#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo_root"

compose_args=(
  -f platform/traefik/compose.yaml
  -f platform/traefik/tests/compose.test.yaml
)

test_dynamic_config="platform/traefik/config/dynamic/99-example-route.test.yaml"
test_cert="platform/traefik/config/dynamic/98-example-cert.test.pem"
test_key="platform/traefik/config/dynamic/98-example-key.test.pem"
test_root="$(mktemp -d)"
export TRAEFIK_ACME_DIR="${test_root}/acme"
export MERCHFACTORY_EDGE_NETWORK="merchfactory-edge-test-${GITHUB_RUN_ID:-local}-$$"

cleanup() {
  rm -f "$test_dynamic_config" "$test_cert" "$test_key"
  docker compose "${compose_args[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker network rm "$MERCHFACTORY_EDGE_NETWORK" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

platform/traefik/scripts/prepare-acme-storage.sh "$TRAEFIK_ACME_DIR" >/dev/null
bash platform/network/scripts/prepare-edge-network.sh "$MERCHFACTORY_EDGE_NETWORK" >/dev/null

[[ "$(stat -c '%a' "$TRAEFIK_ACME_DIR")" == "700" ]]
[[ "$(stat -c '%a' "$TRAEFIK_ACME_DIR/acme.json")" == "600" ]]
[[ "$(docker network inspect --format '{{.Driver}}' "$MERCHFACTORY_EDGE_NETWORK")" == "bridge" ]]
[[ "$(docker network inspect --format '{{.Internal}}' "$MERCHFACTORY_EDGE_NETWORK")" == "false" ]]
[[ "$(docker network inspect --format '{{ index .Labels "com.merchfactory.network.class" }}' "$MERCHFACTORY_EDGE_NETWORK")" == "edge" ]]
[[ "$(docker network inspect --format '{{ index .Labels "com.merchfactory.managed" }}' "$MERCHFACTORY_EDGE_NETWORK")" == "true" ]]

# Idempotenz des hostweiten Edge-Netzes prüfen.
bash platform/network/scripts/prepare-edge-network.sh "$MERCHFACTORY_EDGE_NETWORK" >/dev/null

cp platform/traefik/tests/example-route.yaml "$test_dynamic_config"

openssl req \
  -x509 \
  -newkey rsa:2048 \
  -nodes \
  -days 1 \
  -subj "/CN=example.localhost" \
  -addext "subjectAltName=DNS:example.localhost" \
  -keyout "$test_key" \
  -out "$test_cert" \
  >/dev/null 2>&1
chmod 0600 "$test_key"
chmod 0644 "$test_cert"

export TRAEFIK_HTTP_BIND="127.0.0.1:18080"
export TRAEFIK_HTTPS_BIND="127.0.0.1:18443"
export TRAEFIK_ADMIN_BIND="127.0.0.1:18081"

compose_json="$(docker compose "${compose_args[@]}" config --format json)"
app_network="$(printf '%s' "$compose_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["networks"]["app"]["name"])')"
data_network="$(printf '%s' "$compose_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["networks"]["data"]["name"])')"
edge_network="$(printf '%s' "$compose_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["networks"]["edge"]["name"])')"

[[ "$edge_network" == "$MERCHFACTORY_EDGE_NETWORK" ]]

docker compose "${compose_args[@]}" pull
docker compose "${compose_args[@]}" up -d

for attempt in {1..30}; do
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$(docker compose "${compose_args[@]}" ps -q traefik)")"
  if [[ "$health" == "healthy" ]]; then
    break
  fi

  if [[ "$attempt" -eq 30 ]]; then
    docker compose "${compose_args[@]}" ps
    docker compose "${compose_args[@]}" logs
    echo "Traefik wurde nicht healthy." >&2
    exit 1
  fi

  sleep 2
done

assert_network_internal() {
  local network="$1"
  local expected="$2"
  local actual

  actual="$(docker network inspect --format '{{.Internal}}' "$network")"
  if [[ "$actual" != "$expected" ]]; then
    echo "Netzwerk $network: internal=$actual, erwartet $expected." >&2
    exit 1
  fi
}

assert_container_networks() {
  local container_id="$1"
  shift

  python3 - "$container_id" "$@" <<'PY'
import json
import subprocess
import sys

container_id = sys.argv[1]
expected = set(sys.argv[2:])
document = json.loads(
    subprocess.run(
        ["docker", "inspect", container_id],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
)
actual = set(document[0]["NetworkSettings"]["Networks"])

if actual != expected:
    print(
        "Unerwartete Netzwerkmitgliedschaft für "
        f"{container_id[:12]}: actual={sorted(actual)}, expected={sorted(expected)}",
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
}

assert_network_internal "$app_network" "true"
assert_network_internal "$data_network" "true"

traefik_container_id="$(docker compose "${compose_args[@]}" ps -q traefik)"
example_container_id="$(docker compose "${compose_args[@]}" ps -q example-service)"
worker_container_id="$(docker compose "${compose_args[@]}" ps -q internal-worker)"
data_container_id="$(docker compose "${compose_args[@]}" ps -q data-service)"

assert_container_networks "$traefik_container_id" "$edge_network"
assert_container_networks "$example_container_id" "$app_network" "$edge_network"
assert_container_networks "$worker_container_id" "$app_network" "$data_network"
assert_container_networks "$data_container_id" "$data_network"

redirect_headers="$(mktemp)"
response_headers="$(mktemp)"
response_body="$(mktemp)"
trap 'rm -f "$redirect_headers" "$response_headers" "$response_body"; cleanup' EXIT

http_status="$(curl --silent --output /dev/null --dump-header "$redirect_headers" --write-out '%{http_code}' \
  --header 'Host: example.localhost' \
  http://127.0.0.1:18080/)"

if [[ "$http_status" != "301" && "$http_status" != "308" ]]; then
  echo "HTTP wurde nicht permanent auf HTTPS umgeleitet: HTTP $http_status" >&2
  exit 1
fi

grep -qi '^Location: https://example.localhost' "$redirect_headers"

curl --fail --silent --show-error --insecure \
  --resolve example.localhost:18443:127.0.0.1 \
  --dump-header "$response_headers" \
  --output "$response_body" \
  https://example.localhost:18443/

grep -qi '^X-Merchfactory-Proxy: traefik' "$response_headers"
grep -q 'Host: example.localhost' "$response_body"

# Readiness gezielt auf Fehler setzen und prüfen, dass Traefik das Backend
# aus der Rotation nimmt. Der Docker-Liveness-Zustand bleibt davon getrennt.
example_edge_ip="$(
  docker inspect \
    --format "{{(index .NetworkSettings.Networks \"$edge_network\").IPAddress}}" \
    "$example_container_id"
)"

curl --fail --silent --show-error \
  --request POST \
  --data '500' \
  "http://$example_edge_ip/health" >/dev/null

for attempt in {1..15}; do
  readiness_status="$(
    curl --silent --insecure \
      --resolve example.localhost:18443:127.0.0.1 \
      --output /dev/null \
      --write-out '%{http_code}' \
      https://example.localhost:18443/ || true
  )"

  if [[ "$readiness_status" == "503" ]]; then
    break
  fi

  if [[ "$attempt" -eq 15 ]]; then
    echo "Traefik hat das nicht bereite Backend nicht aus der Rotation genommen: HTTP $readiness_status" >&2
    exit 1
  fi

  sleep 1
done

curl --fail --silent --show-error \
  --request POST \
  --data '200' \
  "http://$example_edge_ip/health" >/dev/null

for attempt in {1..15}; do
  recovery_status="$(
    curl --silent --insecure \
      --resolve example.localhost:18443:127.0.0.1 \
      --output /dev/null \
      --write-out '%{http_code}' \
      https://example.localhost:18443/ || true
  )"

  if [[ "$recovery_status" == "200" ]]; then
    break
  fi

  if [[ "$attempt" -eq 15 ]]; then
    echo "Traefik hat das wieder bereite Backend nicht erneut aufgenommen: HTTP $recovery_status" >&2
    exit 1
  fi

  sleep 1
done

web_dashboard_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --header 'Host: dashboard.localhost' \
  http://127.0.0.1:18080/dashboard/)"
if [[ "$web_dashboard_status" != "301" && "$web_dashboard_status" != "308" ]]; then
  echo "Web-Entrypoint sollte ausschließlich auf HTTPS umleiten: HTTP $web_dashboard_status" >&2
  exit 1
fi

admin_dashboard_status="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  http://127.0.0.1:18081/dashboard/)"
if [[ "$admin_dashboard_status" != "200" ]]; then
  echo "Dashboard ist über den lokalen Admin-Entrypoint nicht erreichbar: HTTP $admin_dashboard_status" >&2
  exit 1
fi

for service in example-service internal-worker data-service; do
  service_container_id="$(docker compose "${compose_args[@]}" ps -q "$service")"
  published_ports="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$service_container_id")"

  if [[ "$published_ports" != "null" && "$published_ports" != "{}" ]]; then
    echo "$service darf keine direkten Host-Port-Bindings besitzen: $published_ports" >&2
    exit 1
  fi
done

backup_target="$(platform/traefik/scripts/backup-acme-storage.sh \
  "$TRAEFIK_ACME_DIR/acme.json" \
  "$test_root/backups")"

[[ -f "$backup_target" ]]
[[ -f "${backup_target}.sha256" ]]
[[ "$(stat -c '%a' "$backup_target")" == "600" ]]
(
  cd "$(dirname "$backup_target")"
  sha256sum --check "$(basename "$backup_target").sha256"
)

printf '%s\n' '{"level":"info","msg":"ACME certificate renewed successfully"}' \
  | python3 platform/traefik/scripts/check-acme-errors.py

if printf '%s\n' '{"level":"error","msg":"Unable to obtain ACME certificate: renewal failed"}' \
  | python3 platform/traefik/scripts/check-acme-errors.py; then
  echo "ACME-Fehlerdetektor hätte fehlschlagen müssen." >&2
  exit 1
fi

docker compose "${compose_args[@]}" logs --no-color traefik \
  | python3 platform/traefik/scripts/check-acme-errors.py

echo "Traefik TLS, ACME, Readiness und segmentierte Docker-Netzwerke erfolgreich geprüft."
