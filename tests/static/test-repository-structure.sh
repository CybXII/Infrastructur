#!/usr/bin/env bash
set -euo pipefail

required_directories=(
  ".github"
  "backup"
  "bootstrap"
  "configuration"
  "deployment"
  "docs"
  "examples"
  "monitoring"
  "restore"
  "scripts"
  "templates"
  "tests"
  "configuration/common"
  "configuration/services"
  "configuration/environments/development"
  "configuration/environments/staging"
  "configuration/environments/production"
  "configuration/hosts"
  "configuration/schemas"
  "tests/static"
  "tests/unit"
  "tests/integration"
  "tests/smoke"
  "tests/security"
  "tests/backup"
  "tests/restore"
  "tests/fixtures"
  "templates/configurations"
  "templates/services"
  "templates/compose"
  "templates/systemd"
  "templates/runbooks"
)

required_files=(
  ".github/README.md"
  "backup/README.md"
  "bootstrap/README.md"
  "configuration/README.md"
  "deployment/README.md"
  "docs/README.md"
  "examples/README.md"
  "monitoring/README.md"
  "restore/README.md"
  "scripts/README.md"
  "templates/README.md"
  "tests/README.md"
  "docs/09-repository-structure.md"
  "docs/10-development-guidelines.md"
)

missing=0

for directory in "${required_directories[@]}"; do
  if [[ ! -d "$directory" ]]; then
    printf 'FEHLT (Verzeichnis): %s\n' "$directory" >&2
    missing=1
  fi
done

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    printf 'FEHLT (Datei): %s\n' "$file" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  printf 'Repositorystruktur ist unvollständig.\n' >&2
  exit 1
fi

printf 'Repositorystruktur ist vollständig und dokumentiert.\n'