#!/usr/bin/env bash
set -Eeuo pipefail

workflow=".github/workflows/deploy-development-monitoring.yml"

grep -Fq 'actions/runs?head_sha=$SOURCE_SHA&per_page=100' "$workflow"
if grep -Fq 'actions/runs?head_sha=$SOURCE_SHA&event=push' "$workflow"; then
  echo "Monitoring-Deploy darf das Image-Security-Gate nicht auf push-Runs beschränken." >&2
  exit 1
fi
grep -Fq 'select(.name == "Container Image Security")' "$workflow"
grep -Fq 'image_status" == "completed"' "$workflow"
grep -Fq 'image_conclusion" == "success"' "$workflow"

echo "Monitoring Image-Security-Gate akzeptiert erfolgreiche Runs für den exakten SOURCE_SHA unabhängig vom Event."
