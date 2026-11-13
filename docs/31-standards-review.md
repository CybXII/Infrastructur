# Standards- und Konventionen-Review

## Zweck

Dieses Dokument prüft die im Epic #35 zusammengeführten technischen und organisatorischen Standards auf Konsistenz, Umsetzbarkeit, Vollständigkeit und kontrollierte Ausnahmen.

## Prüfbereich

Geprüft wurden die Standards für:

- Servernamen
- Container-, Compose- und Servicenamen
- Netzwerk-, VLAN-, Subnetz- und Zonennamen
- Volume- und Datenklassen
- Verzeichnis- und Dateinamen
- Umgebungen und Hostgruppen
- Conventional Commits
- Versions- und Releasekonventionen
- Logging
- Konfiguration
- Fehlerbehandlung
- Dokumentation

Die Standards aus Issues #45 bis #48 liegen zum Zeitpunkt dieses Review-PRs in getrennten Pull Requests vor. Der Abschluss von Issue #49 und Epic #35 setzt deren Merge sowie eine abschließende Prüfung des gemeinsamen `development`-Stands voraus.

## Bewertungsmethode

Jeder Bereich wurde gegen folgende Kriterien geprüft:

1. eindeutiger Zweck und Geltungsbereich
2. konsistente Terminologie
3. maschinenlesbare und technisch umsetzbare Regeln
4. gültige und ungültige Beispiele
5. geregelte Ausnahmen
6. Sicherheits- und Datenschutzverträglichkeit
7. Promotion-, Test- und Rollbackfähigkeit
8. Querverweise zu angrenzenden Standards

## Konsistenzmatrix

| Bereich | Verbindliches Kernelement | Ergebnis |
|---|---|---|
| Umgebungen | `dev`, `test`, `stg`, `prd`, `mgmt`, `lab` | konsistent |
| Promotion | `development -> staging -> main` | konsistent |
| Server | `<umgebung>-<standort>-<rolle>-<nummer>` | konsistent |
| Container | Compose-Projekt, Service und Instanz getrennt | konsistent |
| Netzwerk | Umgebung, Sicherheitszone und Zweck | konsistent |
| Volumes | Umgebung, Service, Datenklasse und Backupklasse | konsistent |
| Dateien | `kebab-case`, definierte Ökosystem-Ausnahmen | konsistent |
| Variablen | `snake_case`; Environment-Variablen `UPPER_SNAKE_CASE` | konsistent |
| Commits | Conventional Commits | konsistent |
| Releases | Semantic Versioning und unveränderliche Tags | konsistent |
| Logging | strukturierte Ereignisse, UTC und Korrelation | nach Merge #45 bestätigt |
| Konfiguration | sichere Defaults, Prioritäten und Validierung | nach Merge #46 bestätigt |
| Fehler | Klassen, Exit Codes, Timeout und Retry | nach Merge #47 bestätigt |
| Dokumentation | Dokumenttypen, Mermaid, ADR und Pflege | nach Merge #48 bestätigt |

## Terminologie

### Umgebungskennungen

Die Standards verwenden einheitlich:

```text
dev
test
stg
prd
mgmt
lab
```

`test` ist eine isolierte Funktions- oder Recovery-Umgebung und kein regulärer Promotion-Branch. Der reguläre Git-Flow bleibt:

```text
Arbeitsbranch -> development -> staging -> main
```

### Schreibweisen

| Kontext | Schreibweise |
|---|---|
| Dateien, Verzeichnisse, Hosts, Container, Netzwerke, Volumes | `kebab-case` |
| YAML-, JSON- und Ansible-Variablen | `snake_case` |
| Environment-Variablen und Repository-Secrets | `UPPER_SNAKE_CASE` |
| Log-Ereignisnamen | `snake_case` |
| Git-Tags | `vMAJOR.MINOR.PATCH` |

Die unterschiedlichen Schreibweisen sind technisch begründet und nicht widersprüchlich.

## Sicherheitsprüfung

Die Standards sind in folgenden Punkten konsistent:

- Secrets werden nicht im Repository gespeichert.
- Production verwendet getrennte Secrets, Benutzer und Schlüssel.
- Logs schließen Tokens, Passwörter und unnötige personenbezogene Daten aus.
- Konfigurationsfehler geben keine Secret-Werte aus.
- Test- und Lab-Umgebungen erhalten keinen direkten Zugriff auf produktive Daten.
- Daten-, Management- und Public-Netzwerke werden getrennt.
- Backup-Relevanz ist bei Volumes explizit.
- Breaking Changes benötigen Migration und Rollback.

