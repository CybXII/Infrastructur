import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class MonitoringVerifierStatusTest(unittest.TestCase):
    def test_verifier_accepts_explicit_status_set(self):
        verifier = (ROOT / "scripts/verify-monitoring-service.py").read_text(encoding="utf-8")
        self.assertIn('.split(",")', verifier)
        self.assertIn("response.status not in expected_statuses", verifier)
        self.assertIn("exc.code not in expected_statuses", verifier)

    def test_grafana_declares_only_200_and_401(self):
        deploy = (ROOT / "scripts/deploy-development-monitoring-core.sh").read_text(encoding="utf-8")
        grafana_call = deploy.split("--service grafana", 1)[1]
        self.assertIn('--verify-arg "200,401"', grafana_call)


if __name__ == "__main__":
    unittest.main()
