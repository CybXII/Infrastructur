#!/usr/bin/env python3
"""Tests for the standard service template renderer."""

from __future__ import annotations

import importlib.util
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "render-service-template.py"

spec = importlib.util.spec_from_file_location("render_service_template", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ValueValidationTests(unittest.TestCase):
    def test_accepts_valid_values(self) -> None:
        module.validate_values(
            {
                "SERVICE_NAME": "example-service",
                "PUBLIC_HOSTNAME": "example.invalid",
                "IMAGE_REFERENCE": "ghcr.io/merchfactory/app@sha256:" + "a" * 64,
                "CONTAINER_PORT": "8080",
                "READINESS_PATH": "/ready",
                "SERVICE_UID": "1000",
                "SERVICE_GID": "1000",
            }
        )

    def test_rejects_invalid_service_name(self) -> None:
        with self.assertRaises(ValueError):
            module.validate_values({"SERVICE_NAME": "../escape"})

    def test_rejects_unpinned_image(self) -> None:
        with self.assertRaises(ValueError):
            module.validate_values(
                {"IMAGE_REFERENCE": "ghcr.io/merchfactory/app:latest"}
            )

    def test_rejects_invalid_readiness_path(self) -> None:
        with self.assertRaises(ValueError):
            module.validate_values({"READINESS_PATH": "ready?full=true"})

    def test_rejects_invalid_port(self) -> None:
        with self.assertRaises(ValueError):
            module.validate_values({"CONTAINER_PORT": "70000"})

    def test_rejects_non_numeric_uid(self) -> None:
        with self.assertRaises(ValueError):
            module.validate_values({"SERVICE_UID": "service-user"})


class RenderingTests(unittest.TestCase):
    def test_replaces_known_placeholders(self) -> None:
        rendered = module.render_text(
            "name={{SERVICE_NAME}} owner={{OWNER}}",
            {"SERVICE_NAME": "demo", "OWNER": "platform"},
        )
        self.assertEqual(rendered, "name=demo owner=platform")

    def test_leaves_unknown_placeholder_visible(self) -> None:
        rendered = module.render_text(
            "{{SERVICE_NAME}} {{UNKNOWN_VALUE}}",
            {"SERVICE_NAME": "demo"},
        )
        self.assertEqual(rendered, "demo {{UNKNOWN_VALUE}}")


if __name__ == "__main__":
    unittest.main()
