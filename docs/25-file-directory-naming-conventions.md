# Verzeichnis- und Dateinamenskonventionen

## Zweck

Dieses Dokument definiert verbindliche Regeln für Verzeichnis-, Datei- und Konfigurationsnamen im Repository und auf verwalteten Hosts.

Ziel ist eine konsistente, plattformübergreifende und maschinenlesbare Struktur für Linux, Windows, Docker, GitHub Actions, Ansible und Dokumentation.

## Grundregeln

Für neue Verzeichnis- und Dateinamen gilt grundsätzlich:

- Kleinbuchstaben `a-z`
- Ziffern `0-9`
- Bindestriche zur Worttrennung
- keine Leerzeichen
- keine Umlaute oder Sonderzeichen
- keine personenbezogenen oder kundenspezifischen Namen
- keine Begriffe wie `new`, `old`, `final`, `final2` oder `copy`
- keine Versionsnummer im dauerhaften Namen, sofern die Version nicht fachlich erforderlich ist
- Namen beschreiben Zweck oder Inhalt, nicht den Bearbeiter

Bevorzugt:

```text
backup-policy.md
server-bootstrap.sh
shopify-order-import/
```

Nicht zulässig:

```text
Backup Policy.md
alex-script.sh
neuer-ordner/
final_v2.yaml
```

## Verzeichnisnamen

Verzeichnisse verwenden `kebab-case`:

```text
server-bootstrap/
compose-templates/
monitoring-rules/
shopify-integrations/
```

Verzeichnisnamen sind:

- kurz, aber eindeutig
- plural, wenn sie eine Sammlung enthalten
- singular, wenn sie genau einen fachlichen Bereich darstellen
- stabil gegenüber technischen Versionswechseln

Beispiele:

```text
services/
scripts/
docs/
ansible/
monitoring/
backup/
```

## Dateinamen

Allgemeine Dateien verwenden ebenfalls `kebab-case`:

```text
server-layout.md
restore-procedure.md
validate-compose.py
backup-database.sh
```

Dateinamen enthalten keine Datumsangabe, sofern die Datei fortlaufend gepflegt wird.

Nicht bevorzugt:

```text
backup-plan-2026-07-27.md
```

Bevorzugt:

```text
backup-plan.md
```

Datumsangaben sind zulässig für unveränderliche Protokolle, Exporte und Snapshots:

```text
restore-test-2026-07-27.md
inventory-export-2026-07-27.json
```

Datumsformat:

```text
YYYY-MM-DD
```

## Erweiterungen und Dateiendungen

Dateiendungen werden klein geschrieben.

Verbindliche Beispiele:

```text
.md
.yaml
.yml
.json
.toml
.ini
.env.example
.sh
.py
.sql
.txt
.csv
```

Für neue YAML-Dateien wird bevorzugt `.yaml` verwendet. Bestehende etablierte Dateien wie GitHub-Workflows dürfen `.yml` behalten.

Skripte erhalten immer eine zur Laufzeit passende Endung:

```text
bootstrap-server.sh
validate-config.py
```

Ausführbare Dateien ohne Endung sind nur zulässig, wenn dies durch das jeweilige Ökosystem üblich oder technisch erforderlich ist.

## Konfigurationsdateien

Konfigurationsdateien verwenden einen klaren Zweck im Namen:

```text
traefik-static.yaml
traefik-dynamic.yaml
prometheus-config.yaml
alertmanager-config.yaml
```

Umgebungsspezifische Konfigurationen verwenden die festgelegten Kennungen:

```text
config-dev.yaml
config-stg.yaml
config-prd.yaml
```

Secrets werden nicht durch Dateinamen verschleiert und niemals in Git gespeichert.

Erlaubt:

```text
.env.example
secrets.example.yaml
```

Nicht zulässig:

```text
.env
production-secrets.yaml
ssh-private-key
```

## Standarddateien

Ökosystembedingte Standardnamen behalten ihre etablierte Schreibweise:

```text
README.md
LICENSE
CODEOWNERS
Dockerfile
Makefile
compose.yaml
```

Diese Ausnahmen werden nicht in Kleinbuchstaben umbenannt.

## Repository-Struktur

Empfohlene oberste Struktur:

