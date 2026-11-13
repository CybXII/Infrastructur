#!/usr/bin/env python3
"""Unit tests for service-specific image environment keys."""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "deployment" / "service-release.py"

spec = importlib.util.spec_from_file_location("service_release", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class ServiceReleaseImageEnvTests(unittest.TestCase):
    def test_parser_keeps_standard_default(self) -> None:
        args = module.build_parser().parse_args(
            ["status", "--state-file", "/tmp/state.json"]
        )
        self.assertEqual(args.image_env_key, "SERVICE_IMAGE_REFERENCE")

    def test_custom_image_env_key_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "release.env"
            module.write_release_env(
                path,
                "docker.io/example/app@sha256:" + "a" * 64,
                "LOKI_IMAGE_REFERENCE",
            )
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "LOKI_IMAGE_REFERENCE=docker.io/example/app@sha256:"
                + "a" * 64
                + "\n",
            )

    def test_valid_custom_key_is_accepted(self) -> None:
        module.validate_image_env_key("PROMETHEUS_IMAGE_REFERENCE")

    def test_invalid_key_is_rejected(self) -> None:
        for value in ("bad-key", "lowercase", "9PREFIX", "WITH SPACE", ""):
            with self.subTest(value=value):
                with self.assertRaises(module.DeploymentError):
                    module.validate_image_env_key(value)


if __name__ == "__main__":
    unittest.main()
