#!/usr/bin/env python3
"""Read-only readiness assessment for the proposed Blackbox network policy.

Never invokes nft -f, firewalld reload or Docker network creation. Local host
assessment is only one gate; a lab/live negative-traffic test is still required.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

EXPECTED_NETWORK = "merchfactory-probe-egress"
EXPECTED_BRIDGE = "mf-probe-egress"
EXPECTED_SUBNET = "172.30.252.0/29"
EXPECTED_GATEWAY = "172.30.252.1"
EXPECTED_MONITORING = "merchfactory-monitoring"


def verify_docker_network(network: dict) -> list[str]:
    errors = []
    if network.get("Name") != EXPECTED_NETWORK:
        errors.append("wrong Docker network name")
    if network.get("Driver") != "bridge" or network.get("Internal") is not False:
        errors.append("network must be an external bridge (Internal=false)")
    if network.get("EnableIPv6") is not False:
        errors.append("Docker IPv6 must be disabled on the probe network")
    labels = network.get("Labels") or {}
    if labels.get("com.merchfactory.network.class") != "probe-egress":
        errors.append("missing probe-egress network class")
    if labels.get("com.merchfactory.managed") != "true":
        errors.append("missing platform-managed label")
    opts = network.get("Options") or {}
    if opts.get("com.docker.network.bridge.name") != EXPECTED_BRIDGE:
        errors.append("unexpected Linux bridge")
    ipam = (network.get("IPAM") or {}).get("Config") or []
    if len(ipam) != 1 or ipam[0].get("Subnet") != EXPECTED_SUBNET or ipam[0].get("Gateway") != EXPECTED_GATEWAY:
        errors.append("unexpected network IPAM")
    return errors


def check_candidate(policy: pathlib.Path, network_json: dict, nft_binary="nft") -> list[str]:
    errors = verify_docker_network(network_json)
    if not policy.is_file():
        return errors + ["missing nftables candidate file"]
    try:
        result = subprocess.run([nft_binary, "-c", "-f", str(policy)],
                                capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"nft syntax validation not executed: {exc}")
    else:
        if result.returncode:
            errors.append(f"nft check failed: {result.stderr.strip()[:500]}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="Check only. Never apply firewall rules.")
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--docker-network-json", type=pathlib.Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.docker_network_json.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if len(data) != 1:
            parser.error("expected exactly one docker inspect object")
        data = data[0]
    if not isinstance(data, dict):
        parser.error("Docker inspect must be an object")
    errors = check_candidate(args.policy, data)
    if errors:
        for error in errors:
            print("BLOCKED:", error)
        raise SystemExit(1)
    print("READ-ONLY PREFLIGHT PASSED; this is NOT approval to apply the firewall.")


if __name__ == "__main__":
    main()
