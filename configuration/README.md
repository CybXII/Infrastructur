# Konfiguration

## Zweck

Dieses Verzeichnis enthält deklarative System- und Servicekonfigurationen. Es trennt gemeinsame Basiswerte, servicebezogene Standardwerte, umgebungsspezifische Abweichungen und hostspezifische Zuweisungen.

## Struktur

```text
configuration/
  container-image-policy.json
  healthcheck-policy.json
  resource-policy.json
  logging-policy.json
  deployment-policy.json
  deployment-topologies.json
  docker-cleanup-policy.json
  platform-validation.json
  monitoring-stack.json
  common/
  services/
  environments/
    development/
    staging/
    production/
  hosts/
  schemas/
```

## Verantwortungsbereiche

### `container-image-policy.json`

Definiert plattformweit die zugelassenen First-Party- und Drittanbieter-Imagequellen, Vulnerability-Gates sowie Retention-Grundsätze. Die technische und betriebliche Bedeutung ist in `docs/52-container-registry-security.md` beschrieben.

### `healthcheck-policy.json`

Definiert die plattformweiten Standardwerte für Liveness, Readiness und externe Probes. Die Fehlersemantik und Ausnahmen stehen in `docs/54-healthcheck-standards.md`.

### `resource-policy.json`

Definiert Standardwerte und Prioritätsklassen für CPU, Memory und PIDs. Betriebs- und OOM-Verhalten sind in `docs/55-container-resource-limits.md` beschrieben.

### `logging-policy.json`

Definiert lokale Docker-/journald-Grenzen, zentrale Retention-Klassen und Disk-Alarmgrenzen. Das vollständige Betriebsmodell steht in `docs/56-log-rotation.md`.

### `deployment-policy.json`

Definiert Preflight-, Backup-, Approval- und Rollback-Regeln für Digest-basierte Service-Releases. Das vollständige Verfahren steht in `docs/57-update-rollback.md`.

### `deployment-topologies.json`

Definiert die unterstützten Placement-Profile für Development-only-, 1-, 2- und 3-Host-Betrieb. Environments, Host-Rollen und physische Server werden bewusst getrennt modelliert. Die Architekturentscheidung steht in ADR-0009 und `docs/03-server-layout.md`.

### `docker-cleanup-policy.json`

Definiert Retention, Safety-Gates, Rollback-Schutz und Zeitplan für die automatische Bereinigung von managed Stopped-Containern, Images und Build-Cache. Persistente Volumes sind ausdrücklich ausgeschlossen. Details stehen in `docs/59-docker-retention-cleanup.md`.

### `platform-validation.json`

Ordnet die v0.5-Plattformanforderungen den realen CI-/Integrationstests zu, dokumentiert getestete Fehlerfälle und enthält das maschinenlesbare Release-Gate für den Abschluss von Epic #67 sowie die Übergabe an Epic #83. Details stehen in `docs/58-container-platform-validation.md` und `docs/60-v0.5-review.md`.

### `monitoring-stack.json`

Definiert die verbindlichen v0.6-Komponenten, Baseline-Versionen, Deploymentformen, Ressourcenobergrenzen, Persistenzpfade, Netzwerk- und Security-Verträge sowie die Zuordnung zu Issues #85–#99. Details stehen in ADR-0008 und `docs/61-monitoring-stack.md`.

### `common/`

Enthält gemeinsame Basiswerte und Regeln, die für alle Umgebungen gelten.

Beispiele:

- allgemeine Netzwerk- und Sicherheitsstandards
- gemeinsame Standardwerte
- wiederverwendbare Konfigurationsfragmente

### `services/`

Enthält servicebezogene Standardkonfigurationen. Jeder Dienst erhält einen eigenen Unterbereich, sobald seine technische Umsetzung beginnt.

Servicekonfigurationen dürfen keine umgebungs- oder hostspezifischen Werte duplizieren.

### `environments/`

Enthält ausschließlich notwendige Abweichungen zwischen den Umgebungen:

- `development/`: Entwicklungs- und Integrationsumgebung
- `staging/`: produktionsnahe Prüf- und Freigabeumgebung
- `production/`: produktiv freigegebene Umgebung

Der Git-Branch `main` entspricht fachlich der Umgebung `production`. Die Bezeichnungen werden bewusst nicht gleichgesetzt, da Branch und Laufzeitumgebung unterschiedliche Konzepte sind.

### `hosts/`

Enthält hostspezifische Zuweisungen wie Rollen, aktivierte Dienste oder technische Hostparameter. Allgemeine Service- und Umgebungswerte dürfen hier nicht erneut definiert werden.

### `schemas/`

Enthält maschinenlesbare Schemata und Validierungsregeln für Konfigurationsdateien.

## Vererbung und Priorität

Konfigurationen werden logisch in folgender Reihenfolge zusammengesetzt:

```text
common defaults
  -> service defaults
  -> environment overrides
  -> host-specific assignments
  -> runtime secrets
```

Ein späterer Layer darf nur Werte überschreiben, die auf seiner Ebene tatsächlich abweichen müssen.

## Regeln für Überschreibungen

- Gemeinsame Werte werden in `common/` definiert.
- Dienstspezifische Standardwerte werden in `services/` definiert.
- Unterschiede zwischen Umgebungen werden ausschließlich in `environments/` abgelegt.
- Hostspezifische Werte werden nur in `hosts/` abgelegt.
- Kopierte vollständige Konfigurationsdateien pro Umgebung sind zu vermeiden.
- Überschreibungen müssen klein, nachvollziehbar und dokumentiert bleiben.

## Secrets

Secrets bleiben vollständig außerhalb des Repositories. Dazu gehören insbesondere:

- Passwörter
- API-Tokens
- private Schlüssel
- produktive Zertifikate
- Kundendaten
- Zugangsdaten zu Datenbanken und externen Diensten

Sensible Werte werden erst zur Laufzeit über GitHub Environments oder das später festgelegte Secret-Management eingebunden.

Im Repository dürfen ausschließlich erkennbare Platzhalter oder Referenznamen verwendet werden, zum Beispiel:

```text
DATABASE_PASSWORD_SECRET
SHOPIFY_API_TOKEN_SECRET
```

## Dateibenennung

- Dateien und Verzeichnisse verwenden `kebab-case`.
- Umgebungen heißen verbindlich `development`, `staging` und `production`.
- Beispielwerte tragen einen Suffix wie `.example`, `.sample` oder `.template`.
- Produktive Domains, IP-Adressen und Zugangsinformationen gehören nicht in Beispiele.

## Abgrenzung

- Deployment-Abläufe und Release-Logik gehören nach `deployment/`.
- Bootstrap- und Betriebssystemgrundkonfiguration gehören nach `bootstrap/`.
- Wiederverwendbare Vorlagen ohne direkte Laufzeitwirkung gehören nach `templates/`.
- Ausführbare Validierungslogik gehört nach `scripts/` oder `tests/`.

## Referenzen

- `docs/01-architecture.md`
- `docs/04-security.md`
- `docs/06-deployment.md`
- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`
