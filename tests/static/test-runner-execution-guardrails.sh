#!/usr/bin/env bash
set -Eeuo pipefail

readonly workflows_directory=".github/workflows"
readonly protected_bootstrap_workflows=(
  "$workflows_directory/bootstrap-fresh-host.yml"
  "$workflows_directory/bootstrap-managed-host.yml"
  "$workflows_directory/bootstrap-idempotency.yml"
  "$workflows_directory/deploy-development-monitoring.yml"
  "$workflows_directory/deploy-development-backup-e2e.yml"
)

for workflow in "${protected_bootstrap_workflows[@]}"; do
  test -f "$workflow"
  if ! grep -Eq '^[[:space:]]+runs-on: ubuntu-24[.]04$' "$workflow"; then
    printf '%s muss GitHub-hosted ubuntu-24.04 verwenden.\n' "$workflow" >&2
    exit 1
  fi
  if grep -Eq '^[[:space:]]+runs-on: ephemeral-linux$' "$workflow"; then
    printf '%s darf nicht auf dem eigenen Runner laufen.\n' "$workflow" >&2
    exit 1
  fi
done

if ! sed -n '/^  prometheus-integration:/,/^  traefik-integration:/p' \
  "$workflows_directory/reusable-static-validation.yml" \
  | grep -Eq '^[[:space:]]+runs-on: ubuntu-24[.]04$'; then
  echo 'Prometheus Host-Integration muss GitHub-hosted bleiben.' >&2
  exit 1
fi

for workflow in \
  "$workflows_directory/bootstrap-validation.yml" \
  "$workflows_directory/image-security.yml" \
  "$workflows_directory/reusable-image-security.yml"; do
  test -f "$workflow"
  if grep -Eq '^[[:space:]]+runs-on: ubuntu' "$workflow"; then
    printf '%s muss auf Self-hosted laufen.\n' "$workflow" >&2
    exit 1
  fi
  grep -Eq '^[[:space:]]+runs-on: ephemeral-linux$' "$workflow"
done

if rg -n '^[[:space:]]*environment:' "$workflows_directory"; then
  printf 'GitHub Environments sind laut aktueller Plattformentscheidung nicht zulässig.\n' >&2
  exit 1
fi

printf 'Runner- und Bootstrap-Guardrails sind erfüllt.\n'
