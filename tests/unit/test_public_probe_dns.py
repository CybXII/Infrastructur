#!/usr/bin/env python3
"""No DNS/network required: supply synthetic resolver answers."""
import importlib.util
import pathlib
import socket
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("public_probe_dns", ROOT / "scripts/validate-public-probe-dns.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def resolver(*addresses):
    def query(host, _port, proto):
        assert proto == socket.IPPROTO_TCP
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET,
                 socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 0)) for ip in addresses]
    return query

MANIFEST = {
    "http": [{"url": "https://example.org/", "expected_status": 200}],
    "tls": [{"target": "example.org:443"}],
    "dns": [{"name": "example.org", "type": "A"}],
}

class PublicDNSGateTests(unittest.TestCase):
    def test_public_v4_only(self):
        self.assertEqual(gate.public_addresses("example.org", resolver("1.1.1.1")), ("1.1.1.1",))

    def test_public_v6_only(self):
        self.assertEqual(gate.public_addresses("example.org", resolver("2606:4700:4700::1111")), ("2606:4700:4700::1111",))

    def test_loopback_rejected(self):
        with self.assertRaises(PermissionError):
            gate.public_addresses("example.org", resolver("127.0.0.1"))

    def test_private_ipv4_rejected(self):
        with self.assertRaises(PermissionError):
            gate.public_addresses("example.org", resolver("10.10.0.3"))

    def test_ula_ipv6_rejected(self):
        with self.assertRaises(PermissionError):
            gate.public_addresses("example.org", resolver("fd00::2"))

    def test_link_local_rejected(self):
        with self.assertRaises(PermissionError):
            gate.public_addresses("example.org", resolver("169.254.169.254"))

    def test_mixed_public_and_private_is_rejected(self):
        with self.assertRaises(PermissionError):
            gate.public_addresses("example.org", resolver("1.1.1.1", "192.168.1.2"))

    def test_empty_resolution_is_rejected(self):
        with self.assertRaises(ValueError):
            gate.public_addresses("example.org", resolver())

    def test_network_lookup_failure_is_rejected(self):
        def failure(_host, _port, proto):
            raise socket.gaierror("failure")
        with self.assertRaises(ValueError):
            gate.public_addresses("example.org", failure)

    def test_manifest_hosts_are_deduplicated(self):
        self.assertEqual(gate.validate_public_targets(MANIFEST, resolver("1.1.1.1")),
                         {"example.org": ("1.1.1.1",)})

if __name__ == "__main__":
    unittest.main()
