# Versions- und Releasekonventionen

## Zweck

Dieses Dokument definiert die verbindlichen Regeln für Versionen, Tags, Pre-Releases, Release-Artefakte, Release Notes und Kompatibilität im Repository `Merchfactory/Infrastructure`.

Es konkretisiert Issue #44 und führt die mit Issue #34 eingeführte Release- und Tagging-Strategie fort.

## Semantic Versioning

Versionen folgen Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

Bedeutung:

- `MAJOR`: nicht rückwärtskompatible Änderung am Betriebs-, Deployment-, Konfigurations- oder Schnittstellenmodell
- `MINOR`: neue rückwärtskompatible Funktion, neuer Service oder neue Infrastruktur-Fähigkeit
- `PATCH`: kompatible Fehlerbehebung, Wartung, Hardening oder Dokumentationskorrektur

Beispiele:

```text
0.3.0
0.3.1
1.0.0
```

Bis zum ersten stabilen produktiven Stand bleibt die Hauptversion `0`. Größere Änderungen innerhalb von `0.x` müssen in den Release Notes ausdrücklich als potenziell inkompatibel gekennzeichnet werden.

## Auswahl der nächsten Version

### PATCH

PATCH wird erhöht bei:

- kompatiblen Fehlerbehebungen
- Security-Hardening ohne notwendige Migration
- Dokumentationskorrekturen
- kompatiblen Abhängigkeitsupdates
- Korrekturen an bestehenden Workflows

```text
v0.3.0 -> v0.3.1
```

### MINOR

MINOR wird erhöht bei:

- neuen Deployment- oder Backup-Funktionen
- neuen Services
- neuen rückwärtskompatiblen Konfigurationsoptionen
- neuen Governance- oder Monitoring-Funktionen

```text
v0.3.1 -> v0.4.0
```

### MAJOR

MAJOR wird erhöht bei:

- inkompatiblen Änderungen an Server-, Netzwerk- oder Deployment-Modellen
- Entfernung bisher zugesicherter Konfigurationsschlüssel oder Schnittstellen
- verpflichtenden Migrationen, die bestehende Installationen ohne Anpassung brechen
- grundlegenden Änderungen am Sicherheits- oder Betriebsmodell

```text
v1.4.2 -> v2.0.0
```

## Zusammenhang mit Conventional Commits

Commit- und Pull-Request-Titel folgen den Conventional-Commits-Regeln aus `docs/15-branch-commit-conventions.md`.

Grundsätzliche Zuordnung:

| Conventional-Commit-Typ | Standardmäßige Versionswirkung |
|---|---|
| `fix` | PATCH |
| `security` | PATCH, bei Inkompatibilität MAJOR |
| `feat` | MINOR |
| `feat!` oder `BREAKING CHANGE:` | MAJOR |
| `docs`, `chore`, `test`, `ci`, `build`, `refactor` | keine automatische Erhöhung; Wirkung wird fachlich bewertet |

Die finale Versionsentscheidung bleibt bewusst manuell. Ein Commit-Typ allein ersetzt keine Prüfung der tatsächlichen Kompatibilitätswirkung.

## Tagformat

Produktive Git-Tags verwenden:

```text
vMAJOR.MINOR.PATCH
```

Beispiele:

```text
v0.3.0
v0.3.1
v1.0.0
```

Regeln:

- Tags werden ausschließlich auf verifizierten Commits in `main` gesetzt.
- Tags werden nicht auf `development`, `staging` oder Arbeitsbranches erstellt.
- Produktive Tags sind annotiert.
- Veröffentlichte Tags sind unveränderlich.
- Ein fehlerhafter Release wird durch einen neuen PATCH-Release korrigiert.
- Ein Tag darf nicht gelöscht oder verschoben werden, um einen veröffentlichten Stand unbemerkt zu ersetzen.

## Pre-Releases

Release Candidates verwenden:

```text
vMAJOR.MINOR.PATCH-rc.N
```

Beispiele:

```text
v0.4.0-rc.1
v0.4.0-rc.2
v1.0.0-rc.1
```

Regeln:

