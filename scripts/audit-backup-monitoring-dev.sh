#!/usr/bin/env bash
# Read-only development audit for issue #94. No public Prometheus endpoint required.
set -Eeuo pipefail
if [[ "${1:-}" != "--environment=development" ]]; then
  echo "Usage: $0 --environment=development" >&2
  exit 2
fi
container=merchfactory-development-prometheus
query() {
  local expr="$1"
  docker exec "$container" wget -qO- --post-data="query=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe=""))' "$expr")" \
    'http://127.0.0.1:9090/api/v1/query' 2>/dev/null ||
    docker exec "$container" wget -qO- "http://127.0.0.1:9090/api/v1/query?query=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe=""))' "$expr")"
}
echo '=== Node Exporter textfile collector errors (0 expected) ==='
query 'node_textfile_scrape_error' | python3 -m json.tool
echo '=== Real backup duration / size / status (synthetic excluded) ==='
for metric in merchfactory_backup_duration_seconds merchfactory_backup_size_bytes merchfactory_backup_last_success merchfactory_backup_restore_test_last_success; do
  echo "--- $metric"
  query "${metric}{service!=\"monitoring-e2e-test\"}" | python3 -m json.tool
done
echo '=== Alert rule state ==='
query 'ALERTS{alertname=~"BackupJobFailed|BackupTooOld|RestoreTestFailed|RestoreTestTooOld"}' | python3 -m json.tool
echo 'NOTE: Empty results are NOT evidence of successful backups. Verify actual backup/restore job wiring separately.'
