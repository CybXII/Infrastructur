#!/usr/bin/env python3
"""Unit tests for the container image policy validator."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "validate-image-policy.py"
DEPLOY_SCRIPT_PATH = REPO_ROOT / "scripts" / "deploy-development-monitoring-core.sh"
IMAGE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "image-security.yml"
DEPLOY_WORKFLOW_PATH = (
    REPO_ROOT / ".github" / "workflows" / "deploy-development-monitoring.yml"
)

spec = importlib.util.spec_from_file_location("validate_image_policy", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

POLICY = {
    "first_party": {
        "registry": "ghcr.io",
        "namespace": "merchfactory",
    },
    "third_party": [
        {"repository": "docker.io/library/traefik"},
        {"repository": "docker.io/traefik/whoami"},
        {"repository": "quay.io/prometheus/prometheus"},
        {"repository": "docker.io/grafana/loki"},
        {"repository": "docker.io/grafana/grafana"},
        {"repository": "quay.io/prometheus/alertmanager"},
    ],
}


class CanonicalRepositoryTests(unittest.TestCase):
    def test_docker_official_image(self) -> None:
        _, repository = module.canonical_repository(
            "docker.io/library/traefik@sha256:" + "a" * 64
        )
        self.assertEqual(repository, "docker.io/library/traefik")

    def test_first_party_image(self) -> None:
        classification, repository = module.classify_image(
            "ghcr.io/merchfactory/odoo@sha256:" + "b" * 64,
            POLICY,
        )
        self.assertEqual(classification, "first-party")
        self.assertEqual(repository, "ghcr.io/merchfactory/odoo")

    def test_allowed_third_party_image(self) -> None:
        classification, _ = module.classify_image(
            "docker.io/traefik/whoami@sha256:" + "c" * 64,
            POLICY,
        )
        self.assertEqual(classification, "third-party")

    def test_prometheus_quay_image_is_allowed(self) -> None:
        classification, repository = module.classify_image(
            "quay.io/prometheus/prometheus@sha256:" + "d" * 64,
            POLICY,
        )
        self.assertEqual(classification, "third-party")
        self.assertEqual(repository, "quay.io/prometheus/prometheus")

    def test_loki_docker_hub_image_is_allowed(self) -> None:
        classification, repository = module.classify_image(
            "docker.io/grafana/loki@sha256:" + "e" * 64,
            POLICY,
        )
        self.assertEqual(classification, "third-party")
        self.assertEqual(repository, "docker.io/grafana/loki")

    def test_grafana_docker_hub_image_is_allowed(self) -> None:
        classification, repository = module.classify_image(
            "docker.io/grafana/grafana@sha256:" + "f" * 64,
            POLICY,
        )
        self.assertEqual(classification, "third-party")
        self.assertEqual(repository, "docker.io/grafana/grafana")

    def test_alertmanager_quay_image_is_allowed(self) -> None:
        classification, repository = module.classify_image(
            "quay.io/prometheus/alertmanager@sha256:" + "1" * 64,
            POLICY,
        )
        self.assertEqual(classification, "third-party")
        self.assertEqual(repository, "quay.io/prometheus/alertmanager")

    def test_unknown_registry_is_forbidden(self) -> None:
        classification, repository = module.classify_image(
            "registry.example.invalid/vendor/app@sha256:" + "d" * 64,
            POLICY,
        )
        self.assertEqual(classification, "forbidden")
        self.assertEqual(repository, "registry.example.invalid/vendor/app")


class ImageValidationTests(unittest.TestCase):
    def test_rejects_unpinned_image(self) -> None:
        document = {
            "services": {
                "app": {"image": "ghcr.io/merchfactory/app:latest"}
            }
        }
        errors, _ = module.validate_images(document, POLICY)
        self.assertTrue(any("sha256-Digest" in error for error in errors))

    def test_rejects_implicit_registry(self) -> None:
        document = {
            "services": {
                "proxy": {"image": "traefik@sha256:" + "e" * 64}
            }
        }
        errors, _ = module.validate_images(document, POLICY)
        self.assertTrue(any("Registry muss explizit" in error for error in errors))

    def test_accepts_explicit_allowlisted_image(self) -> None:
        document = {
            "services": {
                "proxy": {
                    "image": "docker.io/library/traefik@sha256:" + "f" * 64
                }
            }
        }
        errors, inventory = module.validate_images(document, POLICY)
        self.assertEqual(errors, [])
        self.assertEqual(inventory[0]["classification"], "third-party")


class AlertmanagerOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.deploy_script = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
        cls.image_workflow = IMAGE_WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.deploy_workflow = DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_alertmanager_is_deployed_and_verified(self) -> None:
        for fragment in (
            "/srv/merchfactory/deployments/development-alertmanager",
            "/srv/merchfactory/persistent/monitoring/alertmanager",
            "ALERTMANAGER_IMAGE_REFERENCE",
            "merchfactory-development-alertmanager",
            '--verify-arg "9093"',
            '--verify-arg "/-/ready"',
        ):
            self.assertIn(fragment, self.deploy_script)

    def test_alertmanager_is_packaged_for_deployment(self) -> None:
        self.assertIn("deployment/monitoring/alertmanager", self.deploy_workflow)
        self.assertIn("monitoring/alertmanager", self.deploy_workflow)

    def test_alertmanager_image_has_dedicated_scan(self) -> None:
        self.assertIn("alertmanager_image:", self.image_workflow)
        self.assertIn("deployment/monitoring/alertmanager/compose.yaml", self.image_workflow)
        self.assertIn("scan-alertmanager:", self.image_workflow)
        self.assertIn("needs.policy.outputs.alertmanager_image", self.image_workflow)


if __name__ == "__main__":
    unittest.main()
