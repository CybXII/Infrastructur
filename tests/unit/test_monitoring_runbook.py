#!/usr/bin/env python3
"""Coverage guard for the v0.6 operational runbook (#97)."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "monitoring/prometheus/rules"
DOC = ROOT / "docs/80-monitoring-runbook.md"

class MonitoringRunbookTests(unittest.TestCase):
    def test_every_configured_alert_has_a_documented_response(self):
        text = DOC.read_text(encoding="utf-8")
        for path in sorted(RULES.glob("*.yml")):
            rules = path.read_text(encoding="utf-8")
            names = re.findall(r"(?m)^\s*- alert:\s*([A-Za-z][A-Za-z0-9_]*)\s*$", rules)
            self.assertTrue(names, f"No alert names found in {path.name}")
            for name in names:
                with self.subTest(file=path.name, alert=name):
                    self.assertIn(f"`{name}`", text)

    def test_operational_contract(self):
        t = DOC.read_text(encoding="utf-8")
        for required in ("FIRING", "RESOLVED", "Platform Owner", "Backup Owner",
                         "Security Owner", "Service Owner", "discord-default",
                         "high", "keine garantierte 24/7", "Rollback",
                         "docs/57-update-rollback.md", "docs/79-monitoring-retention-capacity.md",
                         "docs/73-backup-monitoring-live-acceptance.md"):
            with self.subTest(required=required):
                self.assertIn(required, t)

    def test_never_offer_disruptive_copy_paste_remedies(self):
        t = DOC.read_text(encoding="utf-8")
        for forbidden in ("sudo docker system prune -af", "sudo rm -rf /srv/merchfactory",
                          "sudo systemctl stop firewalld"):
            self.assertNotIn(forbidden, t)

if __name__ == "__main__":
    unittest.main()