- `N` beginnt bei `1` und wird für jede neue Kandidatenversion erhöht.
- Release Candidates werden in GitHub als Pre-Release markiert.
- Sie gelten nicht als produktiv freigegeben.
- Sie basieren auf einem eindeutig dokumentierten und geprüften Commit.
- Der produktive Tag wird erst nach erfolgreicher Abnahme erstellt.
- Für normale interne Zwischenstände werden keine Pre-Release-Tags benötigt.

Andere Kennzeichnungen wie `alpha`, `beta`, Datumszusätze oder persönliche Suffixe werden nicht verwendet, solange dieser Standard nicht ausdrücklich erweitert wird.

## Promotion- und Release-Flow

Der verbindliche Flow lautet:

```text
Arbeitsbranch -> development -> staging -> main
```

Release-Ablauf:

1. Release-Scope und Zielversion festlegen.
2. Zugehörige Änderungen in `development` integrieren.
3. `development` nach `staging` promoten.
4. Staging-Validierung und Smoke Tests durchführen.
5. Migrationen und Known Limitations dokumentieren.
6. `staging` nach `main` promoten.
7. Exakten Merge-Commit in `main` verifizieren.
8. Annotierten Tag erstellen.
9. GitHub Release aus diesem Tag veröffentlichen.
10. Release und gegebenenfalls Deployment verifizieren.
11. Zugehörige Issues erst danach auf `status: done` setzen und schließen.

Der Release wird nicht automatisch veröffentlicht. Tagging und Veröffentlichung bleiben bewusste manuelle Freigabeschritte.

## Kompatibilitätsregeln

### Rückwärtskompatibel

Eine Änderung ist rückwärtskompatibel, wenn bestehende Installationen ohne verpflichtende Anpassung weiter funktionieren.

Beispiele:

- neuer optionaler Konfigurationswert mit sicherem Standard
- neuer Service ohne Änderung bestehender Services
- zusätzlicher Monitoring-Exporter
- neue Dokumentation oder Prüfungen

### Nicht rückwärtskompatibel

Eine Änderung ist nicht rückwärtskompatibel, wenn mindestens einer der folgenden Fälle eintritt:

- bestehende Konfigurationsschlüssel werden entfernt oder umbenannt
- Verzeichnis-, Volume-, Netzwerk- oder Hostnamen müssen zwingend migriert werden
- bestehende Deployment-Befehle funktionieren nicht mehr
- ein bisher vorhandener Service oder Endpoint entfällt
- Rollen, Berechtigungen oder Secrets müssen verpflichtend geändert werden
- ein Restore mit dem bisherigen Verfahren ist nicht mehr möglich

Breaking Changes benötigen:

- `!` im Commit- oder PR-Titel
- einen `BREAKING CHANGE:`-Hinweis
- eine MAJOR-Version ab `1.0.0`
- dokumentierte Migration
- dokumentiertes Rollback
- Liste betroffener Systeme

Während `0.x` wird mindestens MINOR erhöht und die Inkompatibilität deutlich hervorgehoben.

## Unterstützte Upgrade-Pfade

Unterstützt wird grundsätzlich das Upgrade vom unmittelbar vorherigen stabilen Release auf den neuen Release.

Beispiel:

```text
v0.4.2 -> v0.5.0
```

Sprünge über mehrere Versionen sind nur unterstützt, wenn die Release Notes dies ausdrücklich bestätigen.

Downgrades gelten nicht automatisch als unterstützt. Ein Rollback erfolgt über den dokumentierten vorherigen stabilen Stand und dessen Restore- oder Deployment-Verfahren.

## Release-Artefakte

Ein Release besteht mindestens aus:

- annotiertem Git-Tag
- GitHub Release
- Release Notes
- Referenz auf den freigegebenen Commit-SHA
- Prüfergebnissen
- Known Limitations
- Migrationshinweisen
- Rollback-Ziel

Optionale technische Artefakte sind:

- geprüfte Konfigurationspakete
- Compose-Konfigurationen
- Ansible-Pakete oder Collections
- Prüfsummen
- Software Bill of Materials
- signierte Container-Images

Für optionale Artefakte gelten:

- reproduzierbare Zuordnung zur Release-Version
- keine Secrets oder produktiven Daten
- dokumentierte Herkunft
- Prüfsumme oder Signatur, sobald Artefakte außerhalb von GitHub/Git verteilt werden
- eindeutige Dateinamen mit Version

