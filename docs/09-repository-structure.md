# Repository Structure

## Zweck

Dieses Dokument definiert die verbindliche Zielstruktur des Repositorys `Merchfactory/Infrastructure`. Es konkretisiert ADR-0003 und dient als Umsetzungsgrundlage für Milestone v0.2.

Die Struktur ist funktionsorientiert. Sie trennt Bootstrap, Konfiguration, Deployment, Monitoring, Backup, Restore, Hilfswerkzeuge, Tests und Dokumentation. Server- und umgebungsspezifische Unterschiede werden innerhalb der jeweiligen Fachbereiche abgebildet, ohne die Top-Level-Struktur zu duplizieren.

## Zielstruktur

```text
.github/
bootstrap/
configuration/
deployment/
monitoring/
backup/
restore/
scripts/
templates/
tests/
docs/
examples/
```

## Grundregeln

1. Jede Datei besitzt genau einen primären Verantwortungsbereich.
2. Wiederverwendbare Logik wird von umgebungsspezifischen Werten getrennt.
3. Secrets, Tokens, private Schlüssel und produktive Zugangsdaten werden niemals im Repository gespeichert.
4. Generierte Artefakte, Laufzeitdaten, Dumps und temporäre Dateien werden nicht versioniert.
5. Jedes Hauptverzeichnis erhält eine `README.md` mit Zweck, Eingaben, Ausgaben, Abhängigkeiten und Verantwortungsgrenzen.
6. Produktionsänderungen müssen reproduzierbar aus versionierten Quellen erzeugt werden können.
7. Gemeinsame Komponenten werden nicht pro Server oder Umgebung kopiert, sondern über Variablen, Inventories, Overlays oder Templates parametrisiert.
8. Neue Top-Level-Verzeichnisse benötigen eine dokumentierte Architekturentscheidung.

## Hauptverzeichnisse

### `.github/`

**Zweck:** GitHub-spezifische Governance und Automatisierung.

Enthält:

- GitHub Actions Workflows
- Issue- und Pull-Request-Templates
- CODEOWNERS
- Dependabot-Konfiguration
- Richtlinien für Releases und Beiträge
- optionale wiederverwendbare Workflow-Komponenten

Nicht enthalten:

- eigentliche Deployment-Skripte
- produktive Konfiguration
- Secrets

Workflows orchestrieren Prüfungen und Deployments, delegieren fachliche Logik aber nach Möglichkeit an versionierte Skripte aus `scripts/`, `deployment/` oder `tests/`.

### `bootstrap/`

**Zweck:** Erstbereitstellung und Grundhärtung neuer Server.

Enthält:

- Betriebssystem-Baseline
- Paketquellen und Basispakete
- Benutzer-, Gruppen- und SSH-Grundkonfiguration
- Firewall-Baseline
- Zeitsynchronisation
- Container-Runtime-Installation
- Vorbereitung von Verzeichnissen und Mountpoints

Bootstrap muss idempotent ausgelegt sein. Anwendungskonfiguration und Service-Deployments gehören nicht hierher.

Empfohlene Unterstruktur:

```text
bootstrap/
  roles/
  inventories/
  playbooks/
  files/
  templates/
```

### `configuration/`

**Zweck:** Deklarative System- und Servicekonfiguration.

Enthält:

- gemeinsame Konfigurationsgrundlagen
- servicebezogene Konfiguration
- umgebungsspezifische Variablen und Overlays
- Host- und Rollenzuordnungen
- Validierungsschemata

Empfohlene Unterstruktur:

```text
configuration/
  common/
  services/
  environments/
    development/
    staging/
    production/
  hosts/
  schemas/
```

`common/` enthält wiederverwendbare Basiswerte. `environments/` enthält ausschließlich Unterschiede zwischen Umgebungen. `hosts/` enthält hostbezogene Zuweisungen, jedoch keine Secrets.

### `deployment/`

**Zweck:** Reproduzierbare Bereitstellung und Aktualisierung von Plattformdiensten.

Enthält:

- Deployment-Manifeste
- Compose-Dateien oder vergleichbare Orchestrierungsdefinitionen
- Release- und Rollback-Logik
- Preflight- und Post-Deployment-Schritte
- Health- und Smoke-Test-Integration
- Migrationsabläufe

Empfohlene Unterstruktur:

```text
deployment/
  stacks/
  services/
  environments/
  migrations/
  rollback/
```

