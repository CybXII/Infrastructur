#!/usr/bin/env python3
"""Tests for the v0.5 platform validation evidence matrix."""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate-platform-validation.py"
MATRIX_PATH = REPO_ROOT / "configuration" / "platform-validation.json"

spec = importlib.util.spec_from_file_location("validate_platform_validation", VALIDATOR_PATH)
validator = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(validator)


class PlatformValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    def test_current_matrix_is_valid(self) -> None:
        self.assertEqual(validator.validate(self.matrix, REPO_ROOT), [])

    def test_missing_required_capability_fails(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["required_capabilities"].pop("rollback")
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("Pflichtfähigkeiten fehlen" in error for error in errors))

    def test_unknown_workflow_job_fails(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["required_capabilities"]["routing"]["evidence"][0][
            "job_id"
        ] = "does-not-exist"
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("does-not-exist" in error for error in errors))

    def test_missing_failure_mode_fails(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["failure_modes"] = [
            item
            for item in document["failure_modes"]
            if item["id"] != "failed-release"
        ]
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("Pflicht-Fehlerfälle fehlen" in error for error in errors))

    def test_cleanup_issue_must_be_completed(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["completed_items"] = [
            item
            for item in document["completed_items"]
            if item["issue"] != 231
        ]
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("#231 muss als abgeschlossenes" in error for error in errors))

    def test_open_items_fail_final_release_gate(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["known_open_items"].append(
            {
                "issue": 999,
                "title": "Künstlicher Blocker",
            }
        )
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("keine known_open_items" in error for error in errors))

    def test_review_issue_must_be_completed(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["completed_items"] = [
            item
            for item in document["completed_items"]
            if item["issue"] != 82
        ]
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("#82 muss als abgeschlossenes" in error for error in errors))

    def test_release_closure_must_be_approved(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["release_closure"]["decision"] = "pending"
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("Release-Abschluss muss approved" in error for error in errors))

    def test_release_closure_must_have_zero_blockers(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["release_closure"]["open_blockers"] = 1
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("keine offenen Abschlussblocker" in error for error in errors))

    def test_release_handoff_must_point_to_v06(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["release_closure"]["next_epic"] = 999
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("next_epic muss #83" in error for error in errors))

    def test_monitoring_release_must_remain_explicit(self) -> None:
        document = copy.deepcopy(self.matrix)
        document["monitoring_release"]["decision"] = "pending"
        errors = validator.validate(document, REPO_ROOT)
        self.assertTrue(any("Monitoring-Release" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
