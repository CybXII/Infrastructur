#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFIER = (ROOT / "scripts/verify-monitoring-service.py").read_text(encoding="utf-8")
DEPLOY = (ROOT / "scripts/deploy-development-monitoring-core.sh").read_text(encoding="utf-8")


class MonitoringVerifierNetworkContractTests(unittest.TestCase):
    def test_verifier_supports_explicit_additional_networks(self) -> None:
        self.assertIn("additional_networks =", VERIFIER)
        self.assertIn("allowed_networks = {network, *additional_networks}", VERIFIER)
        self.assertIn("if set(networks) != allowed_networks:", VERIFIER)

    def test_alertmanager_explicitly_allows_egress_network(self) -> None:
        self.assertIn(
            '--verify-arg "200"   --verify-arg "$alerting_egress_network"',
            DEPLOY,
        )

    def test_other_services_do_not_receive_egress_network(self) -> None:
        self.assertEqual(DEPLOY.count('--verify-arg "$alerting_egress_network"'), 1)


if __name__ == "__main__":
    unittest.main()
