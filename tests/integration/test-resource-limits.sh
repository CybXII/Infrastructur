#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
image="merchfactory/resource-pressure:test"
cpu_container="mf-resource-cpu-$$"
pid_container="mf-resource-pids-$$"
oom_container="mf-resource-oom-$$"

cleanup() {
  docker rm -f "$cpu_container" "$pid_container" "$oom_container" >/dev/null 2>&1 || true
  docker image rm -f "$image" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

command -v go >/dev/null
go version
docker version >/dev/null

CGO_ENABLED=0 GOOS=linux GOARCH="$(go env GOARCH)" \
  go build -trimpath -ldflags='-s -w' \
  -o "$test_root/resource-pressure" \
  tests/fixtures/resource-pressure/main.go

cat > "$test_root/Dockerfile" <<'DOCKERFILE'
FROM scratch
COPY resource-pressure /resource-pressure
ENTRYPOINT ["/resource-pressure"]
DOCKERFILE

docker build --quiet -t "$image" "$test_root" >/dev/null

docker run -d \
  --name "$cpu_container" \
  --cpus 0.25 \
  --cpu-shares 256 \
  --memory 64m \
  --memory-reservation 32m \
  --pids-limit 64 \
  "$image" cpu >/dev/null

python3 - "$cpu_container" <<'PY'
import json
import subprocess
import sys

name = sys.argv[1]
document = json.loads(
    subprocess.run(
        ["docker", "inspect", name],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
)[0]["HostConfig"]

expected = {
    "NanoCpus": 250_000_000,
    "CpuShares": 256,
    "Memory": 64 * 1024 * 1024,
    "MemoryReservation": 32 * 1024 * 1024,
    "PidsLimit": 64,
}

for key, value in expected.items():
    if document.get(key) != value:
        raise SystemExit(
            f"{key}: actual={document.get(key)!r}, expected={value!r}"
        )

print("CPU-/Memory-/PID-cgroup-Limits korrekt übernommen.")
PY

docker rm -f "$cpu_container" >/dev/null

set +e
docker run \
  --name "$pid_container" \
  --memory 64m \
  --memory-reservation 32m \
  --pids-limit 24 \
  "$image" pids >/dev/null 2>&1
pid_status=$?
set -e

if [[ "$pid_status" -ne 0 ]]; then
  docker logs "$pid_container" >&2 || true
  echo "PID-Drucktest ist unerwartet fehlgeschlagen: Exit $pid_status" >&2
  exit 1
fi

if ! docker logs "$pid_container" 2>&1 | grep -q 'PID_LIMIT_REACHED'; then
  docker logs "$pid_container" >&2 || true
  echo "PID-Limit wurde im Drucktest nicht erreicht." >&2
  exit 1
fi

set +e
docker run \
  --name "$oom_container" \
  --memory 32m \
  --memory-swap 32m \
  --pids-limit 64 \
  "$image" memory >/dev/null 2>&1
oom_status=$?
set -e

oom_killed="$(docker inspect --format '{{.State.OOMKilled}}' "$oom_container")"
exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$oom_container")"

if [[ "$oom_killed" != "true" ]]; then
  if [[ "$exit_code" == "137" || "$oom_status" == "137" ]]; then
    echo "Hinweis: Docker/containerd meldet OOMKilled=false, der Druckprozess wurde aber erwartungsgemäß mit SIGKILL/Exit 137 beendet."
  else
    echo "Memory-Drucktest zeigte weder OOMKilled=true noch SIGKILL/Exit 137: OOMKilled=$oom_killed docker=$oom_status container=$exit_code" >&2
    exit 1
  fi
fi

if [[ "$exit_code" != "137" && "$oom_status" != "137" ]]; then
  echo "Unerwarteter OOM-Exit: OOMKilled=$oom_killed docker=$oom_status container=$exit_code" >&2
  exit 1
fi

docker info >/dev/null

echo "Ressourcenlimits, PID-Druck und containerlokales OOM-Verhalten erfolgreich geprüft."
