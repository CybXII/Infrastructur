# Monitoring-Runbook – v0.6 / Issue #97

**Geltung:** Die derzeitige Instanz ist ausschließlich **Development**. Dieses Runbook beschreibt die Reaktion auf die im Repository tatsächlich definierten Prometheus-Alarme und die bestehende Alertmanager/Discord-Zustellung. Staging-/Produktions-Rufbereitschaft, Kundendaten, Alarm-SLAs oder eine übergreifende Betreiberplattform werden damit **nicht** eingeführt.

## 1. Alarmannahme (jede FIRING-Meldung)

1. In Discord `FIRING`, `alertname`, `severity`, `environment`, `host`/`instance`, `service` und `summary` notieren. Bei leerem Feld tatsächliche Labels in Prometheus prüfen; **keinen Host oder Service raten**.
2. Prüfen, ob der Alert zur richtigen Umgebung gehört und zum aktuellen Zeitpunkt aktiv ist. In Grafana/Prometheus aktuelle Werte, erste Auslösung und ähnliche Warnungen derselben Umgebung ansehen. Der administrative Zugriff ist **privat per SSH-Tunnel/VPN**, nicht über öffentlich freigeschaltete Ports.
3. Auswirkungen konkret benennen: gesamter VPS unerreichbar, Monitoring-Collector gestört, eine App nicht erreichbar, Storage unter Druck, Backup-/Restore-Zustand unklar oder lediglich verspätete Scrapes.
4. Im zugehörigen Abschnitt unten **lesende** Diagnosen durchführen. Zeitstempel, Metrik, betroffene Ressource und belegten Fehler dokumentieren. Bei geplanten Deployments den laufenden CI-/Release-Status und den letzten guten SHA prüfen.
5. Nur eine klar begründete, autorisierte Maßnahme ausführen. **Keine** blinden Neustarts, `docker system prune`, manuelle TSDB-/Loki-Löschungen, Firewall-Eingriffe oder Restore in laufende Produktionsdaten.
6. Erholung über Metrik/Healthcheck und möglichst `RESOLVED` nachvollziehen. Ein `RESOLVED`-Signal beweist allein nicht, dass verlorene Daten, Jobs oder Backups wiederhergestellt wurden.

## 2. Priorisierung, Besitzer und Eskalation

**Tatsächlich im Code:** Die Alarmregeln nutzen `severity: high` oder `warning`. Die Alertmanager-Routen besitzen explizite Receiver nur für `critical`, `warning` und `info`. Bis zur #98-Korrektur fiel `high` auf **`discord-default`** zurück. Nach Deployment des #98-Patches werden `high` und `critical` explizit nach **`discord-critical`** geroutet; die tatsächliche Empfänger-/Discord-Abnahme bleibt in [#98](https://github.com/Merchfactory/Infrastructure/issues/98) offen.

| Label / Vorfall | Operative Behandlung auf Development | Primärverantwortung |
|---|---|---|
| `high`: Server/Collector/Probe/Backup-Ausfall oder kritischer Speicher | möglichst sofort während betreuter Zeiten prüfen; bei Datenrisiko priorisieren | Platform Owner, bei Datenrisiko Backup Owner |
| `warning`: Kapazität, Ressourcen, Zertifikatsfrist, Retries oder abgelaufener Test | während der regulären Betreuung prüfen und geplante Gegenmaßnahme dokumentieren | Platform Owner / betroffener Service Owner |
| `info` oder `RESOLVED` | verifizieren, dokumentieren, ohne unnötigen Eingriff | zuständiger Service Owner |
| Sicherheitsvorfall / mutmaßlicher Datenverlust | Zugriff und Auswirkungen sichern, Security-/Backup-Verantwortung einbinden; keine unkontrollierten Änderungen | Security Owner + Platform Owner, ggf. Backup Owner |

