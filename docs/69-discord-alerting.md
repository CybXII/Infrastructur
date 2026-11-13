# Discord-Alarmierung

## Zweck

Dieses Dokument definiert den Betriebsvertrag für Benachrichtigungen aus dem Monitoring-Stack. Alertmanager ist die zentrale Routing-Instanz; Discord ist der aktuell freigegebene Alarmkanal.

## Kanalmodell

Für die aktuelle Development-Plattform wird ein gemeinsamer Discord-Monitoring-Kanal verwendet. Die Receiver `discord-critical`, `discord-warning`, `discord-info` und `discord-default` verwenden denselben Webhook. Spätere Trennung nach Kunde, Server oder Severity erfolgt über zusätzliche Receiver, ohne Prometheus-Alarmregeln zu duplizieren.

Der Webhook ist ein Secret und darf nicht im Repository, in Release-Artefakten oder Logs gespeichert werden. Das Deployment installiert ihn unter `/srv/merchfactory/secrets/alertmanager/discord-webhook-url`.

## Severity und Reaktion

| Severity | Bedeutung | Erwartete Reaktion |
|---|---|---|
| `critical` / `high` | Dienst oder wesentliche Plattformfunktion ausgefallen bzw. unmittelbar gefährdet | zuerst prüfen und zeitnah bearbeiten |
| `warning` | degradierter Zustand oder absehbares Betriebsrisiko | zeitnah während des regulären Betriebs prüfen |
| `info` | relevante Betriebsinformation ohne unmittelbaren Eingriffsbedarf | informativ; bei Bedarf prüfen |
| unbekannt | unvollständig klassifizierter Alert | wie `warning` behandeln und Klassifizierung korrigieren |

Für die Development-Plattform besteht keine 24/7-Bereitschaft und keine garantierte Reaktionszeit. Die Infrastrukturverantwortlichen betreuen den gemeinsamen Monitoring-Kanal im regulären Betrieb. Eine spätere formale Rufbereitschaft benötigt einen eigenen Betriebsvertrag.

## Nachrichtenvertrag

Jede Discord-Meldung muss Status `FIRING` oder `RESOLVED`, Severity, Umgebung, Server/Instance, Service, Alertname, Zusammenfassung und Beschreibung enthalten. `send_resolved: true` ist Pflicht.

## Eskalation

1. `critical` und `high` haben Vorrang vor `warning` und `info`.
2. Inhibition darf niedrigere Severities unterdrücken, wenn für denselben Dienst bereits ein Critical- oder Down/Unavailable-Alarm aktiv ist.
3. Nicht direkt einordenbare Critical-Alarme werden zuerst in Grafana/Prometheus und anschließend in den Service-/Host-Logs untersucht.
4. Discord ist bis zur Einführung eines zweiten unabhängigen Kanals ein Single Point of Notification.

## Kontrollierter Zustellungstest

Der reale Test wird ausschließlich gegen den Development-Alertmanager durchgeführt. Voraussetzung sind ein erfolgreich deployter Monitoring-Release, das GitHub Secret `DISCORD_WEBHOOK_URL`, die installierte Webhook-Datei und ein bereiter Alertmanager.

1. Testalert mit `environment=development`, `host`, `service` und `severity=warning` einspeisen.
2. `FIRING` in Discord inklusive Umgebung, Server und Service prüfen.
3. Testalert auflösen.
4. Zugehöriges `RESOLVED` in Discord prüfen.
5. Testzeitpunkt und Ergebnis in Issue #92 dokumentieren.

Der reale Webhook wird nicht in automatisierten Pull-Request-Tests verwendet. CI validiert ausschließlich den Konfigurationsvertrag.

## `high`-Routing, Dateisystemdetails und Live-Abnahme (#98)

Die Regeln verwenden `high` für dringliche Alarme; `critical` bleibt als
kompatible Severity erhalten. **Nach erfolgreichem Deployment dieser
Änderung** werden beide über den Receiver `discord-critical` geroutet.
Die Inhibition unterdrückt für dasselbe `environment`/`service`/`instance`
Warnungen und Informationen auch dann, wenn der Quellalarm `high` ist.
Der Discord-Titel zeigt den **ursprünglichen** Schweregrad (`high` oder
`critical`) und nicht fälschlich ein festes `critical`.

Alle vier Meldungstemplates enthalten bei vorhandenen Labels zusätzlich
`instance`, `mountpoint` und `device`, damit Dateisystemalarme
präzise dem betroffenen Mount zugeordnet werden können. `host` kann ein
externes Prometheus-Label sein und ist **nicht immer der SSH-Hostname**.

Die echten Zustellungs-, Inhibition- und Auflösungsnachweise sind im
[Abnahmeplan #98](81-alerting-e2e-acceptance.md) beschrieben. Der
gezielte Development-Smoke ist **opt-in** und wird weder in Pull-Request-
Tests noch automatisch beim Merge an den Discord-Webhook gesendet.

## Historischer Routingzustand vor #98

Bis zum Deployment der #98-Routingkorrektur fiel `high` in
`discord-default`. Die Meldungen wurden zwar zugestellt, aber nicht
explizit auf die dringliche Route klassifiziert. Der Betrieb auf
Development muss nach Merge und Deployment erneut kontrolliert werden.
Die Arbeitsabläufe sind im [Monitoring-Runbook](80-monitoring-runbook.md)
dokumentiert.

## Referenzen

- Issue #92
- Epic #83
- `monitoring/alertmanager/alertmanager.yml`
- `deployment/monitoring/alertmanager/compose.yaml`
- `docs/61-monitoring-stack.md`
- `docs/66-development-monitoring-deployment.md`
