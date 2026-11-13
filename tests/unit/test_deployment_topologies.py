#!/usr/bin/env python3
"""Tests for flexible deployment topology placement."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "configuration" / "deployment-topologies.json"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-deployment-topologies.py"

spec = importlib.util.spec_from_file_location("validate_deployment_topologies", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


class DeploymentTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_policy_is_valid(self) -> None:
        self.assertEqual(validator.validate(self.policy), [])

    def test_current_profile_is_development_only(self) -> None:
        self.assertEqual(self.policy["current_profile"], "development-only")
        profile = self.policy["profiles"]["development-only"]
        self.assertEqual(profile["host_count"], 1)
        self.assertEqual(profile["active_environments"], ["development"])

    def test_supported_host_counts(self) -> None:
        expected = {
            "development-only": 1,
            "compact": 1,
            "standard": 2,
            "split-production": 3,
        }
        actual = {
            name: profile["host_count"]
            for name, profile in self.policy["profiles"].items()
            if name in expected
        }
        self.assertEqual(actual, expected)

    def test_compact_places_all_environments_on_one_host(self) -> None:
        profile = self.policy["profiles"]["compact"]
        self.assertEqual(len(profile["placements"]), 1)
        placement = next(iter(profile["placements"].values()))
        self.assertEqual(
            set(placement["environments"]),
            {"development", "staging", "production"},
        )
        self.assertTrue({"application", "database"}.issubset(set(placement["roles"])))

    def test_standard_colocates_production_app_and_database(self) -> None:
        profile = self.policy["profiles"]["standard"]
        production = profile["placements"]["production-host"]
        self.assertIn("production", production["environments"])
        self.assertTrue({"application", "database"}.issubset(set(production["roles"])))

    def test_split_production_separates_app_and_database(self) -> None:
        profile = self.policy["profiles"]["split-production"]
        app = set(profile["placements"]["production-app-host"]["roles"])
        db = set(profile["placements"]["production-database-host"]["roles"])
        self.assertIn("application", app)
        self.assertNotIn("database", app)
        self.assertIn("database", db)
        self.assertNotIn("application", db)

    def test_every_host_has_baseline_and_monitoring_agent(self) -> None:
        for profile_name, profile in self.policy["profiles"].items():
            for placement_name, placement in profile["placements"].items():
                with self.subTest(profile=profile_name, placement=placement_name):
                    roles = set(placement["roles"])
                    self.assertIn("host_baseline", roles)
                    self.assertIn("monitoring_agent", roles)

    def test_shared_host_isolation_contract_is_mandatory(self) -> None:
        rules = self.policy["rules"]
        self.assertTrue(rules["environment_isolation_required_on_shared_hosts"])
        self.assertTrue(
            {
                "compose_project",
                "network",
                "persistent_storage",
                "runtime_secrets",
                "database_credentials",
            }.issubset(set(rules["isolation_dimensions"]))
        )

    def test_public_database_exposure_is_forbidden(self) -> None:
        self.assertFalse(self.policy["rules"]["public_database_exposure_allowed"])

    def test_missing_monitoring_agent_fails(self) -> None:
        broken = copy.deepcopy(self.policy)
        broken["profiles"]["compact"]["placements"]["all-in-one-host"]["roles"].remove(
            "monitoring_agent"
        )
        errors = validator.validate(broken)
        self.assertTrue(any("monitoring_agent fehlt" in error for error in errors))

    def test_fixed_three_host_assumption_fails(self) -> None:
        broken = copy.deepcopy(self.policy)
        broken["profiles"]["compact"]["host_count"] = 3
        errors = validator.validate(broken)
        self.assertTrue(any("compact: host_count muss 1 sein" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
