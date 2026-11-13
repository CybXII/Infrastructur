# Issue #94: Live-Abnahme auf Development

## Ausführung (read-only)

Auf dem Development-VPS im ausgecheckten Repository:

```bash
bash scripts/audit-backup-monitoring-dev.sh --environment=development
```

Das Skript fragt Prometheus ausschließlich innerhalb des vorhandenen Containers ab. Es verändert keine Dateien, Container, Timer oder Dienste und verwendet keinen öffentlich erreichbaren Port. Benötigt werden Docker-Berechtigung, Python 3 und `wget` im Prometheus-Container.

## Bewertung

1. `node_textfile_scrape_error` muss für den relevanten Node Exporter 0 sein; fehlende Serien sind **kein** Erfolg.
2. Für jeden real angebundenen Backup-Job müssen `merchfactory_backup_duration_seconds`, `merchfactory_backup_size_bytes` und `merchfactory_backup_last_success` mit stabilen `service`-/`backup`-Labels erscheinen. `monitoring-e2e-test` ist ausgeschlossen.
3. Restore-Teststatus muss aus einem echten, unabhängig ausgeführten Restore-Test stammen; synthetische E2E-Werte gelten nicht.
4. Die Grafana-Panels im Dashboard `merchfactory-backup-overview` müssen dieselben realen Zeitreihen zeigen.
5. Für jeden erwarteten Backup-Job die Datenquelle und den Publisher der `.prom`-Metrik dokumentieren. Fehlende Jobs sind explizite Abhängigkeiten und dürfen nicht als überwacht gelten.

## Abnahmeentscheidung

Ohne Laufzeitausgabe vom VPS ist keine Live-Abnahme möglich. Fehlende Metriken bedeuten, dass die eigentliche Backup-/Restore-Integration erst zu implementieren ist. Das Audit selbst löst keine langen GitHub Actions Runs aus. Keine produktiven Restore-Vorgänge allein für diesen Nachweis starten.

Die synthetischen Tests aus PR #319 und die Dokumentation aus PR #320 bleiben als getrennte, bereits bestätigte Evidenz erhalten.