```text
.github/
ansible/
compose/
docs/
scripts/
services/
tests/
```

Unterverzeichnisse orientieren sich an technischer Verantwortung oder Service:

```text
services/n8n/
services/traefik/
services/postgres/
monitoring/prometheus/
monitoring/grafana/
```

## Plattformübergreifende Kompatibilität

Namen dürfen sich nicht nur durch Groß- und Kleinschreibung unterscheiden.

Nicht zulässig:

```text
Config.yaml
config.yaml
```

Weitere Regeln:

- keine reservierten Windows-Namen wie `CON`, `PRN`, `AUX`, `NUL`, `COM1` oder `LPT1`
- kein Punkt oder Leerzeichen am Ende eines Namens
- Pfade bleiben möglichst kurz
- keine Backslashes in Repository-Pfaden
- relative Referenzen verwenden `/`
- symbolische Links nur mit dokumentierter Notwendigkeit

## Nummerierte Dokumente

Bestehende nummerierte Dokumente unter `docs/` verwenden:

```text
NN-thema.md
```

Beispiele:

```text
21-server-naming-conventions.md
22-container-naming-conventions.md
23-network-naming-conventions.md
24-volume-naming-conventions.md
```

Regeln:

- zweistellige fortlaufende Nummer
- Bindestrich nach der Nummer
- sprechender englischer Dateiname
- bestehende Nummern werden nicht neu vergeben
- Umbenennungen berücksichtigen alle Verweise

## Temporäre Dateien

Temporäre Dateien gehören nicht dauerhaft ins Repository.

Typische Muster für `.gitignore`:

```text
*.tmp
*.bak
*.swp
.DS_Store
Thumbs.db
```

Temporäre Arbeitsdateien auf Hosts liegen in dafür vorgesehenen Verzeichnissen und nicht zwischen Konfigurationen oder persistenten Daten.

## Verbotene Muster

Nicht zulässig sind insbesondere:

```text
Neuer Ordner/
script final.sh
config_old.yaml
config-new.yaml
alex-test.py
kunde-a-config.yaml
backup(1).zip
Dokumentation.md
```

Gründe:

- Leerzeichen oder Sonderzeichen
- vergängliche Statusbegriffe
- Personen- oder Kundenbezug
- inkonsistente Großschreibung
- unklare fachliche Bedeutung

## Umbenennung bestehender Dateien

Vor einer Umbenennung sind mindestens zu prüfen:

1. interne Markdown-Links
2. Workflow- und Skriptreferenzen
3. Compose- und Ansible-Pfade
4. CI-Prüfungen
5. Dokumentationsverweise
6. Deployment- und Backup-Skripte
7. Groß-/Kleinschreibungsprobleme auf verschiedenen Dateisystemen

Reine Änderungen der Großschreibung werden unter Git in zwei Schritten durchgeführt, wenn das lokale Dateisystem Groß- und Kleinschreibung nicht unterscheidet.

## Validierung

Allgemeine neue Namen entsprechen grundsätzlich:

```regex
^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+(?:\.[a-z0-9]+)*)?$
```

Nummerierte Dokumente entsprechen:

```regex
^[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$
```

Ökosystembedingte Standarddateien werden über eine Ausnahmeliste geprüft.

## Ausnahmen

Abweichungen sind zulässig, wenn ein etabliertes Werkzeug oder Format einen festen Dateinamen verlangt.

Beispiele:

```text
Dockerfile
CODEOWNERS
README.md
Makefile
```

Andere Ausnahmen benötigen:

- technische Begründung
- betroffenen Pfad
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #41

- Schreibweise und Trennzeichen sind verbindlich geregelt.
- Dateiendungen und Konfigurationsnamen sind dokumentiert.
- plattformübergreifende Kompatibilität ist berücksichtigt.
- gültige und verbotene Beispiele sind vorhanden.
- Standarddateien und Ausnahmeprozess sind definiert.

## Referenzen

- `docs/03-server-layout.md`
- `docs/21-server-naming-conventions.md`
- `docs/22-container-naming-conventions.md`
- `docs/23-network-naming-conventions.md`
- `docs/24-volume-naming-conventions.md`
- Issue #41
- Epic #35
