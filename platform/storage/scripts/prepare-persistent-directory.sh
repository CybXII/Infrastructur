#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 4 ]]; then
  echo "Verwendung: $0 <pfad> <owner> <group> <mode>" >&2
  exit 2
fi

requested_path="$1"
owner="$2"
group="$3"
mode="$4"

if [[ "$requested_path" != /* ]]; then
  echo "Persistenzpfad muss absolut sein: $requested_path" >&2
  exit 2
fi

case "$mode" in
  0700|0750|0770) ;;
  *)
    echo "Nicht erlaubter Verzeichnismodus: $mode (zulässig: 0700, 0750, 0770)" >&2
    exit 2
    ;;
esac

normalized_path="$(readlink -m -- "$requested_path")"
allowed_roots_raw="${MERCHFACTORY_ALLOWED_PERSISTENCE_ROOTS:-/srv/merchfactory/persistent:/srv/merchfactory/shared:/var/lib/merchfactory}"

allowed=false
IFS=':' read -r -a allowed_roots <<< "$allowed_roots_raw"
for root in "${allowed_roots[@]}"; do
  normalized_root="$(readlink -m -- "$root")"
  if [[ "$normalized_path" == "$normalized_root" || "$normalized_path" == "$normalized_root/"* ]]; then
    allowed=true
    break
  fi
done

if [[ "$allowed" != true ]]; then
  echo "Persistenzpfad liegt außerhalb der freigegebenen Plattformpfade: $normalized_path" >&2
  exit 1
fi

if ! id "$owner" >/dev/null 2>&1 && [[ ! "$owner" =~ ^[0-9]+$ ]]; then
  echo "Owner existiert nicht und ist keine numerische UID: $owner" >&2
  exit 2
fi

if ! getent group "$group" >/dev/null 2>&1 && [[ ! "$group" =~ ^[0-9]+$ ]]; then
  echo "Group existiert nicht und ist keine numerische GID: $group" >&2
  exit 2
fi

install -d -o "$owner" -g "$group" -m "$mode" "$normalized_path"

actual_mode="$(stat -c '%a' "$normalized_path")"
actual_uid="$(stat -c '%u' "$normalized_path")"
actual_gid="$(stat -c '%g' "$normalized_path")"

expected_uid="$(id -u "$owner" 2>/dev/null || printf '%s' "$owner")"
expected_gid="$(getent group "$group" 2>/dev/null | cut -d: -f3 || true)"
if [[ -z "$expected_gid" ]]; then
  expected_gid="$group"
fi

if [[ "$actual_mode" != "${mode#0}" && "$actual_mode" != "$mode" ]]; then
  echo "Unerwarteter Modus für $normalized_path: $actual_mode" >&2
  exit 1
fi

if [[ "$actual_uid" != "$expected_uid" ]]; then
  echo "Unerwartete UID für $normalized_path: $actual_uid (erwartet $expected_uid)" >&2
  exit 1
fi

if [[ "$actual_gid" != "$expected_gid" ]]; then
  echo "Unerwartete GID für $normalized_path: $actual_gid (erwartet $expected_gid)" >&2
  exit 1
fi

echo "$normalized_path"