Deployment-Dateien referenzieren unveränderliche Artefakte oder Image-Digests. Secrets werden zur Laufzeit aus dem vorgesehenen Secret-Management bezogen.

### `monitoring/`

**Zweck:** Observability, Logging, Healthchecks und Alarmierung.

Enthält:

- Monitoring-Stack-Konfiguration
- Exporter- und Agent-Konfiguration
- Dashboards
- Alert-Regeln
- Log-Pipelines
- Healthcheck-Definitionen
- SLO- und Kapazitätsabfragen

Empfohlene Unterstruktur:

```text
monitoring/
  metrics/
  logs/
  alerts/
  dashboards/
  healthchecks/
  recording-rules/
```

Betriebsdaten selbst werden nicht versioniert.

### `backup/`

**Zweck:** Erstellung, Verschlüsselung, Übertragung und Prüfung von Backups.

Enthält:

- Backup-Jobs
- Datenbank-Dump-Definitionen
- Volume- und Dateisicherungen
- Retention-Regeln
- Offsite-Transfer
- Integritäts- und Vollständigkeitsprüfungen

Empfohlene Unterstruktur:

```text
backup/
  jobs/
  databases/
  volumes/
  retention/
  verification/
```

Backups und Schlüsselmaterial selbst werden nicht im Repository gespeichert.

### `restore/`

**Zweck:** Wiederherstellung einzelner Datenklassen und vollständiger Systeme.

Enthält:

- Restore-Abläufe
- Disaster-Recovery-Automatisierung
- Wiederanlaufreihenfolgen
- Validierung nach Restore
- Testverfahren für Wiederherstellungen

Empfohlene Unterstruktur:

```text
restore/
  databases/
  volumes/
  services/
  full-rebuild/
  validation/
```

Backup-Erstellung und Restore bleiben getrennt, damit Wiederherstellungslogik unabhängig geprüft werden kann.

### `scripts/`

**Zweck:** Kleine, wiederverwendbare Betriebs- und Entwicklungswerkzeuge.

Enthält:

- Validierungs- und Prüfskripte
- lokale Entwicklungshelfer
- Wartungswerkzeuge
- Wrapper für standardisierte Aufrufe
- Migrations- und Diagnosehilfen

Empfohlene Unterstruktur:

```text
scripts/
  ci/
  maintenance/
  validation/
  migration/
  diagnostics/
```

Skripte müssen Eingaben validieren, sinnvolle Exit-Codes liefern und gefährliche Aktionen standardmäßig verweigern oder explizite Bestätigung verlangen.

### `templates/`

**Zweck:** Wiederverwendbare, nicht direkt ausführbare Vorlagen.

Enthält:

- Konfigurationsvorlagen
- Environment-Beispiele ohne Secrets
- Service-Definitionen
- Runbook- und Dokumentationsvorlagen
- Beispielsystemd-Units oder Compose-Fragmente

Eine Vorlage ist kein produktives Deployment-Artefakt. Produktive Dateien werden daraus reproduzierbar erzeugt.

### `tests/`

**Zweck:** Automatisierte Qualitäts-, Sicherheits- und Wiederherstellungsprüfungen.

Enthält:

- Struktur- und Schema-Tests
- Linting-Konfiguration
- Konfigurationstests
- Deployment- und Smoke-Tests
- Security-Checks
- Backup- und Restore-Tests
- Test-Fixtures ohne reale Geheimnisse oder Kundendaten

Empfohlene Unterstruktur:

```text
tests/
  unit/
  integration/
  smoke/
  security/
  backup/
  restore/
  fixtures/
```

### `docs/`

**Zweck:** Architektur-, Sicherheits-, Betriebs- und Projektdokumentation.

Enthält:

- Vision und Architektur
- ADRs
- Servermodell
- Security-Baseline
- CI/CD- und Deployment-Konzept
- Backup- und Disaster-Recovery-Konzept
- Monitoring-Konzept
- Runbooks und Betriebsanweisungen

Die Dokumentation beschreibt Zielzustand und Betrieb. Ausführbare Konfiguration bleibt in den jeweiligen Fachverzeichnissen.

### `examples/`

**Zweck:** Sichere, vereinfachte Referenzbeispiele.

Enthält:

- Beispielinventories
- anonymisierte Konfigurationen
- Muster-Deployments
- lokale Testbeispiele
- Beispielvariablen mit erkennbaren Platzhaltern

Beispiele dürfen keine produktiven Domains, IP-Adressen, Schlüssel, Kundendaten oder Zugangsinformationen enthalten.

