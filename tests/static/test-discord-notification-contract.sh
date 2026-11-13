#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
config="$repo_root/monitoring/alertmanager/alertmanager.yml"
compose="$repo_root/deployment/monitoring/alertmanager/compose.yaml"
workflow="$repo_root/.github/workflows/deploy-development-monitoring.yml"
doc="$repo_root/docs/69-discord-alerting.md"
for file in "$config" "$compose" "$workflow" "$doc"; do test -f "$file"; done
for receiver in discord-default discord-critical discord-warning discord-info; do grep -q "name: $receiver" "$config"; done
grep -Fq 'severity=~"critical|high"' "$config"
grep -q 'severity="warning"' "$config"
grep -q 'severity="info"' "$config"
test "$(grep -c 'send_resolved: true' "$config")" -eq 4
test "$(grep -c 'webhook_url_file: /run/secrets/discord-webhook-url' "$config")" -eq 4
grep -q '\*\*Umgebung:\*\*' "$config"
grep -q '\*\*Server:\*\*' "$config"
grep -q '\*\*Dienst:\*\*' "$config"
grep -q 'FIRING' "$config"
grep -q 'RESOLVED' "$config"
grep -q 'target: /run/secrets/discord-webhook-url' "$compose"
grep -q 'DISCORD_WEBHOOK_URL:.*secrets.DISCORD_WEBHOOK_URL' "$workflow"
grep -q 'install-secret-file.sh.*alertmanager discord-webhook-url 65534 65534 0400' "$workflow"
if grep -R --exclude='test-discord-notification-contract.sh' -E 'discord(app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9._-]+' "$repo_root/monitoring" "$repo_root/deployment" "$repo_root/docs" "$repo_root/.github/workflows"; then
  echo "Ein Discord-Webhook darf nicht im Repository gespeichert werden." >&2
  exit 1
fi
echo "Discord-Notification-Vertrag ist vollständig und secret-basiert."
