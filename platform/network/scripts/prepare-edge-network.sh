#!/usr/bin/env bash
set -Eeuo pipefail

network_name="${1:-${MERCHFACTORY_EDGE_NETWORK:-merchfactory-edge}}"

expected_driver="bridge"
expected_class="edge"
expected_managed="true"

if docker network inspect "$network_name" >/dev/null 2>&1; then
  driver="$(docker network inspect --format '{{.Driver}}' "$network_name")"
  internal="$(docker network inspect --format '{{.Internal}}' "$network_name")"
  network_class="$(docker network inspect --format '{{ index .Labels "com.merchfactory.network.class" }}' "$network_name")"
  managed="$(docker network inspect --format '{{ index .Labels "com.merchfactory.managed" }}' "$network_name")"

  if [[ "$driver" != "$expected_driver" ]]; then
    echo "Netzwerk $network_name verwendet Treiber $driver statt $expected_driver." >&2
    exit 1
  fi

  if [[ "$internal" != "false" ]]; then
    echo "Edge-Netzwerk $network_name darf nicht internal=true sein." >&2
    exit 1
  fi

  if [[ "$network_class" != "$expected_class" || "$managed" != "$expected_managed" ]]; then
    echo "Netzwerk $network_name besitzt nicht die erwarteten Merchfactory-Plattform-Labels." >&2
    exit 1
  fi

  echo "$network_name"
  exit 0
fi

docker network create   --driver "$expected_driver"   --label "com.merchfactory.network.class=$expected_class"   --label "com.merchfactory.managed=$expected_managed"   "$network_name" >/dev/null

echo "$network_name"