## Gemeinsame und umgebungsspezifische Dateien

### Gemeinsame Dateien

Gemeinsame Dateien enthalten Verhalten, Struktur und Standardwerte, die für alle Umgebungen gelten.

Beispiele:

- gemeinsame Container-Definitionen
- Baseline-Firewall-Regeln
- allgemeine Monitoring-Regeln
- Backup-Logik
- Standard-Healthchecks

### Umgebungsspezifische Dateien

Umgebungsspezifische Dateien enthalten nur notwendige Abweichungen, beispielsweise:

- Hostnamen und Domains
- Replikazahl
- Ressourcenlimits
- Wartungsfenster
- Alarmempfänger
- Aktivierung optionaler Dienste

Umgebungsdateien dürfen keine Secrets enthalten. Sensible Werte werden zur Laufzeit über GitHub Environments oder das vorgesehene Secret-Management eingebunden.

### Prioritätsregel

Die Konfiguration wird logisch in folgender Reihenfolge zusammengesetzt:

```text
common defaults
  -> service defaults
  -> environment overrides
  -> host-specific assignments
  -> runtime secrets
```

Hostbezogene Werte dürfen keine allgemeinen Service- oder Umgebungsregeln duplizieren.

## Mehrere Server und Rollen

Die Verzeichnisstruktur bleibt unabhängig von der Anzahl physischer Server. Serverrollen werden über Inventories, Hostgruppen und Konfigurationszuweisungen zusammengesetzt.

Beispiel:

```text
configuration/hosts/prod-edge-01.yml
configuration/hosts/prod-app-01.yml
configuration/hosts/prod-data-01.yml
configuration/hosts/prod-ops-01.yml
```

Ein Host kann mehrere Rollen tragen. Rollen dürfen keine implizite Abhängigkeit von einem festen Hostnamen besitzen.

## Benennungsregeln

- Verzeichnis- und Dateinamen verwenden `kebab-case`.
- Umgebungen heißen verbindlich `development`, `staging` und `production`.
- Servernamen folgen dem im Servermodell definierten Schema.
- Beispiel- und Template-Dateien tragen einen eindeutigen Suffix wie `.example`, `.template` oder `.sample`.
- Skripte besitzen eine erkennbare Dateiendung und einen passenden Interpreter-Header.
- README-Dateien heißen `README.md`.

## Erweiterungsregeln

Ein neuer Bestandteil wird wie folgt eingeordnet:

1. Fachverantwortung bestimmen.
2. Passendes bestehendes Hauptverzeichnis wählen.
3. Wiederverwendbare Logik und umgebungsspezifische Werte trennen.
4. README und Tests ergänzen.
5. Abhängigkeiten dokumentieren.
6. Nur bei fehlender fachlicher Zuordnung ein neues Top-Level-Verzeichnis über ADR vorschlagen.

## Verbotene Ablagemuster

Nicht zulässig sind:

- generische Sammelverzeichnisse wie `misc/`, `temp/` oder `other/`
- produktive Secrets in `.env`-Dateien
- vollständige Kopien derselben Konfiguration pro Umgebung
- Backups, Datenbank-Dumps oder Laufzeitdaten im Repository
- Deployment-Logik ausschließlich in GitHub Actions ohne versionierte Fachskripte
- serverbezogene Duplikation wiederverwendbarer Rollen
- nicht dokumentierte produktive Hotfix-Dateien

## Mindestinhalt jeder Bereichs-README

Jede `README.md` eines Hauptbereichs dokumentiert mindestens:

- Zweck
- Verantwortungsgrenze
- erwartete Eingaben
- erzeugte Ausgaben
- Abhängigkeiten
- Ausführungs- oder Nutzungsweg
- Testverfahren
- Security- und Secret-Hinweise
- zuständige Rolle

## Umsetzung in v0.2

Milestone v0.2 erstellt die Hauptverzeichnisse und initialen README-Dateien. Leere Verzeichnisse werden nicht durch Platzhalterdateien ohne Aussagekraft erhalten. Stattdessen enthält jedes angelegte Verzeichnis mindestens eine fachlich sinnvolle README oder erste Implementierung.

## Referenzen

- Issue #10
- Epic #2
- `docs/02-adr/ADR-0003-repository-directory-layout.md`
- `docs/03-server-layout.md`
- `docs/04-security.md`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/07-disaster-recovery.md`
- `docs/08-monitoring.md`