Beispiele:

```text
merchfactory-infrastructure-v0.5.0.tar.gz
merchfactory-infrastructure-v0.5.0.sha256
```

Quellcode-Archive, die GitHub automatisch erzeugt, ersetzen keine betrieblich benötigten Backup- oder Deployment-Artefakte.

## Release Notes

Jeder Release enthält mindestens:

```markdown
## Zusammenfassung

## Änderungen

### Security

### Deployment und Betrieb

### Dokumentation und Governance

### Abhängigkeiten

## Kompatibilität

## Migration oder manuelle Schritte

## Known Limitations

## Verifikation

## Rollback
```

### Änderungen

Relevante Pull Requests und Issues werden referenziert. `.github/release.yml` unterstützt die automatische Kategorisierung generierter Release Notes.

### Kompatibilität

Dieser Abschnitt nennt:

- kompatible Ausgangsversion
- Breaking Changes
- geänderte Voraussetzungen
- betroffene Hosts, Services oder Umgebungen

### Migration oder manuelle Schritte

Beispiele:

- Repository-Secrets anlegen oder ändern
- Serverkonfiguration aktualisieren
- Verzeichnisse oder Berechtigungen vorbereiten
- Volume- oder Datenmigration durchführen
- bestehende Deployments anpassen

Ist keine manuelle Aktion erforderlich, wird ausdrücklich `Keine` eingetragen.

### Known Limitations

Jede bekannte Einschränkung nennt möglichst:

- betroffenen Bereich
- praktische Auswirkung
- Workaround
- zugehöriges Issue
- geplanten Lösungsstand

Ohne bekannte Einschränkungen:

```text
Keine bekannten Einschränkungen zum Veröffentlichungszeitpunkt.
```

### Verifikation

Mindestens dokumentiert werden:

- Commit-SHA
- ausgeführte Checks
- Staging-Ergebnis
- Release- oder Deployment-Verifikation

### Rollback

Der Release nennt:

- vorherigen stabilen Tag
- benötigte Backup- oder Restore-Punkte
- technische Rollback-Schritte
- erwartete Datenwirkung

## Tag-Erstellung

Nach Freigabe des Commits in `main`:

```bash
git checkout main
git pull --ff-only origin main
git tag -a v0.5.0 -m "Release v0.5.0"
git push origin v0.5.0
```

Vor dem Push:

```bash
git show --no-patch --decorate v0.5.0
git rev-parse main
git rev-list -n 1 v0.5.0
```

Der Commit des Tags und der freigegebene Commit in `main` müssen identisch sein.

## Fehlerhafter Release

Ein veröffentlichter Release wird nicht nachträglich überschrieben.

Vorgehen:

1. Fehler und Auswirkungen dokumentieren.
2. Bei akutem Risiko Rollback ausführen.
3. Korrektur über den regulären Branch- und PR-Flow umsetzen.
4. Neue PATCH-Version veröffentlichen.
5. In den Release Notes auf den fehlerhaften Vorgänger verweisen.

Beispiel:

```text
v0.5.0 fehlerhaft -> Korrektur als v0.5.1
```

## Release-Verantwortung

`CybXII` bestätigt vor Veröffentlichung:

- Zielversion
- Ziel-Commit
- Kompatibilitätsbewertung
- Release Notes
- Migration
- Known Limitations
- Rollback-Ziel
- Veröffentlichung

Eine spätere Erweiterung um Reviewer ändert nicht den Grundsatz der bewussten manuellen Freigabe.

## Definition of Done für Issue #44

- Semantic Versioning ist verbindlich definiert.
- Pre-Release-Regeln sind dokumentiert.
- Tag- und Releaseformat sind festgelegt.
- Release-Artefakte und deren Mindestanforderungen sind beschrieben.
- Release Notes enthalten Kompatibilität, Migration, Known Limitations, Verifikation und Rollback.
- Breaking Changes und unterstützte Upgrade-Pfade sind geregelt.
- die bestehende Release-Notes-Konfiguration ist eingebunden.

## Referenzen

- `.github/release.yml`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/15-branch-commit-conventions.md`
- `docs/17-github-actions-foundation.md`
- Issue #34
- Issue #44
- Epic #23
- Epic #35
