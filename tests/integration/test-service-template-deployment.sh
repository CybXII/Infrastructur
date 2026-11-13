#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
rendered="$test_root/template-smoke"
edge_network="merchfactory-template-test-${GITHUB_RUN_ID:-local}-$$"
project_name="template-smoke-$$"

cleanup() {
  if [[ -f "$rendered/deployment/compose.yaml" && -f "$test_root/compose.test.yaml" ]]; then
    docker compose \
      -p "$project_name" \
      -f "$rendered/deployment/compose.yaml" \
      -f "$test_root/compose.test.yaml" \
      down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  docker network rm "$edge_network" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

python3 scripts/render-service-template.py \
  --output "$rendered" \
  --set SERVICE_NAME=template-smoke \
  --set IMAGE_REFERENCE=docker.io/traefik/whoami@sha256:c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44 \
  --set CONTAINER_PORT=80 \
  --set PUBLIC_HOSTNAME=template-smoke.example.invalid \
  --set 'HEALTHCHECK_COMMAND=true' \
  --set READINESS_PATH=/health \
  --set SERVICE_UID="$(id -u)" \
  --set SERVICE_GID="$(id -g)" \
  --set OWNER=platform-team \
  --set ESCALATION_CONTACT=platform-oncall \
  >/dev/null

required=(
  README.md
  configuration/service.yaml
  configuration/secrets.yaml
  deployment/compose.yaml
  routing/route.yaml
  monitoring/healthcheck.yaml
  logging/policy.yaml
  backup/policy.yaml
  operations/runbook.md
)

for path in "${required[@]}"; do
  [[ -f "$rendered/$path" ]] || {
    echo "Gerenderte Datei fehlt: $path" >&2
    exit 1
  }
done

if grep -R -nE '\{\{[A-Z][A-Z0-9_]*\}\}' "$rendered"; then
  echo "Gerendertes Template enthält noch Platzhalter." >&2
  exit 1
fi

grep -q 'SERVICE_IMAGE_REFERENCE' "$rendered/deployment/compose.yaml"
grep -q 'template-smoke.example.invalid' "$rendered/routing/route.yaml"
grep -q 'http://template-smoke:80' "$rendered/routing/route.yaml"
grep -q 'path: "/health"' "$rendered/routing/route.yaml"
grep -q 'interval: "10s"' "$rendered/routing/route.yaml"
grep -q 'timeout: "3s"' "$rendered/routing/route.yaml"
grep -q '/run/secrets/primary-secret' "$rendered/configuration/secrets.yaml"
grep -q 'driver: local' "$rendered/logging/policy.yaml"
grep -q 'max_size: 20m' "$rendered/logging/policy.yaml"
grep -q 'max_files: 5' "$rendered/logging/policy.yaml"
grep -q 'compress: true' "$rendered/logging/policy.yaml"
grep -q 'standard_days: 30' "$rendered/logging/policy.yaml"
grep -q 'security_days: 365' "$rendered/logging/policy.yaml"

mkdir -p "$test_root/data"
printf '%s' 'MF_TEMPLATE_TEST_SECRET' > "$test_root/primary-secret"
chmod 0600 "$test_root/primary-secret"

export SERVICE_DATA_DIR="$test_root/data"
export PRIMARY_SECRET_FILE="$test_root/primary-secret"
export MERCHFACTORY_EDGE_NETWORK="$edge_network"

python3 scripts/validate-compose-standards.py "$rendered/deployment/compose.yaml"
python3 scripts/validate-image-policy.py "$rendered/deployment/compose.yaml"

bash platform/network/scripts/prepare-edge-network.sh "$edge_network" >/dev/null

cat > "$test_root/compose.test.yaml" <<'YAML'
services:
  template-smoke:
    ports:
      - "127.0.0.1:18083:80"
    healthcheck:
      disable: true
YAML

docker compose \
  -p "$project_name" \
  -f "$rendered/deployment/compose.yaml" \
  -f "$test_root/compose.test.yaml" \
  config >/dev/null

docker compose \
  -p "$project_name" \
  -f "$rendered/deployment/compose.yaml" \
  -f "$test_root/compose.test.yaml" \
  pull

docker compose \
  -p "$project_name" \
  -f "$rendered/deployment/compose.yaml" \
  -f "$test_root/compose.test.yaml" \
  up -d

for attempt in {1..30}; do
  status="$(
    curl --silent --output /dev/null --write-out '%{http_code}' \
      http://127.0.0.1:18083/health || true
  )"
  if [[ "$status" == "200" ]]; then
    break
  fi

  if [[ "$attempt" -eq 30 ]]; then
    docker compose \
      -p "$project_name" \
      -f "$rendered/deployment/compose.yaml" \
      -f "$test_root/compose.test.yaml" \
      ps
    docker compose \
      -p "$project_name" \
      -f "$rendered/deployment/compose.yaml" \
      -f "$test_root/compose.test.yaml" \
      logs
    echo "Gerenderte Beispielbereitstellung wurde nicht erreichbar." >&2
    exit 1
  fi

  sleep 1
done

container_id="$(
  docker compose \
    -p "$project_name" \
    -f "$rendered/deployment/compose.yaml" \
    -f "$test_root/compose.test.yaml" \
    ps -q template-smoke
)"

[[ -n "$container_id" ]]
[[ "$(docker inspect --format '{{.State.Running}}' "$container_id")" == "true" ]]

python3 - "$container_id" <<'PY'
import json
import subprocess
import sys

container_id = sys.argv[1]
host_config = json.loads(
    subprocess.run(
        ["docker", "inspect", container_id],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
)[0]["HostConfig"]

expected = {
    "NanoCpus": 1_000_000_000,
    "CpuShares": 512,
    "Memory": 512 * 1024 * 1024,
    "MemoryReservation": 256 * 1024 * 1024,
    "PidsLimit": 256,
}

for key, value in expected.items():
    if host_config.get(key) != value:
        raise SystemExit(
            f"Template-Ressource {key}: actual={host_config.get(key)!r}, expected={value!r}"
        )

print("Gerenderte Resource-Defaults wurden von Docker korrekt übernommen.")
PY

echo "Standard-Service-Template erfolgreich gerendert, validiert und bereitgestellt."