Der technische **Platform Owner** nimmt die initiale Entwicklungsmeldung an. Der **Service Owner** führt App- und Deployment-Diagnose; der **Backup Owner** bestätigt RPO/RTO/Restore und die **Security-Verantwortung** klärt Datenschutz-/Sicherheitsereignisse. Für Development besteht **keine garantierte 24/7-Bereitschaft oder feste Reaktions-SLA** (siehe `docs/69-discord-alerting.md`). Fehlen konkrete Verantwortliche oder ist der Platform Owner nicht erreichbar, muss die Zuordnung und der alternative Kontakt **vor produktivem Kundeneinsatz** festgelegt werden. Eskalationspfad in Kundensetups: erst betroffener Verantwortlicher, dann Betreiber-Vertretung und ggf. Kunde gemäß gesondertem Servicevertrag.

## 3. Sichere Basiskommandos auf Development

Ausführung nur mit berechtigtem SSH-Zugang und im **richtigen** Zielhost-Kontext. Die folgenden Prüfungen ändern keine laufenden Container oder Host-Firewall:

```bash
date -Is
hostnamectl
uptime
df -h
df -i
free -h
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
sudo systemctl --no-pager status docker node_exporter cadvisor alloy
sudo journalctl -u docker -n 80 --no-pager
```

Nicht jeder Dienst muss auf jedem späteren Server installiert sein; ein `Unit not found` ist zunächst gegen das verwaltete Inventar zu prüfen. Container-Logs nur für den eindeutig identifizierten Container abrufen, z.B. `sudo docker logs --tail 100 <containername>` (Platzhalter ersetzen; mögliche Tokens vor dem Teilen entfernen).

Monitoring-Core-Projekte: `merchfactory-development-prometheus`, `merchfactory-development-loki`, `merchfactory-development-alertmanager`, `merchfactory-development-grafana`, `merchfactory-development-blackbox`. Den exakten Container anhand der Compose-Labels ermitteln:

```bash
sudo docker ps --filter 'label=com.docker.compose.project=merchfactory-development-prometheus' --format 'table {{.Names}}\t{{.Status}}'
sudo docker ps --filter 'label=com.docker.compose.project=merchfactory-development-blackbox' --format 'table {{.Names}}\t{{.Status}}'
```

Grafana, Loki, Prometheus und Alertmanager **nicht öffentlich exponieren**, nur um eine Störung zu prüfen. Für GitHub-Deployments die Workflows `.github/workflows/tests.yml` und `.github/workflows/deploy-development-monitoring.yml` sowie `docs/66-development-monitoring-deployment.md` verwenden. Der Commit-/Image-Security-Gate und das bestehende Release-/Rollback-System bleiben verbindlich.

## 4. Vorfallmatrix – anhand tatsächlicher Alertnamen

