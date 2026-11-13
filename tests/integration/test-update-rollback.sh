#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
compose_file="$test_root/compose.yaml"
state_file="$test_root/state.json"
release_env="$test_root/release.env"
project_name="release-rollback-$$"
service_name="release-test"
host_port=18084

good_image="docker.io/traefik/whoami@sha256:c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44"
bad_image="docker.io/library/traefik@sha256:f86a2cab1b5c649070c49f883c743dd32d8485a56e3368c5f93b9e91f1e91259"

cleanup() {
  if [[ -f "$release_env" ]]; then
    docker compose \
      --env-file "$release_env" \
      -p "$project_name" \
      -f "$compose_file" \
      down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf "$test_root"
}
trap cleanup EXIT

cat > "$compose_file" <<YAML
services:
  $service_name:
    image: \${CUSTOM_IMAGE_REFERENCE}
    restart: unless-stopped
    ports:
      - "127.0.0.1:$host_port:80"
YAML

common_args=(
  --compose-file "$compose_file"
  --project-name "$project_name"
  --service "$service_name"
  --state-file "$state_file"
  --release-env "$release_env"
  --environment development
  --image-env-key CUSTOM_IMAGE_REFERENCE
  --verify-url "http://127.0.0.1:$host_port/health"
  --verify-attempts 15
  --verify-interval 0.5
  --verify-timeout 1
)

python3 deployment/service-release.py deploy \
  "${common_args[@]}" \
  --target-image "$good_image" \
  --source-revision test-good \
  --release-reference ci:good

python3 - "$state_file" "$good_image" <<'PY'
import json
import pathlib
import sys

state = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = sys.argv[2]

assert state["current"]["image"] == expected, state
assert state["last_attempt"]["status"] == "success", state
print("Bekannte gute Version erfolgreich als Deployment-State gespeichert.")
PY

curl --fail --silent --show-error \
  "http://127.0.0.1:$host_port/health" >/dev/null

set +e
python3 deployment/service-release.py deploy \
  "${common_args[@]}" \
  --target-image "$bad_image" \
  --source-revision test-bad \
  --release-reference ci:bad
failed_status=$?
set -e

if [[ "$failed_status" -eq 0 ]]; then
  echo "Fehlerhaftes Update wurde unerwartet als erfolgreich gemeldet." >&2
  exit 1
fi

python3 - "$state_file" "$release_env" "$good_image" "$bad_image" <<'PY'
import json
import pathlib
import sys

state_path = pathlib.Path(sys.argv[1])
env_path = pathlib.Path(sys.argv[2])
good = sys.argv[3]
bad = sys.argv[4]

state = json.loads(state_path.read_text(encoding="utf-8"))
env = env_path.read_text(encoding="utf-8").strip()

assert state["current"]["image"] == good, state
assert state["last_attempt"]["status"] == "failed-rolled-back", state
assert state["last_attempt"]["attempted_image"] == bad, state
assert state["last_attempt"]["rollback_image"] == good, state
assert env == f"CUSTOM_IMAGE_REFERENCE={good}", env

print("Deployment-State und release.env stehen nach Fehler wieder auf der guten Version.")
PY

container_id="$(
  docker compose \
    --env-file "$release_env" \
    -p "$project_name" \
    -f "$compose_file" \
    ps -q "$service_name"
)"

[[ -n "$container_id" ]]

actual_image="$(docker inspect --format '{{.Config.Image}}' "$container_id")"
if [[ "$actual_image" != "$good_image" ]]; then
  echo "Rollback-Container verwendet falsches Image: $actual_image" >&2
  exit 1
fi

curl --fail --silent --show-error \
  "http://127.0.0.1:$host_port/health" >/dev/null

python3 deployment/service-release.py status \
  --state-file "$state_file" >/dev/null

echo "Fehlgeschlagenes Update wurde auf den letzten bekannten guten Digest zurückgerollt und erfolgreich verifiziert."
