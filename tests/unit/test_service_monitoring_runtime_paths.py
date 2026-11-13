#!/usr/bin/env python3
"""Contract tests: shared service targets persist outside infrastructure releases."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PersistentServiceTargetsTests(unittest.TestCase):
    def test_prometheus_discovers_only_runtime_targets(self):
        conf = (ROOT / "monitoring/prometheus/prometheus.yml").read_text()
        self.assertIn("/etc/prometheus/service-targets/http/*.json", conf)
        self.assertIn("/etc/prometheus/service-targets/tls/*.json", conf)
        self.assertNotIn("/etc/prometheus/targets/services/", conf)

    def test_mount_is_read_only_and_platform_owned(self):
        compose = (ROOT / "deployment/monitoring/prometheus/compose.yaml").read_text()
        self.assertIn("PROMETHEUS_SERVICE_TARGETS_DIR", compose)
        self.assertIn("/srv/merchfactory/monitoring/targets", compose)
        self.assertIn("target: /etc/prometheus/service-targets\n        read_only: true", compose)

    def test_bootstrap_creates_target_directories_before_deploy(self):
        deploy = (ROOT / "scripts/deploy-development-monitoring-core.sh").read_text()
        self.assertIn('service_targets="/srv/merchfactory/monitoring/targets"', deploy)
        self.assertIn('"\u0024{service_targets}/http" "\u0024{service_targets}/tls"', deploy)
        self.assertIn('export PROMETHEUS_SERVICE_TARGETS_DIR="\u0024{service_targets}"', deploy)
        self.assertLess(deploy.index('service_targets="/srv/merchfactory/monitoring/targets"'),
                        deploy.index('python3 "\u0024controller" deploy'))


if __name__ == "__main__":
    unittest.main()