| Alert(s) | Diagnose zuerst | Maßnahme / sichere Grenze | Verweis |
|---|---|---|---|
| `NodeExporterDown` | Host-/SSH-Erreichbarkeit, `systemctl status node_exporter`, Netz `merchfactory-monitoring`, Scrape-Target | Hostausfall und Exporter-Ausfall unterscheiden; kein blindes Netzwerk-Reset | `docs/63-node-exporter.md` |
| `CAdvisorDown` | `systemctl status cadvisor`, Docker-Dienst, Monitoring-Gateway/Port 8080 | Host-Agent-/Docker-Zustand prüfen; Docker-Socket-Zugriff nicht lockern | `docs/64-cadvisor.md` |
| `AlloyDown`, `AlloyLogDrops`, `AlloyWriteRetries`, `AlloyMemoryNearLimit` | `systemctl status alloy`, `journalctl -u alloy`, Loki-Bereitschaft, begrenzter Agent-State | Drops sind möglicher Logverlust; Loki/Alloy-Pfad priorisieren, keine unendliche Queue aktivieren | `docs/67-alloy.md`, `docs/65-loki.md` |
| `PrometheusSelfScrapeDown`, `PrometheusConfigurationReloadFailure`, `PrometheusRuleEvaluationFailures`, `PrometheusTSDBCompactionsFailing` | Prometheus-Container, letzte CI-Konfigurationsänderung, Rules-/Disk-Status | Bei Deploymentfehlern bestehendes Release-/Rollback-Verfahren nutzen; TSDB nicht manuell löschen | `docs/62-prometheus.md`, `docs/57-update-rollback.md` |
| `HostHighCPUUtilization`, `HostMemoryPressure` | `uptime`, `free -h`, laufende Docker-Container, jüngste Änderungen | Limit-/Lastursache zuordnen; keine Ressourcen-Limits ohne geprüftes Deployment überschreiben | `docs/63-node-exporter.md` |
| `HostFilesystemSpaceLow`, `HostFilesystemSpaceCritical`, `HostFilesystemInodesLow` | `df -h`, `df -i`, `du` für betroffene Pfade, Logspitzen, TSDB/Loki/Backups | Ab 75 % wachsen beobachten, ab 85 % dringlich; **nicht** per `rm -rf` Datenbestände oder Backups beseitigen | `docs/79-monitoring-retention-capacity.md` |
| `HostNetworkErrors`, `HostClockSkew` | NIC-Statistik bzw. `timedatectl status`, Systemjournal, Zeit-/Netzwerkänderungen | Ursache beim Host/Provider prüfen; keine remote Firewall-Reparatur ohne Rückfallpfad | `docs/63-node-exporter.md` |
| `BlackboxExporterUnavailable` | Laufender Blackbox-Container und internes Netz, Prometheus Scrape | In #95 ist zunächst nur der interne Exporter aktiv. **Keinen Egress-Smoke parallel** zu dessen Deployment erzwingen | `docs/74-external-probes-design.md`, `docs/77-blackbox-development-smoke-test.md` |
| `PublicEndpointHTTPUnavailable`, `PublicEndpointDNSFailure`, `PublicEndpointTLSFailure` | DNS vs. TLS vs. HTTP von unabhängiger Perspektive unterscheiden, Traefik-/App-Health prüfen | Aktuell erst nach expliziter Probe-Freigabe möglich; keine Tests an unautorisierten URLs | `docs/74-external-probes-design.md`, `docs/78-blackbox-security-lab-acceptance.md` |
| `PublicCertificateExpiringSoon`, `PublicCertificateExpiringCritical` | Ablaufdatum der tatsächlich ausgelieferten Kette prüfen, Traefik/ACME-Logs, Domain/DNS-Zuordnung | Erneuerungsfehler gezielt beheben; Zertifikat nicht ungetestet/manuell im Live-Routing ersetzen | `docs/74-external-probes-design.md` |
| `BackupJobFailed`, `BackupTooOld`, `RestoreTestFailed`, `RestoreTestTooOld` | `service`/`backup` Labels, Textfile-Collector und Job-Publisher, letzte reale Sicherung/Test-ID | Synthetischer E2E-Test ist **kein reales Backup**; keine Restore-Zusage ohne tatsächlichen Nachweis | `docs/70-backup-monitoring.md`, `docs/73-backup-monitoring-live-acceptance.md` |

**Nicht vorhandene Alarme sind keine stillschweigend aktive Überwachung:** Die derzeitigen Regeln alarmieren beispielsweise nicht automatisch jede einzelne App-Datenbank, jeden unhealthy Container oder jedes fehlgeschlagene Systemupdate. Das erfordert entsprechende Service-/Backup-/Update-Signale aus späteren Issues, nicht einen pauschalen Blackbox-Check auf jede API.

## 5. Spezielle Entscheidungspfade

### Komplettausfall des Development-VPS

Wenn kein SSH, keine App und kein internes Prometheus erreichbar sind, kann der **ausgefallene Prometheus selbst keine Discord-Meldung mehr auslösen**. Unabhängig per DNS/öffentlichem HTTP vom externen Prüfer und im VPS-Provider-Panel verifizieren. Der dokumentierte Windows-Watchdog prüft nur solange der Windows-Rechner läuft und ist **kein 24/7-SLA-Nachweis**. Zugang über Provider-Konsole und Infrastruktur-Hardening-Runbook (u. a. `docs/46-bootstrap-runbook.md`); Netzwerk-/Firewall-Konfiguration nicht blind ersetzen. Bei Root-/Dateisystem-Fehlern erst Erreichbarkeit und Sicherungsstand verifizieren.

### Fehlgeschlagenes Update / fehlerhafter Release

