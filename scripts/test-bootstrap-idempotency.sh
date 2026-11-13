#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/test-bootstrap-idempotency.sh <inventory> [limit]

Beispiel:
  scripts/test-bootstrap-idempotency.sh ansible/inventories/development/hosts.yml bootstrap-test-01

Der Test führt das Bootstrap-Playbook zweimal gegen dasselbe Ziel aus.
Der zweite Lauf muss erfolgreich sein und darf keine Änderungen melden.
EOF
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 2
fi

inventory="$1"
limit="${2:-}"
playbook="ansible/playbooks/bootstrap.yml"
artifact_dir="${IDEMPOTENCY_ARTIFACT_DIR:-artifacts/bootstrap-idempotency}"
first_result="${artifact_dir}/first-run.json"
second_result="${artifact_dir}/second-run.json"
summary_file="${artifact_dir}/summary.txt"

if [[ ! -f "$inventory" ]]; then
  echo "Inventar nicht gefunden: $inventory" >&2
  exit 2
fi

if [[ ! -f "$playbook" ]]; then
  echo "Bootstrap-Playbook nicht gefunden: $playbook" >&2
  exit 2
fi

mkdir -p "$artifact_dir"

ansible_args=(
  -i "$inventory"
  "$playbook"
)

if [[ -n "$limit" ]]; then
  ansible_args+=(--limit "$limit")
fi

print_failures() {
  local result_file="$1"

  python3 - "$result_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"Ansible-Ergebnis konnte nicht ausgewertet werden: {exc}", file=sys.stderr)
    raise SystemExit(0)

for play in payload.get("plays", []):
    for task in play.get("tasks", []):
        task_name = task.get("task", {}).get("name", "<unbekannte Task>")
        for host, result in task.get("hosts", {}).items():
            if result.get("failed") or result.get("unreachable"):
                message = result.get("msg", "kein Fehlertext vorhanden")
                print(f"FAILED: {task_name} [{host}]: {message}", file=sys.stderr)
PY
}

run_bootstrap() {
  local output_file="$1"
  local rc

  set +e
  ANSIBLE_STDOUT_CALLBACK=ansible.posix.json \
  ANSIBLE_LOAD_CALLBACK_PLUGINS=1 \
    ansible-playbook "${ansible_args[@]}" >"$output_file"
  rc=$?
  set -e

  if (( rc != 0 )); then
    print_failures "$output_file"
    return "$rc"
  fi
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
    raise SystemExit(f"Ansible-Ergebnis konnte nicht ausgewertet werden: {exc}")

stats = payload.get("stats")
if not isinstance(stats, dict) or not stats:
    raise SystemExit("Ansible-Ergebnis enthält keine Host-Statistik.")

changed = 0
failures = []
for host, values in stats.items():
    changed += int(values.get("changed", 0))
    if int(values.get("failures", 0)) or int(values.get("unreachable", 0)):
        failures.append(host)

if failures:
    raise SystemExit("Fehlerhafte Hosts im Ergebnis: " + ", ".join(failures))

print(changed)
PY
}

echo "Bootstrap-Idempotenztest: erster Lauf"
if ! run_bootstrap "$first_result"; then
  {
    echo "Bootstrap idempotency result"
    echo "inventory=${inventory}"
    echo "limit=${limit:-<none>}"
    echo "result=failed"
    echo "failed_run=first"
  } | tee "$summary_file"
  exit 2
fi
first_changed="$(changed_count "$first_result")"

echo "Bootstrap-Idempotenztest: zweiter Lauf"
if ! run_bootstrap "$second_result"; then
  {
    echo "Bootstrap idempotency result"
    echo "inventory=${inventory}"
    echo "limit=${limit:-<none>}"
    echo "result=failed"
    echo "failed_run=second"
    echo "first_run_changed=${first_changed}"
  } | tee "$summary_file"
  exit 2
fi
second_changed="$(changed_count "$second_result")"

{
  echo "Bootstrap idempotency result"
  echo "inventory=${inventory}"
  echo "limit=${limit:-<none>}"
  echo "result=passed"
  echo "first_run_changed=${first_changed}"
  echo "second_run_changed=${second_changed}"
} | tee "$summary_file"

if (( second_changed != 0 )); then
  echo "Idempotenz verletzt: Der zweite Bootstrap-Lauf meldet ${second_changed} Änderung(en)." >&2
  exit 1
fi

echo "Idempotenz bestätigt: Der zweite Bootstrap-Lauf meldet keine Änderungen."
