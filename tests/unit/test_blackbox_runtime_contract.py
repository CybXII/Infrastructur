#!/usr/bin/env python3
"""Static acceptance checks for isolated Blackbox staging and separate manual egress testing."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]

class BlackboxRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = (ROOT / "deployment/monitoring/blackbox/compose.yaml").read_text()
        cls.staging = (ROOT / "deployment/monitoring/blackbox/compose.staging.yaml").read_text()
        cls.deploy = (ROOT / "scripts/deploy-development-monitoring-core.sh").read_text()
        cls.workflow = (ROOT / ".github/workflows/deploy-development-monitoring.yml").read_text()
        cls.network = (ROOT / "platform/network/scripts/prepare-probe-egress-network.sh").read_text()
        cls.config = (ROOT / "monitoring/blackbox/blackbox.yml").read_text()
        cls.policy = json.loads((ROOT / "configuration/container-image-policy.json").read_text())

    def test_pinned_image_and_policy_allowlist(self):
        self.assertRegex(self.compose, r"docker\.io/prom/blackbox-exporter@sha256:[0-9a-f]{64}")
        repos = {entry["repository"] for entry in self.policy["third_party"]}
        self.assertIn("docker.io/prom/blackbox-exporter", repos)

    def test_private_only_hardened_container(self):
        for setting in ("user: \"65534:65534\"", "read_only: true", "cap_drop:",
                        "- ALL", "no-new-privileges:true", "mem_limit:",
                        "pids_limit:", "cpus:"):
            self.assertIn(setting, self.compose)
        self.assertNotRegex(self.compose, r"(?m)^\s+ports:")
        self.assertNotIn("/var/run/docker.sock", self.compose)

    def test_dedicated_egress_not_alerting_network(self):
        self.assertIn("merchfactory-probe-egress", self.compose)
        self.assertIn("merchfactory-monitoring", self.compose)
        self.assertNotIn("merchfactory-alerting-egress", self.compose)
        self.assertIn("172.30.252.0/29", self.network)
        self.assertIn("mf-probe-egress", self.network)
        self.assertIn("com.merchfactory.network.class", self.network)

    def test_no_redirects_in_public_http_checks(self):
        self.assertIn("follow_redirects: false", self.config)

    def test_staging_is_isolated_and_integrated(self):
        self.assertIn("compose.staging.yaml", self.deploy)
        self.assertIn("development-blackbox", self.deploy)
        self.assertIn("verify-monitoring-service.py", self.deploy)
        self.assertIn("deployment/monitoring/blackbox", self.workflow)
        self.assertIn("monitoring/blackbox", self.workflow)
        self.assertNotIn("probe_egress:", self.staging)
        self.assertNotIn("merchfactory-probe-egress", self.staging)
        self.assertIn("monitoring:", self.staging)
        self.assertNotRegex(self.staging, r"(?m)^\s+ports:")
        self.assertIn("Blackbox staging blocks any active service probe targets", self.deploy)
        self.assertNotIn("prepare-probe-egress-network.sh", self.deploy)

if __name__ == "__main__":
    unittest.main()
