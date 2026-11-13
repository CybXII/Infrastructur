#!/usr/bin/env bash
set -euo pipefail
# Development host only. Install without enabling the timer.
if [[ "${1:-}" != "--environment=development" ]]; then
  echo "Refusing install: explicit --environment=development required" >&2
  exit 2
fi
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target=/opt/merchfactory/monitoring-e2e
install -d -m 0755 "$target"
if [[ -f "$repo_root/deployed-commit" ]]; then
  install -m 0644 "$repo_root/deployed-commit" "$target/deployed-commit"
fi
install -m 0755 "$repo_root/tests/integration/backup-monitoring-e2e.py" "$target/backup-monitoring-e2e.py"
install -m 0755 "$repo_root/tests/integration/run-backup-monitoring-e2e.py" "$target/run-backup-monitoring-e2e.py"
install -m 0755 "$repo_root/tests/integration/notify-backup-monitoring-e2e.py" "$target/notify-backup-monitoring-e2e.py"
install -m 0755 "$repo_root/scripts/run-backup-monitoring-e2e-and-notify.sh" "$target/run-backup-monitoring-e2e-and-notify.sh"
install -m 0644 "$repo_root/templates/systemd/merchfactory-backup-monitoring-e2e.service" /etc/systemd/system/
install -m 0644 "$repo_root/templates/systemd/merchfactory-backup-monitoring-e2e.timer" /etc/systemd/system/
systemctl daemon-reload
echo "Installed but NOT started. Check Prometheus local endpoint and directory first."
echo "Manual run: systemctl start merchfactory-backup-monitoring-e2e.service"
echo "Logs: journalctl -u merchfactory-backup-monitoring-e2e.service -f"
echo "Weekly timer (optional, only after validation): systemctl enable --now merchfactory-backup-monitoring-e2e.timer"
