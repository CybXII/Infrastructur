#!/usr/bin/env bash
set -Eeuo pipefail

workflow=".github/workflows/reusable-static-validation.yml"

grep -q '^  changes:$' "$workflow"
grep -q 'fetch-depth: 0' "$workflow"
grep -q 'github.event.pull_request.base.sha' "$workflow"
grep -q 'github.event.before' "$workflow"

for scope in monitoring traefik service_template resources logging rollback reference_service cleanup; do
  grep -q "steps.scope.outputs.$scope" "$workflow"
done

for job in prometheus-integration traefik-integration service-template-integration resource-limits-integration log-rotation-integration update-rollback-integration reference-service-integration docker-cleanup-integration; do
  grep -q "^  $job:" "$workflow"
done

grep -q "needs.changes.outputs.monitoring == 'true'" "$workflow"
grep -q "needs.changes.outputs.traefik == 'true'" "$workflow"
grep -q "needs.changes.outputs.rollback == 'true'" "$workflow"

echo "Change-aware Integrationstest-Steuerung ist verdrahtet."
