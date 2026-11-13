#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -lt 4 || "$#" -gt 5 ]]; then
  echo "Verwendung: $0 <service> <secret-name> <uid> <gid> [0400|0440]" >&2
  exit 2
fi

service="$1"
secret_name="$2"
owner_uid="$3"
owner_gid="$4"
mode="${5:-0400}"
default_secret_root="/srv/merchfactory/secrets"
secret_root="${MERCHFACTORY_SECRET_ROOT:-$default_secret_root}"

if [[ "$EUID" -eq 0 && "$secret_root" != "$default_secret_root" ]]; then
  echo "Als root darf die Secret-Wurzel nicht überschrieben werden." >&2
  exit 2
fi

name_pattern='^[a-z0-9][a-z0-9._-]*$'
if [[ ! "$service" =~ $name_pattern ]]; then
  echo "Ungültiger Service-Name." >&2
  exit 2
fi

if [[ ! "$secret_name" =~ $name_pattern ]]; then
  echo "Ungültiger Secret-Name." >&2
  exit 2
fi

if [[ ! "$owner_uid" =~ ^[0-9]+$ || ! "$owner_gid" =~ ^[0-9]+$ ]]; then
  echo "UID und GID müssen numerisch angegeben werden." >&2
  exit 2
fi

case "$mode" in
  0400|0440) ;;
  *)
    echo "Nicht erlaubter Secret-Modus: $mode (zulässig: 0400, 0440)" >&2
    exit 2
    ;;
esac

normalized_root="$(readlink -m -- "$secret_root")"
service_dir="${normalized_root}/${service}"
target="${service_dir}/${secret_name}"

install -d -m 0700 "$normalized_root"
install -d -m 0700 "$service_dir"

umask 077
tmp="$(mktemp "${service_dir}/.${secret_name}.tmp.XXXXXX")"

cleanup() {
  rm -f -- "$tmp"
}
trap cleanup EXIT

cat > "$tmp"

if [[ ! -s "$tmp" ]]; then
  echo "Secret-Inhalt ist leer; Installation abgebrochen." >&2
  exit 1
fi

current_uid="$(stat -c '%u' "$tmp")"
current_gid="$(stat -c '%g' "$tmp")"

if [[ "$current_uid" != "$owner_uid" || "$current_gid" != "$owner_gid" ]]; then
  chown "$owner_uid:$owner_gid" "$tmp"
fi

chmod "$mode" "$tmp"

actual_uid="$(stat -c '%u' "$tmp")"
actual_gid="$(stat -c '%g' "$tmp")"
actual_mode="$(stat -c '%a' "$tmp")"

if [[ "$actual_uid" != "$owner_uid" || "$actual_gid" != "$owner_gid" ]]; then
  echo "Secret-Ownership konnte nicht sicher gesetzt werden." >&2
  exit 1
fi

expected_mode="${mode#0}"
if [[ "$actual_mode" != "$expected_mode" ]]; then
  echo "Secret-Modus konnte nicht sicher gesetzt werden." >&2
  exit 1
fi

mv -f -- "$tmp" "$target"
trap - EXIT

echo "$target"
