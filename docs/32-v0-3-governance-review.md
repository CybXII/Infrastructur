# v0.3 Governance Review und Abschluss

## Zweck

Dieses Dokument fasst die abschließende Prüfung der GitHub-Governance und der Standards für Version `v0.3` zusammen.

Es konkretisiert Issue #50 und dient als Entscheidungsgrundlage für den Abschluss von Epic #23 sowie den Start von `v0.4`.

## Prüfungsumfang

Geprüft wurden:

- Branch- und Promotion-Modell
- Pull-Request- und Commit-Konventionen
- Governance- und Repository-Workflows
- Branch Protection und Merge-Governance
- Issue-, Label- und Projektregeln
- Release- und Tagging-Konventionen
- technische und organisatorische Standards aus Epic #35
- Dokumentations-, Logging-, Konfigurations- und Fehlerbehandlungsstandards

## Verifizierter Integrationsstand

Die Pull Requests #203 bis #208 wurden nach `development` gemergt.

Damit sind insbesondere folgende Standards gemeinsam im Integrationsstand vorhanden:

- Versions- und Releasekonventionen
- Logging-Standards
- Konfigurationsstandards
- Fehlerbehandlungsstandards
- Dokumentationsstandards
- Standards- und Konventionsreview

Die Umsetzung erfolgte weiterhin über den verbindlichen Flow:

```text
Arbeitsbranch -> development -> staging -> main
```

Der Merge nach `development` bedeutet noch keine produktive Freigabe und keinen Release-Abschluss.

## Governance-Checks

Für den Head-Commit von PR #208 wurden die GitHub-Actions-Workflows geprüft.

Ergebnis:

| Workflow | Status | Ergebnis |
|---|---|---|
| `Repository Tests` | completed | success |
| `Governance Checks` | completed | success |

Damit ist für diesen repräsentativen PR bestätigt, dass die automatische Repository- und Governance-Prüfung erfolgreich ausgeführt wurde.

Der Governance-Workflow prüft insbesondere:

- erlaubte Arbeitsbranch-Namen
- zulässige Zielbranches
- Pull-Request-Titel nach Conventional Commits
- Commit-Betreffzeilen nach dem verbindlichen Format

## Branch- und Merge-Governance

Bestätigt sind:

- Arbeitsbranches werden von `development` erstellt.
- Arbeitsbranches zielen auf `development`.
- Promotion erfolgt über `development -> staging -> main`.
- direkte reguläre Promotion von Arbeitsbranches nach `staging` oder `main` ist nicht vorgesehen.
- Pull Requests werden manuell geprüft und gemergt.
- automatische Veröffentlichung produktiver Releases ist ausgeschlossen.

## Commit- und Pull-Request-Konventionen

Verbindlich sind:

```text
<typ>(optionaler-scope)!: beschreibung
```

Bestätigt wurden:

- definierte Commit-Typen
- optionale technische Scopes
- Breaking-Change-Kennzeichnung über `!`
- zusätzliche Dokumentation über `BREAKING CHANGE:`
- identisches Format für Pull-Request-Titel
- Eignung für nachvollziehbare Squash-Merges

## Release-Governance

Bestätigt sind:

- Semantic Versioning
- produktive Tags im Format `vMAJOR.MINOR.PATCH`
- Release Candidates im Format `vMAJOR.MINOR.PATCH-rc.N`
- produktive Tags ausschließlich auf verifizierten Commits in `main`
- unveränderliche veröffentlichte Tags
- verpflichtende Release Notes
- verpflichtende Known Limitations
- dokumentierte Migration, Verifikation und Rollback
- manuelle finale Versions- und Veröffentlichungsentscheidung

Für den Abschluss von `v0.3` ist weiterhin eine Promotion nach `staging` und `main` erforderlich, bevor ein produktiver Tag gesetzt werden darf.

## Standards und Konventionen

Die Standards aus Epic #35 decken folgende Bereiche ab:

| Bereich | Standard |
|---|---|
| Server | Hostnamen nach Umgebung, Standort, Rolle und Nummer |
| Container | Compose-Projekte, Services und Container |
| Netzwerk | Docker-Netzwerke, Zonen, VLANs, Subnetze und interne DNS-Zonen |
| Volumes | Umgebung, Service, Datenklasse und Backupklasse |
| Dateien | `kebab-case`, Endungen, Standarddateien und Ausnahmen |
| Umgebungen | Development, Test, Staging, Production, Management und Lab |
| Commits | Conventional Commits |
| Releases | Semantic Versioning, Tags, Artefakte und Kompatibilität |
| Logging | strukturierte Ereignisse, UTC, Level, Korrelation und Redaction |
| Konfiguration | Formate, Prioritäten, Defaults, Secrets und Validierung |
| Fehlerbehandlung | Fehlerklassen, Exit Codes, Timeouts, Retries und Diagnostik |
| Dokumentation | Dokumenttypen, Mindestinhalte, Mermaid, ADRs und Pflege |

