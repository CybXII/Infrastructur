#!/usr/bin/env python3
"""Synthetic read-only nft readiness checks, no docker or root required."""
import importlib.util
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("blackbox_egress_readiness", ROOT / "scripts/check-blackbox-egress-readiness.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

GOOD = {
    "Name": "merchfactory-probe-egress", "Driver": "bridge",
    "Internal": False, "EnableIPv6": False,
    "Labels": {"com.merchfactory.network.class": "probe-egress",
               "com.merchfactory.managed": "true"},
    "Options": {"com.docker.network.bridge.name": "mf-probe-egress"},
    "IPAM": {"Config": [{"Subnet": "172.30.252.0/29", "Gateway": "172.30.252.1"}]},
}


class ReadinessTests(unittest.TestCase):
    def test_valid_topology(self):
        self.assertEqual(gate.verify_docker_network(GOOD), [])

    def test_wrong_bridge_is_blocked(self):
        altered = dict(GOOD, Options={"com.docker.network.bridge.name": "docker0"})
        self.assertTrue(gate.verify_docker_network(altered))

    def test_ipv6_enabled_is_blocked(self):
        self.assertIn("Docker IPv6 must be disabled on the probe network",
                      gate.verify_docker_network(dict(GOOD, EnableIPv6=True)))

    def test_missing_ipv6_flag_fails_closed(self):
        altered = dict(GOOD)
        altered.pop("EnableIPv6")
        self.assertTrue(gate.verify_docker_network(altered))

    def test_wrong_subnet_is_blocked(self):
        self.assertTrue(gate.verify_docker_network(dict(GOOD, IPAM={"Config": [{"Subnet": "172.30.1.0/24"}]})))

    def test_nft_check_only_never_apply(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "candidate.nft"
            p.write_text("table inet example {}")
            result = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch.object(gate.subprocess, "run", return_value=result) as command:
                self.assertEqual(gate.check_candidate(p, GOOD), [])
            self.assertEqual(command.call_args.args[0], ["nft", "-c", "-f", str(p)])

    def test_nft_parse_error_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "candidate.nft"
            p.write_text("broken")
            result = subprocess.CompletedProcess([], 1, "", "syntax error")
            with mock.patch.object(gate.subprocess, "run", return_value=result):
                self.assertTrue(gate.check_candidate(p, GOOD))

    def test_missing_nft_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "candidate.nft"
            p.write_text("table inet example {}")
            with mock.patch.object(gate.subprocess, "run", side_effect=FileNotFoundError("nft")):
                self.assertTrue(gate.check_candidate(p, GOOD))


if __name__ == "__main__":
    unittest.main()
