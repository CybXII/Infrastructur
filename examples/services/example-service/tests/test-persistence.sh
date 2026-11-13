#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$repo_root"

compose_file="examples/services/example-service/deployment/compose.yaml.example"
policy_file="examples/services/example-service/backup/policy.yaml.example"

secret_fixture_root="$(mktemp -d)"
printf '%s' 'MF_TEST_API_TOKEN' > "$secret_fixture_root/api-token"
printf '%s' 'MF_TEST_DATABASE_PASSWORD' > "$secret_fixture_root/database-password"
chmod 0600 "$secret_fixture_root/api-token" "$secret_fixture_root/database-password"

export EXAMPLE_SERVICE_API_TOKEN_FILE="$secret_fixture_root/api-token"
export EXAMPLE_DATABASE_PASSWORD_FILE="$secret_fixture_root/database-password"

compose_json="$(docker compose -f "$compose_file" config --format json)"

COMPOSE_JSON="$compose_json" python3 - "$policy_file" <<'PY'
import json
import os
import pathlib
import sys

policy_path = pathlib.Path(sys.argv[1])
document = json.loads(os.environ["COMPOSE_JSON"])

allowed_write_roots = (
    "/srv/merchfactory/persistent/",
    "/srv/merchfactory/shared/",
    "/var/lib/merchfactory/",
    "/var/log/merchfactory/",
    "/var/tmp/merchfactory/",
)

errors = []
services = document.get("services", {})
for service_name, service in services.items():
    for mount in service.get("volumes") or []:
        if isinstance(mount, str):
            errors.append(f"{service_name}: String-/anonymer Volume-Eintrag ist nicht zulässig: {mount}")
            continue

        mount_type = mount.get("type")
        source = mount.get("source")
        target = mount.get("target")
        read_only = bool(mount.get("read_only"))

        if mount_type == "volume":
            if not source:
                errors.append(f"{service_name}: anonymes Volume für {target} ist nicht zulässig.")
        elif mount_type == "bind":
            if not source:
                errors.append(f"{service_name}: Bind Mount ohne Quelle für {target}.")
                continue
            if source.startswith("/var/lib/docker/volumes"):
                errors.append(f"{service_name}: direkter Docker-Volume-Pfad ist verboten: {source}")
            if not read_only and not source.startswith(allowed_write_roots):
                errors.append(
                    f"{service_name}: beschreibbarer Bind Mount außerhalb freigegebener Pfade: {source}"
                )

volumes = document.get("volumes", {})
for volume_name, volume in volumes.items():
    labels = (volume or {}).get("labels") or {}
    persistence_class = labels.get("com.merchfactory.persistence.class")
    backup_required = str(labels.get("com.merchfactory.backup.required", "")).lower()
    backup_method = labels.get("com.merchfactory.backup.method")

    if not persistence_class:
        errors.append(f"{volume_name}: Persistenzklasse fehlt.")
    if backup_required == "true" and not backup_method:
        errors.append(f"{volume_name}: Backup ist Pflicht, aber backup.method fehlt.")

if not policy_path.is_file() or policy_path.stat().st_size == 0:
    errors.append("Service-Backup-Policy fehlt oder ist leer.")

if errors:
    for error in errors:
        print(f"FEHLER: {error}", file=sys.stderr)
    raise SystemExit(1)

print("Persistenzmodell der Service-Referenz erfüllt.")
PY

test_root="$(mktemp -d)"
trap 'rm -rf "$test_root" "$secret_fixture_root"' EXIT

export MERCHFACTORY_ALLOWED_PERSISTENCE_ROOTS="$test_root"
target="$test_root/example-service/data"

bash platform/storage/scripts/prepare-persistent-directory.sh \
  "$target" \
  "$(id -u)" \
  "$(id -g)" \
  0750 >/dev/null

# Zweiter identischer Lauf muss ohne Zustandsänderung erfolgreich bleiben.
bash platform/storage/scripts/prepare-persistent-directory.sh \
  "$target" \
  "$(id -u)" \
  "$(id -g)" \
  0750 >/dev/null

[[ -d "$target" ]]
[[ "$(stat -c '%a' "$target")" == "750" ]]
[[ "$(stat -c '%u' "$target")" == "$(id -u)" ]]
[[ "$(stat -c '%g' "$target")" == "$(id -g)" ]]

if MERCHFACTORY_ALLOWED_PERSISTENCE_ROOTS="$test_root" \
  bash platform/storage/scripts/prepare-persistent-directory.sh \
    /tmp/merchfactory-forbidden \
    "$(id -u)" \
    "$(id -g)" \
    0750 >/dev/null 2>&1; then
  echo "Pfad außerhalb der freigegebenen Persistenzwurzel hätte abgelehnt werden müssen." >&2
  exit 1
fi

echo "Persistenzpfade und Service-Referenz erfolgreich geprüft."
