#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/test-bootstrap-fresh-host.sh <initial-inventory> <managed-inventory> [limit]

Führt Preflight, initialen Bootstrap, Reconnect, Idempotenzprüfung und
Sicherheits-/Funktionschecks gegen einen freigegebenen Fresh Host aus.
EOF
}

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage >&2
  exit 2
fi

initial_inventory="$1"
managed_inventory="$2"
limit="${3:-}"
bootstrap_playbook="ansible/playbooks/bootstrap.yml"
preflight_playbook="tests/integration/test-bootstrap-fresh-host-preflight.yaml"
verification_playbook="tests/integration/test-bootstrap-fresh-host-verify.yaml"
artifact_dir="${FRESH_HOST_ARTIFACT_DIR:-artifacts/bootstrap-fresh-host}"
correlation_id="${BOOTSTRAP_CORRELATION_ID:-fresh-host-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
environment="${BOOTSTRAP_ENVIRONMENT:-development}"
commit_sha="${BOOTSTRAP_COMMIT_SHA:-unknown}"
started_at="$(date +%s)"
phase="initialization"
result="failed"
first_changed="not-run"
second_changed="not-run"
exit_code=10

first_result="${artifact_dir}/first-run.json"
second_result="${artifact_dir}/second-run.json"
preflight_result="${artifact_dir}/preflight.log"
verification_result="${artifact_dir}/verification.log"
summary_file="${artifact_dir}/summary.txt"

log_event() {
  local level="$1"
  local event="$2"
  local message="$3"

  python3 - "$level" "$event" "$message" "$correlation_id" "$environment" <<'PY'
import json
import sys
from datetime import datetime, timezone

level, event, message, correlation_id, environment = sys.argv[1:]
print(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    "level": level,
    "component": "bootstrap-fresh-host",
    "environment": environment,
    "event": event,
    "message": message,
    "correlation_id": correlation_id,
}, ensure_ascii=False))
PY
}

write_summary() {
  local trap_exit_code=$?
  local finished_at elapsed_seconds

  if [[ "$result" == "passed" ]]; then
    exit_code=0
  elif [[ "$trap_exit_code" -ne 0 ]]; then
    exit_code="$trap_exit_code"
  fi

  finished_at="$(date +%s)"
  elapsed_seconds="$((finished_at - started_at))"
  {
    echo "Bootstrap fresh-host result"
    echo "result=${result}"
    echo "last_phase=${phase}"
    echo "exit_code=${exit_code}"
    echo "elapsed_seconds=${elapsed_seconds}"
    echo "environment=${environment}"
    echo "commit_sha=${commit_sha}"
    echo "correlation_id=${correlation_id}"
    echo "limit=${limit:-<none>}"
    echo "first_run_changed=${first_changed}"
    echo "second_run_changed=${second_changed}"
  } >"$summary_file"

  if [[ "$result" == "passed" ]]; then
    log_event info bootstrap_fresh_host_completed \
      "Fresh-Host-Test vollständig erfolgreich"
  else
    log_event error bootstrap_fresh_host_failed \
      "Fresh-Host-Test in Phase ${phase} fehlgeschlagen"
  fi
  return "$exit_code"
}

mkdir -p "$artifact_dir"
trap write_summary EXIT

for required_file in \
  "$initial_inventory" \
  "$managed_inventory" \
  "$bootstrap_playbook" \
  "$preflight_playbook" \
  "$verification_playbook"; do
  if [[ ! -f "$required_file" ]]; then
    echo "configuration_invalid: Datei fehlt: $required_file" >&2
    exit 2
  fi
done

playbook_args() {
  local inventory="$1"
  local playbook="$2"
  local -n output_array="$3"

  output_array=(-i "$inventory" "$playbook")
  if [[ -n "$limit" ]]; then
    output_array+=(--limit "$limit")
  fi
}

run_bootstrap_json() {
  local inventory="$1"
  local output_file="$2"
  local -a args=()

  playbook_args "$inventory" "$bootstrap_playbook" args
  ANSIBLE_STDOUT_CALLBACK=ansible.posix.json \
  ANSIBLE_LOAD_CALLBACK_PLUGINS=1 \
    ansible-playbook "${args[@]}" >"$output_file"
}

changed_count() {
  local result_file="$1"

  python3 - "$result_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"validation_error: Ansible-Ergebnis ist ungültig: {exc}")

stats = payload.get("stats")
if not isinstance(stats, dict) or not stats:
    raise SystemExit("validation_error: Ansible-Ergebnis enthält keine Host-Statistik")

changed = 0
failed_hosts = []
for host, values in stats.items():
    changed += int(values.get("changed", 0))
    if int(values.get("failures", 0)) or int(values.get("unreachable", 0)):
        failed_hosts.append(host)

if failed_hosts:
    raise SystemExit(
        "dependency_error: Fehlerhafte Hosts: " + ", ".join(failed_hosts)
    )
print(changed)
PY
}

phase="preflight"
log_event info bootstrap_preflight_started \
  "Fresh-Host-Voraussetzungen werden geprüft"
preflight_args=()
playbook_args "$initial_inventory" "$preflight_playbook" preflight_args
ansible-playbook "${preflight_args[@]}" | tee "$preflight_result"

phase="initial-bootstrap"
log_event info bootstrap_initial_run_started \
  "Erster Bootstrap mit initialem Provider-Zugang gestartet"
run_bootstrap_json "$initial_inventory" "$first_result"
first_changed="$(changed_count "$first_result")"

phase="managed-user-reconnect"
log_event info bootstrap_managed_reconnect_started \
  "Reconnect mit verwaltetem Benutzer gestartet"
reconnect_args=(-i "$managed_inventory" bootstrap_targets)
if [[ -n "$limit" ]]; then
  reconnect_args+=(--limit "$limit")
fi
reconnect_args+=(
  -m ansible.builtin.wait_for_connection
  -a "timeout=60 connect_timeout=5 sleep=2"
)
ansible "${reconnect_args[@]}"

phase="idempotency-bootstrap"
log_event info bootstrap_idempotency_run_started \
  "Zweiter Bootstrap mit verwaltetem Benutzer gestartet"
run_bootstrap_json "$managed_inventory" "$second_result"
second_changed="$(changed_count "$second_result")"
if (( second_changed != 0 )); then
  echo "validation_error: Zweiter Lauf meldet ${second_changed} Änderung(en)" >&2
  exit 7
fi

phase="security-and-function-verification"
log_event info bootstrap_verification_started \
  "Sicherheits- und Funktionschecks gestartet"
verification_args=()
playbook_args "$managed_inventory" "$verification_playbook" verification_args
ansible-playbook "${verification_args[@]}" | tee "$verification_result"

phase="completed"
result="passed"
