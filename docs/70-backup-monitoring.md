# Backup-Monitoring

## Zweck

Issue #94 überwacht Backup- und Restore-Ergebnisse, implementiert aber bewusst keine Backup-Engine. Backup-Jobs veröffentlichen einen stabilen Prometheus-Vertrag über den Node-Exporter-Textfile-Collector.

## Metrikvertrag

Jedes überwachte Backup verwendet ausschließlich niedrig-kardinale Labels:

- `service`: stabiler Service-Name
- `backup`: stabiler Backup-Objektname

Pflichtmetriken:

```text
merchfactory_backup_last_success{service="...",backup="..."} 0|1
merchfactory_backup_last_run_timestamp_seconds{...} <unix>
merchfactory_backup_last_success_timestamp_seconds{...} <unix>
merchfactory_backup_duration_seconds{...} <seconds>
merchfactory_backup_size_bytes{...} <bytes>
merchfactory_backup_max_age_seconds{...} <seconds>
merchfactory_backup_restore_test_last_success{...} 0|1
merchfactory_backup_restore_test_last_run_timestamp_seconds{...} <unix>
merchfactory_backup_restore_test_last_success_timestamp_seconds{...} <unix>
merchfactory_backup_restore_test_max_age_seconds{...} <seconds>
```

Keine Pfade, IDs, Dateinamen, Zeitstempel oder Fehlermeldungen als Labels verwenden.

## Veröffentlichung

Die Metrikdatei wird atomar geschrieben: zunächst temporäre Datei im selben Dateisystem erzeugen, Inhalt vollständig schreiben und anschließend per `rename` ersetzen. Der Node Exporter liest nur fertige `.prom`-Dateien.

Hostpfad:

```text
/var/lib/merchfactory/node_exporter/textfile
```

Der Node-Exporter-Prozess erhält darauf ausschließlich Lesezugriff. Backup-/Restore-Jobs benötigen Schreibrecht auf den Hostpfad; das Node-Exporter-Hardening wird dafür nicht aufgeweicht.

## Alarmierung

- letzter Lauf fehlgeschlagen: `BackupJobFailed`, high
- erfolgreicher Stand älter als das vom Job veröffentlichte Maximum: `BackupTooOld`, high
- letzter Restore-Test fehlgeschlagen: `RestoreTestFailed`, high
- erfolgreicher Restore-Test älter als das veröffentlichte Maximum: `RestoreTestTooOld`, warning

Die Schwellenwerte werden pro Backup als Metrik veröffentlicht. Dadurch muss die zentrale Alertregel bei unterschiedlichen RPO-/Testintervallen nicht geändert werden.

## Abgrenzung

Die konkrete Backup-Engine, Verschlüsselung, Offsite-Übertragung und eigentliche Restore-Ausführung bleiben Aufgabe der Backup-/Restore-Implementierung. #94 definiert deren beobachtbaren Betriebsvertrag.

## Issue #94 – Abnahmestand (2026-10-14)

| Kriterium | Repository-Nachweis | Bewertung |
| --- | --- | --- |
| Fehlgeschlagene/veraltete Backups alarmieren | `monitoring/prometheus/rules/backup.yml`; synthetische FIRING/RESOLVED-Tests und Discord SUCCESS nach PR #319 | Synthetisch bestätigt |
| Laufzeit und Größe sichtbar | `monitoring/grafana/dashboards/backup-overview.json` mit `merchfactory_backup_duration_seconds` und `merchfactory_backup_size_bytes` | Dashboard-Definition vorhanden; Live-Darstellung mit realen Jobdaten noch zu prüfen |
| Restore-Teststatus berücksichtigt | `merchfactory_backup_restore_test_last_success` im Dashboard; `RestoreTestFailed` und `RestoreTestTooOld` in Regeln/E2E | Synthetisch bestätigt |

**Scope:** #94 stellt den Metrikvertrag, die Visualisierung und Alarmierung bereit, nicht die Backup-Engine. Ohne angebundene reale Backup-Jobs ist keine Aussage über die tatsächliche Backup-Abdeckung oder Wiederherstellbarkeit zulässig. Für die endgültige Issue-Abnahme die Live-Dashboard-Darstellung und die Einbindung der vorgesehenen Jobs prüfen; tatsächliche Restore-Tests bleiben eigenständige Arbeit. Siehe `docs/71-backup-monitoring-e2e.md`, ADR-0007 und ADR-0008.
