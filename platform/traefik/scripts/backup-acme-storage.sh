#!/usr/bin/env bash
set -Eeuo pipefail

source_file="${1:-/srv/merchfactory/persistent/traefik/acme/acme.json}"
backup_dir="${2:-/srv/merchfactory/shared/backups/traefik-acme}"

if [[ ! -f "$source_file" ]]; then
  echo "ACME-Speicher fehlt: $source_file" >&2
  exit 1
fi

source_mode="$(stat -c '%a' "$source_file")"
if [[ "$source_mode" != "600" ]]; then
  echo "ACME-Speicher hat unsicheren Modus $source_mode; Backup abgebrochen." >&2
  exit 1
fi

install -d -m 0700 "$backup_dir"

timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
target="${backup_dir}/acme-${timestamp}.json"
tmp="${target}.tmp"

install -m 0600 "$source_file" "$tmp"
mv "$tmp" "$target"

sha256sum "$target" > "${target}.sha256"
chmod 0600 "${target}.sha256"

echo "$target"
