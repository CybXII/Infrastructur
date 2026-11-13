#!/usr/bin/env bash
# Issue #98: opt-in, Development-only Alertmanager/Discord routing smoke.
# Default mode is read-only. --apply sends a short-lived synthetic alert.
set -Eeuo pipefail

usage() {
  echo "Usage: $0 --plan [high|warning|info]" >&2
  echo "       $0 --apply --confirm-development [high|warning|info]" >&2
}

mode="${1:---plan}"
case "$mode" in
  --plan)
    if (( $# > 2 )); then usage; exit 2; fi
    severity="${2:-high}"
    ;;
  --apply)
    if [[ "${2:-}" != "--confirm-development" ]] || (( $# > 3 )); then
      usage
      exit 2
    fi
    severity="${3:-high}"
    ;;
  *)
    usage
    exit 2
    ;;
esac

case "$severity" in
  high|warning|info) ;;
  *) echo "Only high, warning or info are supported" >&2; exit 2 ;;
esac

case "$severity" in
  high) expected=discord-critical ;;
  warning) expected=discord-warning ;;
  info) expected=discord-info ;;
esac

# Never target a user-provided URL or a public Alertmanager endpoint.
# Verify the exact Development compose scope and require one running target.
mapfile -t containers < <(
  docker ps -q \
    --filter 'label=com.docker.compose.project=merchfactory-development-alertmanager' \
    --filter 'label=com.docker.compose.service=alertmanager'
)
if (( ${#containers[@]} != 1 )); then
  echo "Expected exactly one Development Alertmanager; found ${#containers[@]}" >&2
  exit 1
fi
cid="${containers[0]}"

echo "Development Alertmanager: $cid"
docker exec "$cid" /bin/amtool \
  --alertmanager.url=http://127.0.0.1:9093 \
  config routes test --verify.receivers="$expected" \
  severity="$severity" environment=development service=monitoring-e2e-test

if [[ "$mode" == "--plan" ]]; then
  echo "Read-only plan OK: $severity -> $expected"
  echo "No alert was sent. Use --apply --confirm-development to send a real Discord smoke."
  exit 0
fi

run_id="issue98-$(date -u +%Y%m%dT%H%M%SZ)-$$"
expires="$(date -u -d '+3 minutes' +%Y-%m-%dT%H:%M:%SZ)"
echo "Sending short-lived, isolated Development test: $run_id"
echo "Expected receiver: $expected; endsAt: $expires UTC"

docker exec "$cid" /bin/amtool \
  --alertmanager.url=http://127.0.0.1:9093 \
  alert add \
  alertname=MerchfactoryAlertRoutingSmoke \
  severity="$severity" \
  environment=development \
  service=monitoring-e2e-test \
  host=monitoring-e2e-test \
  instance=monitoring-e2e-test \
  test_run="$run_id" \
  --end="$expires" \
  '--annotation=summary="Manual Development routing smoke (#98)"' \
  '--annotation=description="Synthetic test alert; no actual incident."'

echo "Alert submitted. Verify Discord FIRING and, after automatic expiry,"
echo "RESOLVED for the same test_run. Do not claim delivery from this exit code."
echo "Allow routing/grouping delays (group_wait 30s, group_interval 5m)."
