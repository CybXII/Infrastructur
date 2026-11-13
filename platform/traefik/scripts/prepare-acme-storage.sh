#!/usr/bin/env bash
set -Eeuo pipefail

acme_dir="${1:-/srv/merchfactory/persistent/traefik/acme}"
acme_file="${acme_dir}/acme.json"

install -d -m 0700 "$acme_dir"

if [[ ! -e "$acme_file" ]]; then
  install -m 0600 /dev/null "$acme_file"
else
  chmod 0600 "$acme_file"
fi

mode="$(stat -c '%a' "$acme_file")"
if [[ "$mode" != "600" ]]; then
  echo "Unsicherer Modus für $acme_file: $mode (erwartet 600)" >&2
  exit 1
fi

echo "$acme_file"
