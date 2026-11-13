# Log-Rotation und lokale Aufbewahrung

## Zweck

Dieses Dokument definiert die verbindliche lokale Log-Rotation und Aufbewahrung für die Merchfactory Container Platform. Es setzt Issue #78 um und konkretisiert die bereits bestehenden Logging-Standards aus `docs/27-logging-standards.md`.

Ziel ist, dass Container- oder Systemlogs einen Host nicht unkontrolliert füllen und dass lokale Aufbewahrung mit der späteren zentralen Logplattform abgestimmt bleibt.

## Container-Logs

Container schreiben Anwendungsausgaben nach `stdout` und Fehler nach `stderr`.

Der Docker-Daemon verwendet verbindlich den Logging Driver:

```text
local
```

Standard:

```text
max-size: 20m
max-file: 5
compress: true
```

Damit stehen pro Container maximal fünf lokale Logsegmente mit jeweils bis zu 20 MiB vor Kompression zur Verfügung. Der `local`-Driver rotiert die Dateien automatisch.

Anwendungen schreiben keine zusätzlichen unkontrollierten Logdateien in den Container-Layer.

## Compose-Regel

Standard-Services erben die Logging-Konfiguration des Docker-Daemons.

Ein servicebezogener `logging:`-Override ist standardmäßig nicht zulässig. Damit kann ein einzelner Compose-Stack die globale Rotationsgrenze nicht versehentlich durch `json-file` ohne Rotation oder einen unkontrollierten Driver umgehen.

Eine Abweichung benötigt eine dokumentierte Plattform-/Observability-Entscheidung.

## Systemlogs / journald

Host-Systemlogs werden persistent über systemd-journald gespeichert.

Verbindliche Werte:

```text
Storage=persistent
SystemMaxUse=512M
SystemKeepFree=1G
SystemMaxFileSize=64M
RuntimeMaxUse=64M
RuntimeKeepFree=128M
RuntimeMaxFileSize=16M
MaxRetentionSec=30day
MaxFileSec=1day
Compress=yes
```

### Bedeutung

- `SystemMaxUse` begrenzt die persistente Journal-Gesamtgröße.
- `SystemKeepFree` reserviert freien Speicher für das restliche System.
- `SystemMaxFileSize` sorgt für kleinere Rotationssegmente.
- Runtime-Limits begrenzen Journal-Daten während früher Bootphasen.
- `MaxRetentionSec=30day` setzt zusätzlich eine Zeitgrenze.
- `MaxFileSec=1day` sorgt für tägliche Journal-Segmente, auch bei geringer Lograte.

Die Konfiguration wird über die Ansible-Rolle `system_logging` unter `/etc/systemd/journald.conf.d/60-merchfactory-retention.conf` verwaltet.

## Zentrale Logaufbewahrung

Lokale Logs sind ein Betriebsbuffer und keine langfristige Archivplattform.

Die zentrale Logplattform verwendet folgende Zielklassen, sofern kein strengerer rechtlicher oder fachlicher Bedarf gilt:

| Klasse | Zentrale Aufbewahrung |
|---|---:|
| Debug | 7 Tage |
| Standard-Betriebslogs | 30 Tage |
| Fehlerlogs | 90 Tage |
| Security-relevante Logs | 365 Tage |
| Audit-relevante Ereignisse | 365 Tage |
| Deployment-/Backup-Nachweise | 365 Tage |

Damit werden bestehende Richtwerte aus Monitoring und Logging vereinheitlicht.

Die konkrete Produktauswahl für den zentralen Log-Stack bleibt eine separate Architekturentscheidung.

## Ausfall der zentralen Logplattform

Ein Ausfall der zentralen Weiterleitung darf Anwendungen nicht unbegrenzt blockieren.

Grundregeln:

- lokale Containerlogs bleiben durch Docker begrenzt,
- Systemlogs bleiben durch journald begrenzt,
- lokale Buffer sind endlich,
- bei gestörter Weiterleitung wird alarmiert,
- ein Collector darf keine unbegrenzte lokale Queue erzeugen.

## Datenschutz und Secrets

Nie protokolliert werden:

- Passwörter,
- API-Tokens,
- Session-Cookies,
- Authorization-Header,
- private Schlüssel,
- vollständige Webhook-Signaturen,
- Kundendaten ohne technischen Bedarf,
- vollständige Druck-/Produktionsdateien.

Production-Debuglogging ist standardmäßig deaktiviert.

Redaction erfolgt vor dem Schreiben in stdout/stderr, nicht erst im zentralen Logsystem.

## Dateisystemschutz und Alarmierung

Zusätzlich zu den harten Größenlimits wird Hostspeicher überwacht.

Standard:

```text
warning: 75 %
critical: 85 %
```

Bei ungewöhnlich hoher Lograte müssen sowohl der verursachende Service als auch die verbleibende Dateisystemkapazität sichtbar sein.

Die Logrotation ersetzt nicht das separate Docker-Retention-/Image-Cleanup aus #231.

## Service-Template

Jeder gerenderte Service erhält eine `logging/policy.yaml` mit:

- stdout/stderr als Quelle,
- Plattform-Driver `local`,
- lokalen Rotationsgrenzen,
- zentraler Retention-Klasse,
- Redaction-Regeln,
- Hinweis auf den verbotenen servicebezogenen Driver-Override.

## Bestehende Container

Änderungen an Docker-Daemon-Logging-Defaults gelten nur für neu erstellte Container.

Nach einer Änderung der globalen Logging-Policy werden bestehende Container kontrolliert neu erstellt, damit sie die neuen Driver-/Optionswerte übernehmen.

## Tests

Die CI prüft:

1. Policy und Docker-Daemon-Template verwenden dieselben Werte.
2. Compose-Services dürfen die Plattform-Logging-Konfiguration nicht überschreiben.
3. Das Service-Template enthält die erwarteten Logging-Regeln.
4. Ein kurzlebiger Testcontainer erzeugt mehr Logs als die konfigurierte Testrotation halten darf.
5. Die neuesten Logs bleiben über `docker logs` verfügbar.
6. ein früh erzeugter Marker ist nach Rotation nicht mehr vorhanden.
7. Docker meldet den `local`-Driver mit begrenztem `max-size` und `max-file`.

## Referenzen

- `configuration/logging-policy.json`
- `docs/08-monitoring.md`
- `docs/27-logging-standards.md`
- `docs/43-docker-runtime.md`
- `docs/48-docker-compose-standards.md`
- `docs/53-standard-service-template.md`
