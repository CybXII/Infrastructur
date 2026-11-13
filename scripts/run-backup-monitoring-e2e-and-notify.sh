#!/usr/bin/env bash
set -Eeuo pipefail
base=/opt/merchfactory/monitoring-e2e
log="$(mktemp /tmp/merchfactory-backup-e2e.XXXXXXXX.log)"
trap 'rm -f "$log"' EXIT
status=SUCCESS
if [[ -f "$base/deployed-commit" ]]; then
  echo "E2E deployed commit: $(cat "$base/deployed-commit")"
fi
{
  # Fail before creating synthetic metrics if the required host dependencies
  # or Discord endpoint are unavailable. The wrapper still sends a failure report.
  /usr/bin/python3 "$base/notify-backup-monitoring-e2e.py" --check
  test -d /var/lib/merchfactory/node_exporter/textfile
  command -v docker
  container_id="$(/usr/bin/docker ps --filter label=com.docker.compose.project=merchfactory-development-prometheus --filter label=com.docker.compose.service=prometheus --format '{{.ID}}')"
  test -n "$container_id"
  /usr/bin/docker exec "$container_id" wget -q -O /dev/null http://127.0.0.1:9090/-/ready
  /usr/bin/python3 "$base/run-backup-monitoring-e2e.py" --environment development --directory /var/lib/merchfactory/node_exporter/textfile --prometheus-url docker-prometheus
} >"$log" 2>&1 || status=FAILED
cat "$log"
if ! /usr/bin/python3 "$base/notify-backup-monitoring-e2e.py" "$status" "$log"; then
  echo "ERROR: Discord completion notification failed; see journal" >&2
  exit 1
fi
[[ "$status" == SUCCESS ]]
