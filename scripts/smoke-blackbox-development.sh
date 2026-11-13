#!/usr/bin/env bash
set -Eeuo pipefail

# Manual, development-only smoke check for #95.
# Does not alter host nftables/firewalld, Traefik, or Prometheus.
# Blackbox retains unrestricted external bridge egress during this test:
# run ONLY with trusted probe targets on the development VPS.
#
# Usage:
#   sudo bash scripts/smoke-blackbox-development.sh check
#   sudo bash scripts/smoke-blackbox-development.sh start
#   sudo bash scripts/smoke-blackbox-development.sh verify https://example.org
#   sudo bash scripts/smoke-blackbox-development.sh stop
#
# 'start' deliberately requires explicit opt-in. The monitoring network
# must already exist. The egress network is created by the platform helper.
action="${1:-check}"
probe_target="${2:-}"
case "$action" in check|start|verify|stop) ;; *)
  echo "Usage: $0 {check|start|verify|stop}" >&2; exit 2;;
esac

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: Docker network operations require privilege." >&2
  exit 2
fi
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose="$root/deployment/monitoring/blackbox/compose.yaml"
project="merchfactory-development-blackbox"
export MERCHFACTORY_MONITORING_NETWORK=merchfactory-monitoring
export MERCHFACTORY_PROBE_EGRESS_NETWORK=merchfactory-probe-egress


check() {
  local net
  docker info >/dev/null
  net="$(docker network inspect "$MERCHFACTORY_MONITORING_NETWORK")"
  python3 -c '
import json,sys
v=json.load(sys.stdin)[0]
assert v["Driver"]=="bridge" and v["Internal"] is True
assert v["EnableIPv6"] is False
assert v["IPAM"]["Config"][0]["Subnet"]=="172.30.250.0/24"
assert v["Options"]["com.docker.network.bridge.name"]=="mf-monitoring0"
assert all(x.get("IPv4Address", "").split("/")[0]!="172.30.250.40" for x in v["Containers"].values())
' <<< "$net" || { echo "Monitoring network contract or .40 address preflight failed" >&2; return 1; }

  # Check for overlaps before creating a new Docker network. No mutation here.
  docker network inspect $(docker network ls --quiet) | python3 -c '
import ipaddress,json,sys
network=ipaddress.ip_network("172.30.252.0/29")
for obj in json.load(sys.stdin):
  for ipam in obj.get("IPAM",{}).get("Config",[]):
    if ipam.get("Subnet") and ipaddress.ip_network(ipam["Subnet"],strict=False).overlaps(network):
      if obj["Name"]!="merchfactory-probe-egress":
        raise SystemExit("Probe egress subnet overlaps with "+obj["Name"])
' || return 1
  docker compose -f "$compose" config --quiet
  echo "Preflight OK: no runtime modifications."
}

start() {
  check
  bash "$root/platform/network/scripts/prepare-probe-egress-network.sh"
  docker compose -p "$project" -f "$compose" up -d --no-build blackbox-exporter
  echo "Blackbox started for DEVELOPMENT smoke test. Verify and stop explicitly."
}

verify() {
  local status http tls host
  if [[ -z "$probe_target" ]]; then
    echo "verify requires an explicit trusted public HTTPS URL" >&2; return 2
  fi
  host="$(python3 - "$probe_target" <<'PY'
import ipaddress, sys
from urllib.parse import urlsplit
value = sys.argv[1]
try:
    url = urlsplit(value)
    hostname = url.hostname or ""
    if (url.scheme != "https" or not hostname or url.port not in (None, 443)
            or url.username or url.password or url.path not in ("", "/")
            or url.query or url.fragment or value != f"https://{hostname}"
            or len(hostname) > 253 or hostname.endswith(".")
            or not all(p and len(p) <= 63 and p[0].isalnum() and p[-1].isalnum()
                       and all(c.isalnum() or c == "-" for c in p) for p in hostname.split("."))
            or "." not in hostname):
        raise ValueError("invalid HTTPS hostname")
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("IP literals are not allowed")
    except ValueError as ex:
        if str(ex) == "IP literals are not allowed":
            raise
    print(hostname)
except (ValueError, TypeError):
    sys.exit("Provide a plain trusted HTTPS origin, e.g. https://example.org (no paths, ports or credentials)")
PY
)" || return 2
  status="$(docker compose -p "$project" -f "$compose" ps --status running --services)"
  if [[ "$status" != *"blackbox-exporter"* ]]; then
    echo "Blackbox container not running" >&2; return 1
  fi

  # Docker bridge is local; no public host port or ingress required.
  # --noproxy '*' avoids local HTTP proxy variables interfering with bridge checks.
  http="$(curl --noproxy '*' -fsS --connect-timeout 3 --max-time 20 --get \
    --data-urlencode 'module=http_2xx' --data-urlencode "target=$probe_target" \
    'http://172.30.250.40:9115/probe')"
  grep -q '^probe_success 1$' <<< "$http" || {
    echo "HTTP probe failed"; grep -E '^probe_(success|http_status_code)' <<< "$http" || true; return 1;
  }

  tls="$(curl --noproxy '*' -fsS --connect-timeout 3 --max-time 20 --get \
    --data-urlencode 'module=tcp_tls' --data-urlencode "target=$host:443" \
    'http://172.30.250.40:9115/probe')"
  grep -q '^probe_success 1$' <<< "$tls" || {
    echo "TLS probe failed"; grep '^probe_success' <<< "$tls" || true; return 1;
  }
  echo "HTTP and TLS probes OK for $host (probe_success=1)."
}

stop() {
  docker compose -p "$project" -f "$compose" down --remove-orphans
  echo "Blackbox smoke container stopped. Existing shared networks preserved."
}

"$action"
