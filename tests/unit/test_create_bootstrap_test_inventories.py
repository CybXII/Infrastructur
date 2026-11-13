#!/usr/bin/env python3
"""Unit tests for the ephemeral fresh-host inventory generator."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY_ROOT / "scripts/create-bootstrap-test-inventories.py"


class CreateBootstrapTestInventoriesTest(unittest.TestCase):
    def run_generator(
        self, public_key: str, runner_host: bool = False
    ) -> tuple[subprocess.CompletedProcess, Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        temporary_path = Path(temporary_directory.name)
        public_key_path = temporary_path / "bootstrap.pub"
        public_key_path.write_text(public_key, encoding="utf-8")

        command = [
            "python3",
            str(SCRIPT),
            "--host",
            "bootstrap.example.invalid",
            "--initial-user",
            "root",
            "--managed-user",
            "bootstrap",
            "--public-key-file",
            str(public_key_path),
            "--initial-output",
            str(temporary_path / "initial.json"),
            "--managed-output",
            str(temporary_path / "managed.json"),
        ]
        if runner_host:
            command.append("--runner-host")

        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        return result, temporary_path

    def test_creates_separate_initial_and_managed_users(self) -> None:
        result, temporary_path = self.run_generator(
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey example"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        initial = json.loads((temporary_path / "initial.json").read_text())
        managed = json.loads((temporary_path / "managed.json").read_text())
        initial_host = initial["all"]["children"]["bootstrap_targets"][
            "hosts"
        ]["bootstrap-test"]
        managed_host = managed["all"]["children"]["bootstrap_targets"][
            "hosts"
        ]["bootstrap-test"]

        self.assertEqual(initial_host["ansible_user"], "root")
        self.assertEqual(managed_host["ansible_user"], "bootstrap")
        self.assertEqual(
            managed_host["user_management_users"][0]["name"],
            "bootstrap",
        )
        self.assertEqual(
            managed_host["ssh_hardening_allow_users"],
            ["bootstrap"],
        )
        self.assertNotIn("runner_hosts", managed["all"]["children"])

    def test_can_assign_managed_host_to_runner_hosts(self) -> None:
        result, temporary_path = self.run_generator(
            "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey example",
            runner_host=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        managed = json.loads((temporary_path / "managed.json").read_text())
        runner_hosts = managed["all"]["children"]["runner_hosts"]["hosts"]

        self.assertIn("bootstrap-test", runner_hosts)

    def test_rejects_invalid_public_key(self) -> None:
        result, temporary_path = self.run_generator("not-a-public-key")

        self.assertEqual(result.returncode, 2)
        self.assertIn("configuration_invalid", result.stdout)
        self.assertFalse((temporary_path / "initial.json").exists())
        self.assertFalse((temporary_path / "managed.json").exists())


if __name__ == "__main__":
    unittest.main()
