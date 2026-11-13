# Example Service

## Zweck

Diese Struktur zeigt die minimal erwarteten Bestandteile eines Infrastruktur-Services. Sie ist ausschließlich eine sichere Referenz und keine produktive Konfiguration.

Die Compose-Datei folgt der Baseline aus `docs/48-docker-compose-standards.md`, dem Netzwerkmodell aus `docs/49-docker-network-model.md`, dem Persistenzmodell aus `docs/50-volume-persistence-model.md`, dem Secret-Modell aus `docs/51-secret-management.md` und der Registry-/Image-Security-Strategie aus `docs/52-container-registry-security.md`.

## Struktur

```text
example-service/
  configuration/
    service.yaml.example
    secrets.yaml.example
  deployment/
    compose.yaml.example
  monitoring/
    healthcheck.yaml.example
  backup/
    policy.yaml.example
  tests/
    test-structure.sh
    test-persistence.sh
```

## Compose-Baseline

Die Referenz demonstriert insbesondere:

- eigene Images unter `ghcr.io/merchfactory/...`,
- explizite Registry-/Repositorynamen,
- unveränderliches Image-Pinning per SHA-256-Digest,
- `restart: unless-stopped`,
- read-only Root-Dateisystem,
- `cap_drop: ALL`,
- `no-new-privileges:true`,
- keine direkte Host-Portfreigabe für Anwendungsdienste,
- gemeinsames externes `edge`-Netz für den ingress-fähigen Service,
- internes `app`-Netz für Service-zu-Worker-Kommunikation,
- internes `data`-Netz für Worker-zu-Datenservice-Kommunikation,
- keine Edge-Mitgliedschaft des Datenservice,
- getrennte Liveness-/Readiness-/External-Probe-Semantik,
- explizite CPU-, Memory- und PID-Limits,
- unterschiedliche CPU-Prioritäten für Standard-, Background- und kritische Dienste,
- stdout/stderr-Logging mit hostweit begrenzter Docker-Rotation,
- einen backupfähigen Bind Mount unter `/srv/merchfactory/persistent`,
- ein explizit klassifiziertes Named Volume,
- temporäre Schreibdaten über `tmpfs`,
- dateibasierte Compose-Secrets unter `/run/secrets`,
- keine Secret-Werte in normalen Environment-Variablen.

## Persistenz

Die Referenz verwendet absichtlich beide zulässigen Persistenzformen:

### Application Data

```text
/srv/merchfactory/persistent/example-service/data
        -> /var/lib/example-service
```

Dieser Datensatz ist als dateibasierte Klasse-A-Persistenz gedacht. Vor einem echten Deployment müssen UID, GID und Dateirechte anhand des verwendeten Images festgelegt werden.

### Database Data

`example-database-data` ist ein Named Volume der Klasse A. Seine Labels markieren Backup als verpflichtend und das Verfahren als `application-native`.

Das ist bewusst kein Beispiel für ein Rohkopieren von Datenbankdateien. Ein produktiver Datenbankdienst benötigt einen transaktionskonsistenten Dump bzw. das dafür vorgesehene Datenbankverfahren.

## Secrets

`configuration/secrets.yaml.example` enthält ausschließlich versionierbare Metadaten wie Zweck, Owner-Rolle, Runtime-Ziel, Rotation und Recovery-Anforderung.

Die tatsächlichen Werte liegen außerhalb des Repositorys. Die Compose-Referenz erwartet standardmäßig:

```text
/srv/merchfactory/secrets/example-service/api-token
/srv/merchfactory/secrets/example-service/database-password
```

Im Container werden sie nur den benötigten Diensten als `/run/secrets/api-token` bzw. `/run/secrets/database-password` bereitgestellt.

## Healthchecks

`monitoring/healthcheck.yaml.example` folgt `docs/54-healthcheck-standards.md`:

- Docker-Liveness mit 30s Intervall, 5s Timeout und 3 Retries,
- HTTP-Readiness über Traefik mit 10s Intervall und 3s Timeout,
- externer HTTPS-Probe mit 30s Intervall und 5s Timeout.

Liveness prüft keine optionalen Remote-Abhängigkeiten. Ein `unhealthy`-Container wird nicht automatisch neu gestartet.

## Ressourcen

Die Beispielwerte demonstrieren drei Profile:

- `example-service`: Standardprofil,
- `example-worker`: Background-Priorität mit niedrigerem CPU-Gewicht,
- `example-database`: höher priorisierte Datenkomponente mit größerem Memory-Limit.

Die Werte sind ausschließlich Referenzwerte und kein produktives Datenbank- oder Odoo-Sizing. Das verbindliche Modell steht in `docs/55-container-resource-limits.md`.

## Logging

Der Beispielservice erbt die Plattform-Logging-Policy aus `docs/56-log-rotation.md`: Docker-`local`-Driver, 20 MiB × 5 Segmente, Kompression und kein servicebezogener `logging:`-Override. Die langfristige Aufbewahrung erfolgt zentral nach Logklasse.

## Backup-Policy

`backup/policy.yaml.example` ordnet jedem persistenten Datensatz zu:

- Datenklasse,
- Speicherart,
- Ownership,
- Backup-Verfahren,
- Konsistenzanforderung,
- Restore-Verfahren,
- Restore-Test-Frequenz.

Die Policy enthält keine echten Secrets.

## Automatische Prüfung

Die Repository Tests prüfen:

- die allgemeine Service-Struktur,
- Docker-/Compose-Standards,
- keine anonymen Volumes,
- nur freigegebene beschreibbare Bind-Mount-Pfade,
- Klassifizierung von Named Volumes,
- Vorhandensein einer Backup-Methode für backup-pflichtige Volumes,
- idempotente Vorbereitung eines persistenten Verzeichnisses,
- sichere Installation und Rotation von Secret-Dateien,
- erwartete Compose-Secret-Grants,
- Secret-Scanning im aktuellen Tree und in der Git-Historie,
- Imagequellen gegen die Registry-Allowlist,
- Digest-Pinning und explizite Registrynamen,
- Vulnerability-Scans für tatsächlich ausgeführte Plattformimages,
- vorhandene CPU-, Memory- und PID-Limits,
- Memory-Reservation kleiner als Hard Limit,
- aktiven OOM-Killer.

## Übernahme

Beim Kopieren müssen Servicename, Image-Referenz, Pfade, effektive UID/GID, Healthcheck, Datenklasse, Backup- und Restore-Verfahren fachlich geprüft werden. Platzhalter und Beispielwerte dürfen nicht ungeprüft übernommen werden.

Secrets, Zugangsdaten, private Schlüssel und produktive Zertifikate werden nicht in dieser Struktur abgelegt.