Den exakten GitHub-Commit, Runner/Workflow-Run, letzten guten Release und State des betroffenen Dienstes bestimmen. `docs/57-update-rollback.md` unterscheidet Datenänderung `none`, `compatible`, `destructive`. Nur einen **datenkompatiblen** Rollback auf bekannten guten Stand über den bestehenden Controller ausführen. Bei fehlerhafter/migrierter Datenbank kein automatisches älteres Image blind starten; Backup und Datenbankkompatibilität zuerst prüfen. `rollback-failed` ist ein Incident und kein erneuter Endlos-Retry.

### Backup-/Restore-Problem

Prüfen, ob ein **echter Job** oder die synthetische `monitoring-e2e-test`-Fixture alarmiert. Bei real fehlgeschlagenem Backup: keine Updates mit möglichem Datenverlust fortsetzen, Backup-Ziel/Kapazität/Keyzugriff des vorgesehenen Prozesses prüfen, letzte erfolgreiche Sicherung und deren Integrität bestimmen. Bei fehlgeschlagenem Restore-Test nicht automatisch von Nutzbarkeit ausgehen. Vor einer realen Wiederherstellung isoliertes Ziel, zuständigen Backup Owner und RPO/RTO festlegen. Backup-Engine und umfassender Wiederaufbau gehören zur v0.7/v0.8-Roadmap.

### Discord fehlt oder Meldung ist widersprüchlich

Prometheus Alertstatus, dann Alertmanager, dann `FIRING`/`RESOLVED` am Discord-Empfänger vergleichen. Zeitfenster beachten: Alert `for`, Evaluationsintervall, `group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 4h`. Inhibition, Gruppierung, ausbleibende Labels und Receiver prüfen. Keine Testalerts auf Productive-Webhook ohne Freigabe. Discord ist aktuell **ein einziger Benachrichtigungskanal**. `high` wurde vor #98 über `discord-default` versandt; nach dem neuen Deployment muss die `discord-critical`-Route verifiziert werden (siehe §2).

## 6. Incident dokumentieren und abschließen

Für jeden erheblichen Alarm ein kurzes Issue-/Vorfallsprotokoll hinterlegen (keine Kundengeheimnisse):

```text
UTC-Zeit Erstmeldung:
Umgebung / Host / Service:
Alarmname / Severity / Labels:
FIRING empfangen (Zeit):
Auswirkung / betroffene Nutzer:
Diagnose / Messwerte / Korrelations-SHA:
Ursache (gesichert / vermutet):
Maßnahme und verantwortliche Person/Rolle:
Status nach Korrektur (Health, Metrik, Logs):
RESOLVED empfangen (Zeit / falls nicht: Grund):
Datenintegrität / Backup-/Restore-Zustand:
Prävention / Follow-up-Issue:
```

Ein Vorfall ist erst abgeschlossen, wenn Ursache/Betriebsauswirkung, verifizierter Normalzustand und notwendige Nacharbeiten dokumentiert sind. Reine `RESOLVED`-Nachrichten beenden keinen Datenverlustvorfall.

## 7. Runbook- und Alarmtest-Abnahme

- [x] Alarmnamen aus allen aktuell vorhandenen Prometheus-Regeldateien mit Diagnose-/Reaktionspfaden abgedeckt.
- [x] Verantwortung, Eskalation, fehlende 24/7-Bereitschaft und nicht aufgelöster `high`-Routingvertrag dokumentiert.
- [x] Ohne Chat nutzbare, nichtdestruktive Basiskommandos und Incident-Protokoll enthalten.
- [ ] Entwicklungsläufe für mindestens Server/Plattenalarm, Backupfehler, Collector-Ausfall und Discord FIRING/RESOLVED protokolliert ([#98](https://github.com/Merchfactory/Infrastructure/issues/98)).
- [ ] Eskalationskette und Zuordnung der späteren Kunden-/Produktionsrollen vor Production freigegeben.

Änderungen an Alarmnamen müssen die Abdeckungsprüfung `tests/unit/test_monitoring_runbook.py` bestehen. Das Runbook schafft **keine** zusätzliche Runtime- oder Monitoring-Komponente.