Der gemeinsame Stand ist inhaltlich konsistent ausgerichtet auf:

- explizite Umgebungsgrenzen
- Least Privilege
- keine Secrets im Repository
- kontrollierte Promotion
- diagnostizierbare, aber sichere Betriebsdaten
- dokumentierte Ausnahmen
- manuelle Freigabe kritischer Schritte

## Offene Abweichungen und Restarbeiten

### GitHub-Project-Automationen

Die gewünschten GitHub-Project-Workflows wurden dokumentiert. Ihre tatsächliche Konfiguration in der GitHub-Project-Oberfläche und ein vollständiger Ende-zu-Ende-Test mit einem temporären Test-Issue sind über die derzeit verwendete GitHub-Schnittstelle nicht verifiziert.

Vor dem endgültigen Abschluss von Epic #23 ist manuell zu bestätigen:

- neue Issues landen im vorgesehenen Projektstatus
- Statusänderungen greifen wie dokumentiert
- geschlossene Issues werden korrekt einsortiert
- ein temporäres Test-Issue durchläuft den vollständigen Workflow
- das Test-Issue wird anschließend entfernt oder geschlossen

### Branch Protection

Die Regeln sind dokumentiert. Vor produktiver Freigabe ist in der GitHub-Oberfläche zu bestätigen, dass die aktuell aktiven Branch-Protection- oder Ruleset-Einstellungen mit der Dokumentation übereinstimmen.

Mindestens zu prüfen:

- Pull-Request-Pflicht
- erforderliche Statuschecks
- Schutz vor Force Push
- Schutz vor Branch-Löschung
- Regeln für `development`, `staging` und `main`

### Promotion und Release

Der aktuelle Stand befindet sich in `development`.

Noch offen für einen tatsächlichen `v0.3`-Abschluss:

1. `development` nach `staging` promoten
2. Governance- und Repository-Checks in Staging bestätigen
3. Staging-Smoke-Test dokumentieren
4. Known Limitations finalisieren
5. `staging` nach `main` promoten
6. Merge-Commit in `main` verifizieren
7. Release Notes erstellen
8. Tag und GitHub Release veröffentlichen
9. Release verifizieren

## Abschlusskriterien für Issue #50

Issue #50 kann nach dem Merge dieses Reviews und manueller Bestätigung der UI-gebundenen Prüfungen abgeschlossen werden, wenn:

- Governance-Checks erfolgreich sind
- Repository-Tests erfolgreich sind
- Branch Protection geprüft ist
- GitHub-Project-Automationen geprüft sind
- offene Abweichungen dokumentiert sind
- ein klarer Promotion- und Releasepfad besteht
- Epic #23 keine weitere offene Pflichtaufgabe enthält

## Entscheidung für v0.4

`v0.4` kann fachlich vorbereitet werden, sobald der `v0.3`-Stand eingefroren und der Release-Scope festgelegt ist.

Neue `v0.4`-Arbeiten beginnen weiterhin auf Arbeitsbranches von `development` und dürfen den Abschluss- oder Release-Stand von `v0.3` nicht unkontrolliert verändern.

Empfohlen ist, vor Beginn größerer `v0.4`-Änderungen entweder:

- `v0.3` vollständig bis `main` zu promoten und zu veröffentlichen, oder
- einen eindeutig dokumentierten Release-Freeze-Commit festzulegen.

## Definition of Done für Issue #50

- Governance-Regeln wurden gegen den aktuellen Repository-Stand geprüft.
- `Repository Tests` und `Governance Checks` wurden erfolgreich ausgeführt.
- Standards und Konventionen wurden in den Abschluss einbezogen.
- offene UI- und Release-bezogene Abweichungen wurden erfasst.
- Bedingungen für den Abschluss von Epic #23 sind dokumentiert.
- Startbedingungen für `v0.4` sind beschrieben.

## Referenzen

- `docs/15-branch-commit-conventions.md`
- `docs/20-release-tagging-strategy.md`
- `docs/31-standards-review.md`
- `.github/workflows/governance.yml`
- `.github/release.yml`
- Issue #50
- Epic #23
- Epic #35
