#!/usr/bin/env bash
set -euo pipefail

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_paths=(
  "configuration/service.yaml.example"
  "configuration/secrets.yaml.example"
  "deployment/compose.yaml.example"
  "monitoring/healthcheck.yaml.example"
  "backup/policy.yaml.example"
  "tests/test-persistence.sh"
  "README.md"
)

for path in "${required_paths[@]}"; do
  if [[ ! -f "${base_dir}/${path}" ]]; then
    echo "Fehlende Referenzdatei: ${path}" >&2
    exit 1
  fi
done

files_to_scan=(
  "${base_dir}/configuration/service.yaml.example"
  "${base_dir}/configuration/secrets.yaml.example"
  "${base_dir}/deployment/compose.yaml.example"
  "${base_dir}/monitoring/healthcheck.yaml.example"
  "${base_dir}/backup/policy.yaml.example"
)

if grep -nE '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|password:[[:space:]]*[^C]|token:[[:space:]]*[^C])' "${files_to_scan[@]}"; then
  echo "Potentiell sensibles Beispielmaterial gefunden." >&2
  exit 1
fi

echo "Service-Referenzstruktur ist vollständig."
