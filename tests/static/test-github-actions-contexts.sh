#!/usr/bin/env bash
set -Eeuo pipefail

readonly workflows_directory=".github/workflows"
readonly unsupported_runner_home='\$\{\{[[:space:]]*runner\.home'

if rg -n "$unsupported_runner_home" "$workflows_directory"; then
  printf 'Nicht unterstützter GitHub-Kontext runner.home gefunden.\n' >&2
  printf 'Für temporäre Dateien runner.temp oder RUNNER_TEMP verwenden.\n' >&2
  exit 1
fi

printf 'GitHub-Actions-Kontexte sind gültig.\n'
