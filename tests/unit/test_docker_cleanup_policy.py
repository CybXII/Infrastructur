#!/usr/bin/env python3
"""Tests for safe Docker retention and cleanup policy."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "docker-retention-cleanup.py"
POLICY_PATH = REPO_ROOT / "configuration" / "docker-cleanup-policy.json"
DEPLOYMENT_POLICY_PATH = REPO_ROOT / "configuration" / "deployment-policy.json"
ROLE_DEFAULTS_PATH = (
    REPO_ROOT / "ansible" / "roles" / "docker_cleanup" / "defaults" / "main.yml"
)
SERVICE_TEMPLATE_PATH = (
    REPO_ROOT
    / "ansible"
    / "roles"
    / "docker_cleanup"
    / "templates"
    / "merchfactory-docker-cleanup.service.j2"
)
TIMER_TEMPLATE_PATH = (
    REPO_ROOT
    / "ansible"
    / "roles"
    / "docker_cleanup"
    / "templates"
    / "merchfactory-docker-cleanup.timer.j2"
)

spec = importlib.util.spec_from_file_location("docker_retention_cleanup", SCRIPT_PATH)
cleanup = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = cleanup
spec.loader.exec_module(cleanup)


class DockerCleanupPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.deployment_policy = json.loads(
            DEPLOYMENT_POLICY_PATH.read_text(encoding="utf-8")
        )
        cls.role_defaults = ROLE_DEFAULTS_PATH.read_text(encoding="utf-8")
        cls.service_template = SERVICE_TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.timer_template = TIMER_TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_retention_defaults(self) -> None:
        retention = self.policy["retention"]
        self.assertEqual(retention["stopped_managed_containers_days"], 7)
        self.assertEqual(retention["unused_allowed_images_days"], 30)
        self.assertEqual(retention["dangling_images_days"], 7)
        self.assertEqual(retention["build_cache_retention"], "168h")

    def test_rollback_history_matches_deployment_policy(self) -> None:
        self.assertEqual(
            self.policy["deployment_state"]["protected_previous_versions"],
            self.deployment_policy["state"]["protected_previous_versions"],
        )
        self.assertEqual(
            self.policy["deployment_state"]["protected_previous_versions"],
            2,
        )

    def test_volumes_and_force_removal_are_disabled(self) -> None:
        safety = self.policy["safety"]
        self.assertFalse(safety["remove_volumes"])
        self.assertFalse(safety["force_remove_images"])
        self.assertNotIn("volume prune", SCRIPT_PATH.read_text(encoding="utf-8"))
        self.assertNotIn("system prune", SCRIPT_PATH.read_text(encoding="utf-8"))

    def test_schedule_matches_role_defaults(self) -> None:
        self.assertIn(
            'docker_cleanup_on_calendar: "Sun *-*-* 04:30:00"',
            self.role_defaults,
        )
        self.assertIn(
            "docker_cleanup_randomized_delay_sec: 900",
            self.role_defaults,
        )
        self.assertIn("OnCalendar={{ docker_cleanup_on_calendar }}", self.timer_template)
        self.assertIn(
            "RandomizedDelaySec={{ docker_cleanup_randomized_delay_sec }}",
            self.timer_template,
        )

    def test_systemd_service_runs_apply_with_explicit_policies(self) -> None:
        self.assertIn("--apply", self.service_template)
        self.assertIn("--policy", self.service_template)
        self.assertIn("--image-policy", self.service_template)
        self.assertIn("--deployment-state-root", self.service_template)
        self.assertIn("--report", self.service_template)

    def test_canonical_repository(self) -> None:
        self.assertEqual(
            cleanup.canonical_repository("traefik:latest"),
            "docker.io/library/traefik",
        )
        self.assertEqual(
            cleanup.canonical_repository(
                "ghcr.io/merchfactory/app@sha256:" + "a" * 64
            ),
            "ghcr.io/merchfactory/app",
        )

    def test_stable_release_state_protects_current_and_two_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            service = root / "service-a"
            service.mkdir()
            (service / "state.json").write_text(
                json.dumps(
                    {
                        "current": {"image": "image-current"},
                        "previous": [
                            {"image": "image-prev-1"},
                            {"image": "image-prev-2"},
                            {"image": "image-prev-3"},
                        ],
                        "last_attempt": {"status": "success"},
                    }
                ),
                encoding="utf-8",
            )

            protected, blockers, states = cleanup.scan_release_states(
                root,
                {"success", "failed-rolled-back", "manual-rollback-success"},
                2,
            )

            self.assertEqual(
                protected,
                {"image-current", "image-prev-1", "image-prev-2"},
            )
            self.assertEqual(blockers, [])
            self.assertEqual(len(states), 1)

    def test_unstable_release_state_blocks_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            service = root / "service-a"
            service.mkdir()
            (service / "state.json").write_text(
                json.dumps(
                    {
                        "current": {"image": "image-current"},
                        "previous": [],
                        "last_attempt": {
                            "status": "failed-manual-intervention-required"
                        },
                    }
                ),
                encoding="utf-8",
            )

            _, blockers, _ = cleanup.scan_release_states(
                root,
                {"success", "failed-rolled-back", "manual-rollback-success"},
                2,
            )
            self.assertEqual(len(blockers), 1)
            self.assertIn("nicht cleanup-stabil", blockers[0])


if __name__ == "__main__":
    unittest.main()
