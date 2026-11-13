#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
state_root="$test_root/deployments"
policy_file="$test_root/docker-cleanup-policy.json"
lock_file="$test_root/docker-cleanup.lock"
dry_report="$test_root/dry-run.json"
blocked_report="$test_root/blocked-apply.json"
apply_report="$test_root/apply.json"

good_image="docker.io/traefik/whoami@sha256:c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44"
previous_image="docker.io/library/traefik@sha256:f86a2cab1b5c649070c49f883c743dd32d8485a56e3368c5f93b9e91f1e91259"
running_image="ghcr.io/merchfactory/cleanup-running:ci"
unused_image="ghcr.io/merchfactory/cleanup-unused:ci"

running_container="mf-cleanup-running-$$"
stopped_container="mf-cleanup-stopped-$$"
protected_container="mf-cleanup-protected-$$"
volume_name="mf-cleanup-volume-$$"

cleanup() {
  docker rm -f "$running_container" "$stopped_container" "$protected_container" >/dev/null 2>&1 || true
  docker volume rm "$volume_name" >/dev/null 2>&1 || true
  docker image rm -f "$running_image" "$unused_image" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

mkdir -p "$state_root/service-a" "$test_root/build"

docker pull "$good_image" >/dev/null
docker pull "$previous_image" >/dev/null

cat > "$state_root/service-a/state.json" <<JSON
{
  "version": 1,
  "service": "service-a",
  "project": "service-a",
  "current": {
    "image": "$good_image"
  },
  "previous": [
    {
      "image": "$previous_image"
    }
  ],
  "last_attempt": {
    "status": "failed-manual-intervention-required"
  }
}
JSON

python3 - "$policy_file" <<'PY'
import json
import pathlib
import sys

source = pathlib.Path("configuration/docker-cleanup-policy.json")
target = pathlib.Path(sys.argv[1])
policy = json.loads(source.read_text(encoding="utf-8"))
policy["retention"]["stopped_managed_containers_days"] = 0
policy["retention"]["unused_allowed_images_days"] = 0
policy["retention"]["dangling_images_days"] = 0
policy["retention"]["build_cache_retention"] = "1s"
target.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
PY

CGO_ENABLED=0 GOOS=linux GOARCH="$(go env GOARCH)" \
  go build -trimpath -ldflags='-s -w' \
  -o "$test_root/build/cleanup-sleeper" \
  tests/fixtures/cleanup-sleeper/main.go

cat > "$test_root/build/Dockerfile" <<'DOCKERFILE'
FROM scratch
ARG VARIANT
LABEL com.merchfactory.cleanup.fixture="${VARIANT}"
COPY cleanup-sleeper /cleanup-sleeper
ENTRYPOINT ["/cleanup-sleeper"]
DOCKERFILE

docker build \
  --quiet \
  --build-arg VARIANT=running \
  -t "$running_image" \
  "$test_root/build" >/dev/null

docker build \
  --quiet \
  --build-arg VARIANT=old-unused \
  -t "$unused_image" \
  "$test_root/build" >/dev/null

dangling_image_id="$(docker image inspect --format '{{.Id}}' "$unused_image")"

docker build \
  --quiet \
  --build-arg VARIANT=new-unused \
  -t "$unused_image" \
  "$test_root/build" >/dev/null

unused_image_id="$(docker image inspect --format '{{.Id}}' "$unused_image")"

if [[ "$dangling_image_id" == "$unused_image_id" ]]; then
  echo "Test konnte kein Dangling-Vorgängerimage erzeugen." >&2
  exit 1
fi

docker run -d \
  --name "$running_container" \
  --label com.merchfactory.managed=true \
  "$running_image" >/dev/null

docker create \
  --name "$stopped_container" \
  --label com.merchfactory.managed=true \
  "$unused_image" >/dev/null

docker create \
  --name "$protected_container" \
  --label com.merchfactory.managed=true \
  --label com.merchfactory.cleanup.protect=true \
  "$good_image" >/dev/null

docker volume create "$volume_name" >/dev/null

sleep 2

common_args=(
  --policy "$policy_file"
  --image-policy configuration/container-image-policy.json
  --deployment-state-root "$state_root"
  --lock-file "$lock_file"
)

python3 scripts/docker-retention-cleanup.py \
  "${common_args[@]}" \
  --report "$dry_report" >/dev/null

python3 - "$dry_report" <<'PY'
import json
import pathlib
import sys

report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["mode"] == "dry-run", report
assert report["status"] == "dry-run", report
assert report["cleanup_allowed"] is False, report
assert report["containers"]["count"] >= 1, report
assert report["images"]["count"] >= 1, report
assert report["volumes"]["action"] == "none", report
print("Dry-Run plant Cleanup ohne Änderungen und erkennt instabilen Release-State.")
PY

docker inspect "$stopped_container" >/dev/null
docker image inspect "$unused_image_id" >/dev/null
docker image inspect "$dangling_image_id" >/dev/null
docker volume inspect "$volume_name" >/dev/null

python3 scripts/docker-retention-cleanup.py \
  "${common_args[@]}" \
  --apply \
  --report "$blocked_report" >/dev/null

python3 - "$blocked_report" <<'PY'
import json
import pathlib
import sys

report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["status"] == "skipped-safety-gate", report
assert report["cleanup_allowed"] is False, report
assert report["build_cache"]["executed"] is False, report
print("Apply wurde bei instabilem Deployment-State sicher übersprungen.")
PY

docker inspect "$stopped_container" >/dev/null
docker image inspect "$unused_image_id" >/dev/null
docker volume inspect "$volume_name" >/dev/null

python3 - "$state_root/service-a/state.json" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
state = json.loads(path.read_text(encoding="utf-8"))
state["last_attempt"] = {"status": "success"}
path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
PY

python3 scripts/docker-retention-cleanup.py \
  "${common_args[@]}" \
  --apply \
  --report "$apply_report" >/dev/null

python3 - "$apply_report" "$good_image" "$previous_image" <<'PY'
import json
import pathlib
import sys

report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
good = sys.argv[2]
previous = sys.argv[3]

assert report["status"] == "success", report
assert report["cleanup_allowed"] is True, report
assert good in report["protected_image_references"], report
assert previous in report["protected_image_references"], report
assert report["containers"]["count"] >= 1, report
assert report["images"]["count"] >= 1, report
assert report["build_cache"]["executed"] is True, report
assert report["build_cache"]["returncode"] == 0, report
assert report["volumes"]["action"] == "none", report
assert not report["errors"], report
print("Cleanup wurde mit Rollback-Schutz erfolgreich ausgeführt.")
PY

if docker inspect "$stopped_container" >/dev/null 2>&1; then
  echo "Alter managed Stopped-Container wurde nicht entfernt." >&2
  exit 1
fi

if docker image inspect "$unused_image_id" >/dev/null 2>&1; then
  echo "Ungenutztes First-Party-Testimage wurde nicht entfernt." >&2
  exit 1
fi

if docker image inspect "$dangling_image_id" >/dev/null 2>&1; then
  echo "Dangling Image wurde nicht entfernt." >&2
  exit 1
fi

docker inspect "$running_container" >/dev/null
[[ "$(docker inspect --format '{{.State.Running}}' "$running_container")" == "true" ]]
docker image inspect "$running_image" >/dev/null

docker inspect "$protected_container" >/dev/null

docker image inspect "$good_image" >/dev/null
docker image inspect "$previous_image" >/dev/null

docker volume inspect "$volume_name" >/dev/null

echo "Docker-Retention-Cleanup schützt Rollbacks, laufende Container und Volumes und entfernt nur sichere Altartefakte."
