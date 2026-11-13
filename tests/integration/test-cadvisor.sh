#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

version="0.60.5"
binary_name="cadvisor-v$version-linux-amd64"
url="https://github.com/google/cadvisor/releases/download/v$version/$binary_name"
sha256="6f258bed28113218c88729634c47ead8d928b81b1504b75fd911b98d29003a87"

# Match the Ansible default; filesystem restores the upstream default collectors.
metrics_profile="${CADVISOR_METRICS_PROFILE:-lean}"
metrics_args=()
case "$metrics_profile" in
  lean) metrics_args=(--disable_metrics=advtcp,cpu_topology,cpuset,disk,diskIO,hugetlb,memory_numa,process,referenced_memory,resctrl,sched,tcp,udp) ;;
  filesystem) ;;
  *) echo "Unknown CADVISOR_METRICS_PROFILE: $metrics_profile" >&2; exit 1 ;;
esac

test_root="$(mktemp -d)"
export MERCHFACTORY_MONITORING_NETWORK="cadvisor-ci-${GITHUB_RUN_ID:-local}-$$"
export MERCHFACTORY_MONITORING_SUBNET="172.30.252.0/24"
export MERCHFACTORY_MONITORING_GATEWAY="172.30.252.1"
export MERCHFACTORY_MONITORING_BRIDGE="mfcad$$"

cadvisor_pid=""
fixture="mf-cadvisor-fixture-$$"

cleanup() {
  docker rm -f "$fixture" >/dev/null 2>&1 || true
  if [[ -n "$cadvisor_pid" ]]; then
    sudo -n kill "$cadvisor_pid" >/dev/null 2>&1 || kill "$cadvisor_pid" >/dev/null 2>&1 || true
    wait "$cadvisor_pid" >/dev/null 2>&1 || true
  fi
  docker network rm "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null 2>&1 || true
  rm -rf "$test_root"
}
trap cleanup EXIT

curl --fail --location --silent --show-error "$url" --output "$test_root/cadvisor"
printf '%s  %s\n' "$sha256" "$test_root/cadvisor" | sha256sum --check -
chmod +x "$test_root/cadvisor"

version_output="$("$test_root/cadvisor" --version 2>&1)"
grep -Eq "cAdvisor version v?$version" <<<"$version_output"

bash platform/network/scripts/prepare-monitoring-network.sh "$MERCHFACTORY_MONITORING_NETWORK" >/dev/null

prometheus_image="$(
  docker compose -f deployment/monitoring/prometheus/compose.yaml config --format json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["prometheus"]["image"])'
)"
docker pull "$prometheus_image" >/dev/null

docker run -d \
  --name "$fixture" \
  --label com.merchfactory.managed=true \
  --label com.merchfactory.cleanup.protect=false \
  --label com.merchfactory.not-exported=secret \
  --entrypoint /bin/sh \
  "$prometheus_image" \
  -c 'while :; do sleep 30; done' >/dev/null

fixture_id="$(docker inspect --format '{{.Id}}' "$fixture")"

sudo -n "$test_root/cadvisor" \
  --listen_ip="$MERCHFACTORY_MONITORING_GATEWAY" \
  --port=8080 \
  --docker=unix:///var/run/docker.sock \
  --docker_only=true \
  --store_container_labels=false \
  --whitelisted_container_labels=com.merchfactory.managed,com.merchfactory.cleanup.protect,com.docker.compose.project,com.docker.compose.service \
  --housekeeping_interval=5s \
  --max_housekeeping_interval=10s \
  --global_housekeeping_interval=5s \
  --storage_duration=2m \
  "${metrics_args[@]}" \
  --profiling=false \
  --v=1 \
  >"$test_root/cadvisor.log" 2>&1 &
cadvisor_pid="$!"

for attempt in {1..30}; do
  if curl --fail --silent --show-error --noproxy '*' \
    "http://$MERCHFACTORY_MONITORING_GATEWAY:8080/metrics" \
    > "$test_root/metrics.txt"; then
    break
  fi
  if ! kill -0 "$cadvisor_pid" >/dev/null 2>&1; then
    cat "$test_root/cadvisor.log" >&2
    echo "cAdvisor wurde unerwartet beendet." >&2
    exit 1
  fi
  if [[ "$attempt" -eq 30 ]]; then
    cat "$test_root/cadvisor.log" >&2
    echo "cAdvisor wurde nicht erreichbar." >&2
    exit 1
  fi
  sleep 1
done

