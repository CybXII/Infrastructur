#!/usr/bin/env bash
# Infrastructure-owned, root-installed, narrowly scoped one-time service directory
# provisioner. No arbitrary paths, owners, modes, or recursive chown.
set -Eeuo pipefail

if (( EUID != 0 )) || (( $# != 1 )); then
  echo "Usage: sudo -n /usr/local/sbin/merchfactory-provision-service <service>" >&2
  exit 2
fi

service="$1"
if [[ ! "$service" =~ ^[a-z][a-z0-9-]{0,39}$ ]]; then
  echo "Invalid service name (lowercase letters, digits and hyphens only)." >&2
  exit 2
fi

# No user-controlled paths, UID/GID or permission flags. The deploy account
# is already Docker-group/root-equivalent on this trusted development host.
for root in /opt/merchfactory/apps /opt/merchfactory/backups /srv/merchfactory/persistent; do
  if [[ ! -d "$root" || -L "$root" || "$(stat -c '%U:%G' "$root")" != "root:root" ]]; then
    echo "Missing or untrusted platform directory: $root" >&2
    exit 1
  fi
done

owner=deploy
group=deploy
owner_uid="$(id -u "$owner")"
group_gid="$(getent group "$group" | cut -d: -f3)"

provision() {
  local parent="$1" mode="$2" target="$1/$service"
  if [[ -L "$target" ]]; then
    echo "Refusing symlink: $target" >&2
    exit 1
  fi
  if [[ -e "$target" ]]; then
    [[ -d "$target" ]] || { echo "Not a directory: $target" >&2; exit 1; }
    [[ "$(stat -c '%u:%g' "$target")" == "$owner_uid:$group_gid" ]] || {
      echo "Existing directory ownership differs; manual migration required: $target" >&2
      exit 1
    }
    [[ "$(stat -c '%a' "$target")" == "${mode#0}" ]] || {
      echo "Existing directory mode differs; manual review required: $target" >&2
      exit 1
    }
  else
    install -d -o "$owner" -g "$group" -m "$mode" "$target"
  fi
  printf 'Ready: %s\n' "$target"
}

provision /opt/merchfactory/apps 0750
provision /opt/merchfactory/backups 0700
provision /srv/merchfactory/persistent 0750
