#!/usr/bin/env bash
set -Eeuo pipefail

# This script verifies/prepares the isolated probe egress bridge.
# It does NOT implement destination filtering. NEVER deploy Blackbox simply
# because this network exists; runtime firewall enforcement is a separate gate.
network_name="${1:-${MERCHFACTORY_PROBE_EGRESS_NETWORK:-merchfactory-probe-egress}}"
expected_subnet="172.30.252.0/29"
expected_gateway="172.30.252.1"
expected_bridge="mf-probe-egress"
expected_class="probe-egress"

if docker network inspect "$network_name" >/dev/null 2>&1; then
  driver="$(docker network inspect --format '{{.Driver}}' "$network_name")"
  internal="$(docker network inspect --format '{{.Internal}}' "$network_name")"
  label="$(docker network inspect --format '{{ index .Labels "com.merchfactory.network.class" }}' "$network_name")"
  managed="$(docker network inspect --format '{{ index .Labels "com.merchfactory.managed" }}' "$network_name")"
  subnet="$(docker network inspect --format '{{ (index .IPAM.Config 0).Subnet }}' "$network_name")"
  gateway="$(docker network inspect --format '{{ (index .IPAM.Config 0).Gateway }}' "$network_name")"
  bridge="$(docker network inspect --format '{{ index .Options "com.docker.network.bridge.name" }}' "$network_name")"
  if [[ "$driver" != "bridge" || "$internal" != "false" ||
        "$label" != "$expected_class" || "$managed" != "true" ||
        "$subnet" != "$expected_subnet" || "$gateway" != "$expected_gateway" ||
        "$bridge" != "$expected_bridge" ]]; then
    echo "ERROR: probe egress network differs from platform contract." >&2
    exit 1
  fi
  echo "$network_name"
  exit 0
fi

docker network create \
  --driver bridge \
  --subnet "$expected_subnet" \
  --gateway "$expected_gateway" \
  --opt "com.docker.network.bridge.name=$expected_bridge" \
  --label "com.merchfactory.network.class=$expected_class" \
  --label "com.merchfactory.managed=true" \
  "$network_name" >/dev/null

echo "$network_name"
