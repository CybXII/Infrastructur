#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
image="merchfactory/log-spammer:test"
container="mf-log-rotation-$$"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker image rm -f "$image" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

CGO_ENABLED=0 GOOS=linux GOARCH="$(go env GOARCH)" \
  go build -trimpath -ldflags='-s -w' \
  -o "$test_root/log-spammer" \
  tests/fixtures/log-spammer/main.go

cat > "$test_root/Dockerfile" <<'DOCKERFILE'
FROM scratch
COPY log-spammer /log-spammer
ENTRYPOINT ["/log-spammer"]
DOCKERFILE

docker build --quiet -t "$image" "$test_root" >/dev/null

docker run \
  --name "$container" \
  --log-driver local \
  --log-opt max-size=10k \
  --log-opt max-file=2 \
  --log-opt compress=false \
  "$image" >/dev/null

python3 - "$container" <<'PY'
import json
import subprocess
import sys

name = sys.argv[1]
host_config = json.loads(
    subprocess.run(
        ["docker", "inspect", name],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
)[0]["HostConfig"]["LogConfig"]

if host_config.get("Type") != "local":
    raise SystemExit(f"Unerwarteter Logging Driver: {host_config!r}")

expected = {
    "max-size": "10k",
    "max-file": "2",
    "compress": "false",
}

for key, value in expected.items():
    if host_config.get("Config", {}).get(key) != value:
        raise SystemExit(
            f"LogConfig {key}: actual={host_config.get('Config', {}).get(key)!r}, expected={value!r}"
        )

print("Docker local Logging Driver mit begrenzter Rotation aktiv.")
PY

logs="$(docker logs "$container" 2>&1)"

if ! grep -q 'MF_LOG_ROTATION_LAST_MARKER' <<<"$logs"; then
  echo "Neuester Logmarker fehlt nach Rotation." >&2
  exit 1
fi

if grep -q 'MF_LOG_ROTATION_FIRST_MARKER' <<<"$logs"; then
  echo "Ältester Logmarker wurde trotz kleiner Retention noch aufbewahrt." >&2
  exit 1
fi

log_lines="$(wc -l <<<"$logs")"
if [[ "$log_lines" -ge 6000 ]]; then
  echo "Logrotation hat den sichtbaren Logbestand nicht begrenzt." >&2
  exit 1
fi

docker info >/dev/null

echo "Docker-Logrotation erfolgreich geprüft; alter Logbestand wurde begrenzt."
