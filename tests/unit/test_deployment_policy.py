#!/usr/bin/env python3
"""Tests for the deployment/update and rollback policy."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTROLLER_PATH = REPO_ROOT / "deployment" / "service-release.py"
IMAGE_POLICY_PATH = REPO_ROOT / "configuration" / "container-image-policy.json"
DEPLOYMENT_POLICY_PATH = REPO_ROOT / "configuration" / "deployment-policy.json"
TEMPLATE_PATH = (
    REPO_ROOT / "templates" / "services" / "container-service" / "deployment" / "compose.yaml.template"
)

spec = importlib.util.spec_from_file_location("service_release", CONTROLLER_PATH)
controller = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(controller)


WHOAMI = (
    "docker.io/traefik/whoami@sha256:"
    "c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44"
)
TRAEFIK = (
    "docker.io/library/traefik@sha256:"
    "f86a2cab1b5c649070c49f883c743dd32d8485a56e3368c5f93b9e91f1e91259"
)


class DeploymentPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.image_policy = json.loads(IMAGE_POLICY_PATH.read_text(encoding="utf-8"))
        cls.deployment_policy = json.loads(
            DEPLOYMENT_POLICY_PATH.read_text(encoding="utf-8")
        )
        cls.template = TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_standard_template_uses_runtime_digest_override(self) -> None:
        self.assertIn(
            "${SERVICE_IMAGE_REFERENCE:-{{IMAGE_REFERENCE}}}",
            self.template,
        )

    def test_allowlisted_images_are_accepted(self) -> None:
        self.assertEqual(
            controller.validate_image(WHOAMI, self.image_policy),
            "third-party",
        )
        self.assertEqual(
            controller.validate_image(TRAEFIK, self.image_policy),
            "third-party",
        )

    def test_unpinned_image_is_rejected(self) -> None:
        with self.assertRaises(controller.DeploymentError):
            controller.validate_image(
                "docker.io/traefik/whoami:latest",
                self.image_policy,
            )

    def test_unknown_repository_is_rejected(self) -> None:
        with self.assertRaises(controller.DeploymentError):
            controller.validate_image(
                "docker.io/example/unknown@sha256:" + "a" * 64,
                self.image_policy,
            )

    def test_previous_releases_are_deduplicated_and_limited(self) -> None:
        current = {"image": "image-a"}
        previous = [
            {"image": "image-b"},
            {"image": "image-b"},
            {"image": "image-c"},
        ]
        result = controller.prior_releases(current, previous, limit=2)
        self.assertEqual([item["image"] for item in result], ["image-a", "image-b"])

    def test_production_requires_approval_reference(self) -> None:
        self.assertTrue(
            self.deployment_policy["approvals"]["production"][
                "approval_reference_required"
            ]
        )

    def _args(
        self,
        root: pathlib.Path,
        *,
        data_change: str = "none",
        rollback_mode: str = "automatic",
        backup_reference: str | None = None,
        restore_plan_reference: str | None = None,
        environment: str = "development",
        approval_reference: str | None = None,
    ) -> argparse.Namespace:
        compose = root / "compose.yaml"
        compose.write_text(
            "services:\n  test:\n    image: docker.io/traefik/whoami@sha256:"
            + "c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44\n",
            encoding="utf-8",
        )
        return argparse.Namespace(
            compose_file=compose,
            image_policy=IMAGE_POLICY_PATH,
            deployment_policy=DEPLOYMENT_POLICY_PATH,
            verify_url="http://127.0.0.1/health",
            verify_exec=None,
            environment=environment,
            approval_reference=approval_reference,
            data_change=data_change,
            rollback_mode=rollback_mode,
            backup_reference=backup_reference,
            restore_plan_reference=restore_plan_reference,
        )

    def test_compatible_change_requires_backup_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self._args(pathlib.Path(tmp), data_change="compatible")
            with self.assertRaises(controller.DeploymentError):
                controller.validate_common(args)

    def test_destructive_change_forbids_automatic_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self._args(
                pathlib.Path(tmp),
                data_change="destructive",
                backup_reference="backup:test",
                restore_plan_reference="restore:test",
                rollback_mode="automatic",
            )
            with self.assertRaises(controller.DeploymentError):
                controller.validate_common(args)

    def test_destructive_change_allows_manual_mode_with_backup_and_restore_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = self._args(
                pathlib.Path(tmp),
                data_change="destructive",
                backup_reference="backup:test",
                restore_plan_reference="restore:test",
                rollback_mode="manual",
            )
            controller.validate_common(args)


if __name__ == "__main__":
    unittest.main()
