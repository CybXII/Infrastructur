#!/usr/bin/env python3
"""Static safety contract for the explicit development-only Blackbox smoke script."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class SmokeScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = (ROOT / "scripts/smoke-blackbox-development.sh").read_text()
        cls.docs = (ROOT / "docs/77-blackbox-development-smoke-test.md").read_text()

    def test_default_action_is_readonly_preflight(self):
        self.assertIn('action="${1:-check}"', self.script)
        self.assertIn('check|start|verify|stop', self.script)

    def test_no_host_firewall_mutations(self):
        for forbidden in ("nft -f", "iptables -A", "firewall-cmd --permanent",
                          "systemctl stop firewalld", "docker network prune"):
            self.assertNotIn(forbidden, self.script)

    def test_no_public_port_or_unauthorized_probe_targets(self):
        self.assertNotIn("n8n.luft-alex.de", self.script)
        self.assertIn('probe_target="${2:-}"', self.script)
        self.assertIn("verify requires an explicit trusted public HTTPS URL", self.script)
        self.assertIn("IP literals are not allowed", self.script)
        self.assertIn('target=$probe_target', self.script)
        self.assertIn("--data-urlencode", self.script)
        self.assertNotIn("docker run --privileged", self.script)
        self.assertIn("172.30.250.40:9115", self.script)
        self.assertIn("probe_success 1", self.script)

    def test_stop_does_not_remove_existing_networks(self):
        self.assertIn('down --remove-orphans', self.script)
        self.assertNotIn("docker network rm", self.script)
        self.assertIn("nicht** die gemeinsam genutzten", self.docs)


if __name__ == "__main__":
    unittest.main()