## Betriebsprüfung

Die Standards unterstützen einen reproduzierbaren Betrieb durch:

- stabile Namen und Rollen
- explizite Umgebungsgrenzen
- nachvollziehbare Konfigurationsvererbung
- zentrale Logging- und Korrelationsregeln
- kontrollierte Exit-, Timeout- und Retry-Semantik
- manuelle, verifizierte Releases
- unveränderliche Tags
- dokumentierte Restore-, Migrations- und Rollbackanforderungen

## Beispiele und Ausnahmen

Alle Standardbereiche enthalten oder verlangen:

- gültige Beispiele
- verbotene beziehungsweise nicht bevorzugte Beispiele
- technische Begründungen
- dokumentierte Ausnahmebedingungen
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Issue- oder ADR-Referenz

Ausnahmen dürfen den Sicherheits- oder Promotion-Prozess nicht still umgehen.

## Festgestellte Abgrenzungen

### Hostname und Ansible-Gruppe

Hostnamen verwenden Bindestriche. Ansible-Gruppen dürfen Unterstriche verwenden, weil dies im Inventarkontext technisch üblich ist. Diese Abweichung ist ausdrücklich dokumentiert.

### Containername und Docker-DNS

Vollständige Containeridentitäten folgen dem Namensstandard. Interne Docker-DNS-Auflösung verwendet den kurzen Compose-Service-Namen. Beide Namen erfüllen unterschiedliche Aufgaben.

### Volume-Backupklasse und Wichtigkeit

`bkp`, `nobkp` und `external` beschreiben die Sicherungsmethode, nicht die fachliche Wichtigkeit. Ein Datenbankvolume kann `external` tragen, wenn konsistente Dumps oder WAL-Sicherung dokumentiert sind.

### Conventional Commits und Versionierung

Commit-Typen liefern ein Versionssignal, bestimmen die Release-Version aber nicht automatisch. Die verantwortliche Freigabe prüft die tatsächliche Kompatibilitätswirkung.

## Offene Merge-Abhängigkeiten

Vor Abschluss des Reviews müssen folgende separaten PRs nach `development` gemergt sein:

- Issue #45: Logging-Standards
- Issue #46: Konfigurationsstandards
- Issue #47: Fehlerbehandlungsstandards
- Issue #48: Dokumentationsstandards

Danach ist der gemeinsame Stand auf gebrochene Links, doppelte Nummern, widersprüchliche Begriffe und fehlende Referenzen zu prüfen.

## Abschlusscheckliste

- [ ] PR zu Issue #45 gemergt
- [ ] PR zu Issue #46 gemergt
- [ ] PR zu Issue #47 gemergt
- [ ] PR zu Issue #48 gemergt
- [ ] Review-PR auf aktuellen `development`-Stand aktualisiert
- [ ] interne Markdown-Referenzen geprüft
- [ ] Dokumentnummern eindeutig
- [ ] Umgebungskennungen konsistent
- [ ] Schreibweisen konsistent
- [ ] Beispiele frei von Secrets und Produktivdaten
- [ ] Ausnahmen vollständig beschrieben
- [ ] Epic #35 gegen alle Definitionen of Done geprüft

## Ergebnis

Der bisherige Standardrahmen ist konzeptionell konsistent und umsetzbar. Es wurden keine grundlegenden Widersprüche zwischen Naming, Umgebungen, Governance, Releases, Sicherheit und Betrieb festgestellt.

Issue #49 und Epic #35 dürfen jedoch erst geschlossen werden, nachdem die PRs zu Issues #45 bis #48 gemergt und die Abschlusscheckliste auf dem gemeinsamen `development`-Stand bestätigt wurde.

## Definition of Done für Issue #49

- alle Standards sind auf dem gemeinsamen Branchstand vorhanden
- Querverweise und Dokumentnummern sind geprüft
- Terminologie und Schreibweisen sind widerspruchsfrei
- Beispiele und Ausnahmen sind vollständig
- keine offene sicherheitskritische Inkonsistenz besteht
- Epic #35 kann nach dokumentierter Abschlussprüfung geschlossen werden

## Referenzen

- `docs/21-server-naming-conventions.md`
- `docs/22-container-naming-conventions.md`
- `docs/23-network-naming-conventions.md`
- `docs/24-volume-naming-conventions.md`
- `docs/25-file-directory-naming-conventions.md`
- `docs/26-environments-host-groups.md`
- `docs/15-branch-commit-conventions.md`
- `docs/20-release-tagging-strategy.md`
- Issues #45, #46, #47, #48 und #49
- Epic #35