if curl --fail --silent --max-time 1 --noproxy '*' http://127.0.0.1:8080/metrics >/dev/null 2>&1; then
  echo "cAdvisor darf nicht auf 127.0.0.1:8080 lauschen." >&2
  exit 1
fi

listener="$(ss -ltnH 'sport = :8080')"
grep -q "$MERCHFACTORY_MONITORING_GATEWAY:8080" <<<"$listener"
if grep -Eq '(^|[[:space:]])0\.0\.0\.0:8080|\[::\]:8080' <<<"$listener"; then
  echo "cAdvisor lauscht unerwartet global: $listener" >&2
  exit 1
fi

metric_for_fixture() {
  local metric="$1"
  python3 - "$test_root/metrics.txt" "$metric" "$fixture_id" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
metric = sys.argv[2]
fixture_id = sys.argv[3]
for line in path.read_text(encoding="utf-8").splitlines():
    if line.startswith(metric + "{") and fixture_id in line:
        print(line.rsplit(" ", 1)[-1])
        raise SystemExit(0)
raise SystemExit(1)
PY
}

for attempt in {1..30}; do
  curl --fail --silent --show-error --noproxy '*' \
    "http://$MERCHFACTORY_MONITORING_GATEWAY:8080/metrics" \
    > "$test_root/metrics.txt"
  if metric_for_fixture container_cpu_usage_seconds_total >/dev/null 2>&1 \
    && metric_for_fixture container_memory_working_set_bytes >/dev/null 2>&1 \
    && metric_for_fixture container_network_receive_bytes_total >/dev/null 2>&1 \
    && metric_for_fixture container_network_transmit_bytes_total >/dev/null 2>&1 \
    && metric_for_fixture container_start_time_seconds >/dev/null 2>&1 \
    && { [[ "$metrics_profile" == "lean" ]] || metric_for_fixture container_fs_usage_bytes >/dev/null 2>&1; }; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "Container-Kernmetriken für $fixture fehlen." >&2
    grep "$fixture_id" "$test_root/metrics.txt" | head -50 >&2 || true
    exit 1
  fi
  sleep 1
done

if [[ "$metrics_profile" == "lean" ]]; then
  if grep -Eq '^container_fs_' "$test_root/metrics.txt"; then
    echo "Filesystem-/Disk-I/O-Metriken sind im lean-Profil unerwartet aktiv." >&2
    exit 1
  fi
else
  metric_for_fixture container_fs_usage_bytes >/dev/null
fi

grep "$fixture_id" "$test_root/metrics.txt" > "$test_root/fixture-metrics.txt"
grep -q 'container_label_com_merchfactory_managed="true"' "$test_root/fixture-metrics.txt"
if grep -q 'container_label_com_merchfactory_not_exported=' "$test_root/fixture-metrics.txt"; then
  echo "Nicht freigegebenes Container-Label wurde exportiert." >&2
  exit 1
fi

start_before="$(metric_for_fixture container_start_time_seconds)"
docker restart "$fixture" >/dev/null

restart_visible=false
for attempt in {1..30}; do
  sleep 1
  curl --fail --silent --show-error --noproxy '*' \
    "http://$MERCHFACTORY_MONITORING_GATEWAY:8080/metrics" \
    > "$test_root/metrics.txt"
  start_after="$(metric_for_fixture container_start_time_seconds 2>/dev/null || true)"
  if [[ -n "$start_after" && "$start_after" != "$start_before" ]]; then
    restart_visible=true
    break
  fi
done
[[ "$restart_visible" == "true" ]] || {
  echo "Container-Neustart wurde über container_start_time_seconds nicht sichtbar." >&2
  exit 1
}

docker run --rm \
  --network "$MERCHFACTORY_MONITORING_NETWORK" \
  --entrypoint /bin/sh \
  "$prometheus_image" \
  -c "wget -q -O - http://$MERCHFACTORY_MONITORING_GATEWAY:8080/metrics" \
  > "$test_root/container-scrape.txt"

grep -q '^container_cpu_usage_seconds_total' "$test_root/container-scrape.txt"
grep -q '^container_memory_working_set_bytes' "$test_root/container-scrape.txt"

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  check rules /etc/prometheus/rules/cadvisor.yml

docker run --rm \
  --entrypoint /bin/promtool \
  -v "$repo_root/monitoring/prometheus/rules:/etc/prometheus/rules:ro" \
  "$prometheus_image" \
  test rules /etc/prometheus/rules/tests/cadvisor.test.yml

echo "cAdvisor erfolgreich verifiziert: Release, Docker-Erkennung, Isolation, Kernmetriken, Labels und Neustarts."
