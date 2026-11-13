"""Unit tests for development-only backup fixture generation."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "integration" / "backup-monitoring-e2e.py"
spec = importlib.util.spec_from_file_location("backup_fixture", SCRIPT)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class FixtureTests(unittest.TestCase):
    def test_success(self):
        data = fixture.metrics(1, 200000)
        self.assertIn("merchfactory_backup_last_success{", data)
        self.assertIn("merchfactory_backup_restore_test_last_success{", data)
        self.assertIn("} 1", data)

    def test_restore_failure_is_isolated(self):
        data = fixture.metrics(1, 200000, restore_failed=True)
        self.assertIn('merchfactory_backup_restore_test_last_success{service="monitoring-e2e-test",backup="synthetic-fixture"} 0', data)
        self.assertIn('merchfactory_backup_last_success{service="monitoring-e2e-test",backup="synthetic-fixture"} 1', data)

    def test_restore_stale_is_isolated(self):
        data = fixture.metrics(1, 200000, restore_stale=True)
        self.assertIn('merchfactory_backup_restore_test_last_success_timestamp_seconds{service="monitoring-e2e-test",backup="synthetic-fixture"} 27200', data)
        self.assertIn('merchfactory_backup_last_success_timestamp_seconds{service="monitoring-e2e-test",backup="synthetic-fixture"} 199940', data)


if __name__ == "__main__":
    unittest.main()
