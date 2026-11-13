#!/usr/bin/env bash
set -Eeuo pipefail

network_name="${1:-${MERCHFACTORY_ALERTING_EGRESS_NETWORK:-merchfactory-alerting-egress}}"

expected_driver="bridge"
expected_class="alerting-egress"
expected_managed="true"
expected_subnet="${MERCHFACTORY_ALERTING_EGRESS_SUBNET:-172.30.251.0/29}"
expected_gateway="${MERCHFACTORY_ALERTING_EGRESS_GATEWAY:-172.30.251.1}"
expected_bridge="${MERCHFACTORY_ALERTING_EGRESS_BRIDGE:-mf-alert-egress}"

if [[ -z "$expected_subnet" || -z "$expected_gateway" || -z "$expected_bridge" ]]; then
  echo "Alerting-Egress-Subnetz, Gateway und Bridge-Name müssen gesetzt sein." >&2
  exit 2
fi

if (( ${#expected_bridge} > 15 )); then
  echo "Linux-Bridge-Name darf höchstens 15 Zeichen lang sein: $expected_bridge" >&2
  exit 2
fi

if docker network inspect "$network_name" >/dev/null 2>&1; then
  driver="$(docker network inspect --format '{{.Driver}}' "$network_name")"
  internal="$(docker network inspect --format '{{.Internal}}' "$network_name")"
  network_class="$(docker network inspect --format '{{ index .Labels "com.merchfactory.network.class" }}' "$network_name")"
  managed="$(docker network inspect --format '{{ index .Labels "com.merchfactory.managed" }}' "$network_name")"
  subnet="$(docker network inspect --format '{{ (index .IPAM.Config 0).Subnet }}' "$network_name")"
  gateway="$(docker network inspect --format '{{ (index .IPAM.Config 0).Gateway }}' "$network_name")"
  bridge="$(docker network inspect --format '{{ index .Options "com.docker.network.bridge.name" }}' "$network_name")"

  if [[ "$driver" != "$expected_driver" || "$internal" != "false" ]]; then
    echo "Alerting-Egress-Netzwerk $network_name muss ein nicht-internes Bridge-Netz sein." >&2
    exit 1
  fi

  if [[ "$network_class" != "$expected_class" || "$managed" != "$expected_managed" ]]; then
    echo "Netzwerk $network_name besitzt nicht die erwarteten Merchfactory-Plattform-Labels." >&2
    exit 1
  fi

  if [[ "$subnet" != "$expected_subnet" || "$gateway" != "$expected_gateway" || "$bridge" != "$expected_bridge" ]]; then
    echo "Alerting-Egress-Netzwerk $network_name weicht von der freigegebenen Netzkonfiguration ab." >&2
    exit 1
  fi

  echo "$network_name"
  exit 0
fi

docker network create \
  --driver "$expected_driver" \
  --subnet "$expected_subnet" \
  --gateway "$expected_gateway" \
  --opt "com.docker.network.bridge.name=$expected_bridge" \
  --label "com.merchfactory.network.class=$expected_class" \
  --label "com.merchfactory.managed=$expected_managed" \
  "$network_name" >/dev/null

echo "$network_name"
