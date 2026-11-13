#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

service_compose="examples/services/reference-http-service/deployment/compose.yaml"
service_project="reference-service-test-$$"
proxy_project="reference-proxy-test-$$"

test_root="$(mktemp -d)"
data_dir="$test_root/data"
export REFERENCE_SERVICE_DATA_DIR="$data_dir"
export TRAEFIK_ACME_DIR="$test_root/acme"
export MERCHFACTORY_EDGE_NETWORK="merchfactory-reference-edge-${GITHUB_RUN_ID:-local}-$$"
export TRAEFIK_HTTP_BIND="127.0.0.1:18085"
export TRAEFIK_HTTPS_BIND="127.0.0.1:18445"
export TRAEFIK_ADMIN_BIND="127.0.0.1:18086"

test_dynamic_config="platform/traefik/config/dynamic/97-reference-service.test.yaml"
test_cert="platform/traefik/config/dynamic/96-reference-service-cert.test.pem"
test_key="platform/traefik/config/dynamic/96-reference-service-key.test.pem"

cleanup() {
  docker compose \
    -p "$service_project" \
    -f "$service_compose" \
    down --volumes --remove-orphans >/dev/null 2>&1 || true

  docker compose \
    -p "$proxy_project" \
    -f platform/traefik/compose.yaml \
    down --volumes --remove-orphans >/dev/null 2>&1 || true

  docker network rm "$MERCHFACTORY_EDGE_NETWORK" >/dev/null 2>&1 || true
  rm -f "$test_dynamic_config" "$test_cert" "$test_key"
  rm -rf "$test_root"
}
trap cleanup EXIT

mkdir -p "$data_dir"
chmod 0750 "$data_dir"

platform/traefik/scripts/prepare-acme-storage.sh "$TRAEFIK_ACME_DIR" >/dev/null
bash platform/network/scripts/prepare-edge-network.sh "$MERCHFACTORY_EDGE_NETWORK" >/dev/null

python3 scripts/validate-compose-standards.py "$service_compose"
python3 scripts/validate-image-policy.py "$service_compose"

cat > "$test_dynamic_config" <<'YAML'
tls:
  certificates:
    - certFile: /etc/traefik/dynamic/96-reference-service-cert.test.pem
      keyFile: /etc/traefik/dynamic/96-reference-service-key.test.pem

http:
  routers:
    reference-http-service:
      rule: "Host(`reference-service.localhost`)"
      entryPoints:
        - websecure
      service: reference-http-service
      tls: {}

  services:
    reference-http-service:
      loadBalancer:
        healthCheck:
          path: /health
          interval: "1s"
          timeout: "500ms"
          status: 200
        servers:
          - url: "http://reference-http-service:8080"
YAML

openssl req \
  -x509 \
  -newkey rsa:2048 \
  -nodes \
  -days 1 \
  -subj "/CN=reference-service.localhost" \
  -addext "subjectAltName=DNS:reference-service.localhost" \
  -keyout "$test_key" \
  -out "$test_cert" \
  >/dev/null 2>&1
chmod 0600 "$test_key"
chmod 0644 "$test_cert"

docker compose \
  -p "$proxy_project" \
  -f platform/traefik/compose.yaml \
  pull

docker compose \
  -p "$service_project" \
  -f "$service_compose" \
  pull

docker compose \
  -p "$proxy_project" \
  -f platform/traefik/compose.yaml \
  up -d

docker compose \
  -p "$service_project" \
  -f "$service_compose" \
  up -d

wait_for_healthy() {
  local container_id="$1"
  local label="$2"

  for attempt in {1..30}; do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
    if [[ "$health" == "healthy" ]]; then
      return 0
    fi

    if [[ "$attempt" -eq 30 ]]; then
      echo "$label wurde nicht healthy; letzter Status: $health" >&2
      docker inspect "$container_id" >&2 || true
      return 1
    fi

    sleep 1
  done
}

proxy_container="$(
  docker compose -p "$proxy_project" -f platform/traefik/compose.yaml ps -q traefik
)"
service_container="$(
  docker compose -p "$service_project" -f "$service_compose" ps -q reference-http-service
)"

[[ -n "$proxy_container" ]]
[[ -n "$service_container" ]]

wait_for_healthy "$proxy_container" "Traefik"
wait_for_healthy "$service_container" "Reference HTTP Service"

published_ports="$(docker inspect --format '{{json .HostConfig.PortBindings}}' "$service_container")"
if [[ "$published_ports" != "null" && "$published_ports" != "{}" ]]; then
  echo "Reference HTTP Service darf keine direkten Host-Ports besitzen: $published_ports" >&2
  exit 1
fi

http_status="$(
  curl --silent \
    --header 'Host: reference-service.localhost' \
    --output /dev/null \
    --write-out '%{http_code}' \
    http://127.0.0.1:18085/
)"

if [[ "$http_status" != "301" && "$http_status" != "308" ]]; then
  echo "HTTP wurde nicht permanent auf HTTPS umgeleitet: HTTP $http_status" >&2
  exit 1
fi

for attempt in {1..20}; do
  https_status="$(
    curl --silent --insecure \
      --resolve reference-service.localhost:18445:127.0.0.1 \
      --output /dev/null \
      --write-out '%{http_code}' \
      https://reference-service.localhost:18445/health || true
  )"

  if [[ "$https_status" == "200" ]]; then
    break
  fi

  if [[ "$attempt" -eq 20 ]]; then
    echo "HTTPS-Healthcheck über Traefik fehlgeschlagen: HTTP $https_status" >&2
    docker compose -p "$proxy_project" -f platform/traefik/compose.yaml logs >&2 || true
    docker compose -p "$service_project" -f "$service_compose" logs >&2 || true
    exit 1
  fi

  sleep 1
done

service_logs="$(
  docker compose \
    -p "$service_project" \
    -f "$service_compose" \
    logs --no-color reference-http-service
)"
grep -q 'Starting up on port 8080' <<<"$service_logs"

runtime_user="$(docker inspect --format '{{.Config.User}}' "$service_container")"
[[ "$runtime_user" == "65532:65532" ]]

marker_source="$test_root/persistence-marker.txt"
marker_restored="$test_root/persistence-marker-restored.txt"
printf '%s\n' 'merchfactory-reference-persistence-v1' > "$marker_source"

docker cp \
  "$marker_source" \
  "$service_container:/var/lib/reference-http-service/persistence-marker.txt"

[[ -f "$data_dir/persistence-marker.txt" ]]
cmp "$marker_source" "$data_dir/persistence-marker.txt"

old_container="$service_container"

docker compose \
  -p "$service_project" \
  -f "$service_compose" \
  up -d --force-recreate reference-http-service

service_container="$(
  docker compose -p "$service_project" -f "$service_compose" ps -q reference-http-service
)"

[[ -n "$service_container" ]]
[[ "$service_container" != "$old_container" ]]

wait_for_healthy "$service_container" "Reference HTTP Service nach Recreate"

docker cp \
  "$service_container:/var/lib/reference-http-service/persistence-marker.txt" \
  "$marker_restored"

cmp "$marker_source" "$marker_restored"

https_status_after_recreate="$(
  curl --silent --insecure \
    --resolve reference-service.localhost:18445:127.0.0.1 \
    --output /dev/null \
    --write-out '%{http_code}' \
    https://reference-service.localhost:18445/health
)"

[[ "$https_status_after_recreate" == "200" ]]

grep -q 'certResolver: letsencrypt' \
  examples/services/reference-http-service/routing/route.yaml

echo "Referenzservice erfolgreich über Traefik/TLS deployt; Health, Logging und Persistenz funktionieren."
