#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

if [[ "$EUID" -eq 0 ]]; then
  echo "Dieser Test erwartet einen unprivilegierten CI-Benutzer." >&2
  exit 1
fi

export MERCHFACTORY_SECRET_ROOT="$test_root/secrets"
uid="$(id -u)"
gid="$(id -g)"

first_value='MF_TEST_SECRET_VALUE_1'
second_value='MF_TEST_SECRET_VALUE_2'
database_value='MF_TEST_DATABASE_PASSWORD'

target="$(
  printf '%s' "$first_value" \
    | bash platform/secrets/scripts/install-secret-file.sh \
        example-service api-token "$uid" "$gid"
)"

database_target="$(
  printf '%s' "$database_value" \
    | bash platform/secrets/scripts/install-secret-file.sh \
        example-service database-password "$uid" "$gid"
)"

[[ "$target" == "$MERCHFACTORY_SECRET_ROOT/example-service/api-token" ]]
[[ -f "$target" ]]
[[ "$(stat -c '%a' "$target")" == "400" ]]
[[ "$(stat -c '%u' "$target")" == "$uid" ]]
[[ "$(stat -c '%g' "$target")" == "$gid" ]]
[[ "$(cat "$target")" == "$first_value" ]]

printf '%s' "$second_value" \
  | bash platform/secrets/scripts/install-secret-file.sh \
      example-service api-token "$uid" "$gid" >/dev/null

[[ "$(cat "$target")" == "$second_value" ]]

if printf '' \
  | bash platform/secrets/scripts/install-secret-file.sh \
      example-service empty-secret "$uid" "$gid" >/dev/null 2>&1; then
  echo "Leeres Secret hätte abgelehnt werden müssen." >&2
  exit 1
fi

if printf '%s' "$first_value" \
  | bash platform/secrets/scripts/install-secret-file.sh \
      '../escape' bad "$uid" "$gid" >/dev/null 2>&1; then
  echo "Path-Traversal im Service-Namen hätte abgelehnt werden müssen." >&2
  exit 1
fi

if printf '%s' "$first_value" \
  | bash platform/secrets/scripts/install-secret-file.sh \
      example-service '../escape' "$uid" "$gid" >/dev/null 2>&1; then
  echo "Path-Traversal im Secret-Namen hätte abgelehnt werden müssen." >&2
  exit 1
fi

export EXAMPLE_SERVICE_API_TOKEN_FILE="$target"
export EXAMPLE_DATABASE_PASSWORD_FILE="$database_target"

compose_json="$(
  docker compose \
    -f examples/services/example-service/deployment/compose.yaml.example \
    config --format json
)"

COMPOSE_JSON="$compose_json" python3 - <<'PY'
import json
import os

document = json.loads(os.environ["COMPOSE_JSON"])
services = document["services"]

expected = {
    "example-service": {"example-service-api-token", "example-database-password"},
    "example-worker": {"example-database-password"},
    "example-database": {"example-database-password"},
}

for service_name, expected_sources in expected.items():
    actual_sources = set()
    for entry in services[service_name].get("secrets") or []:
        if isinstance(entry, str):
            actual_sources.add(entry)
        else:
            actual_sources.add(entry["source"])

    if actual_sources != expected_sources:
        raise SystemExit(
            f"{service_name}: Secret-Grants {sorted(actual_sources)} "
            f"statt {sorted(expected_sources)}"
        )

serialized = json.dumps(document)
for forbidden in ("MF_TEST_SECRET_VALUE_1", "MF_TEST_SECRET_VALUE_2", "MF_TEST_DATABASE_PASSWORD"):
    if forbidden in serialized:
        raise SystemExit("Secret-Wert ist in normalisierter Compose-Konfiguration sichtbar.")

print("Compose-Secret-Grants erfolgreich geprüft.")
PY

echo "Secret-Installation, Rotation und Compose-Injection erfolgreich geprüft."
