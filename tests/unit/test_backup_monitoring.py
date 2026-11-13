#!/usr/bin/env python3
"""Contract tests for backup monitoring."""
from __future__ import annotations
import json, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
RULES=(ROOT/"monitoring/prometheus/rules/backup.yml").read_text(encoding="utf-8")
DOC=(ROOT/"docs/70-backup-monitoring.md").read_text(encoding="utf-8")
DASH=json.loads((ROOT/"monitoring/grafana/dashboards/backup-overview.json").read_text(encoding="utf-8"))
class BackupMonitoringTests(unittest.TestCase):
    def test_required_alerts_exist(self):
        for alert in ("BackupJobFailed","BackupTooOld","RestoreTestFailed","RestoreTestTooOld"):
            self.assertIn(f"alert: {alert}",RULES)
    def test_metric_contract_covers_dod(self):
        for metric in ("merchfactory_backup_last_success","merchfactory_backup_last_success_timestamp_seconds","merchfactory_backup_duration_seconds","merchfactory_backup_size_bytes","merchfactory_backup_restore_test_last_success","merchfactory_backup_restore_test_last_success_timestamp_seconds"):
            self.assertIn(metric,DOC)
    def test_dashboard_covers_status_age_duration_size_restore(self):
        titles={p["title"] for p in DASH["panels"]}
        self.assertEqual(titles,{"Letzter Backup-Status","Letzter Restore-Test","Backup-Laufzeit","Backup-Größe","Alter des letzten erfolgreichen Backups"})
        self.assertEqual(DASH["time"],{"from":"now-7d","to":"now"})
        self.assertFalse(DASH["editable"])
if __name__=="__main__": unittest.main()
