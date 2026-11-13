# Branch- und Commit-Konventionen

## Zweck

Dieses Dokument operationalisiert die in `docs/10-development-guidelines.md` festgelegten Regeln für Branches, Pull Requests und Commit-Nachrichten.

## Arbeitsbranches

Kurzlebige Branches werden von `development` erstellt.

Zulässige Präfixe:

- `feature/`
- `fix/`
- `docs/`
- `chore/`
- `refactor/`
- `test/`
- `agent/`

Der restliche Branchname verwendet `kebab-case`.

Beispiele:

```text
feature/server-bootstrap
fix/backup-retention
agent/branch-commit-conventions
```

## Zielbranches

Der reguläre Fluss ist:

```text
Arbeitsbranch -> development -> staging -> main
```

Zusätzlich ist ein reiner Synchronisierungs-Pull-Request von `main` nach `development` zulässig.

Die CI prüft:

- Arbeitsbranches dürfen nur nach `development` zielen.
- Nach `staging` darf regulär nur `development` zielen.
- Nach `main` darf regulär nur `staging` zielen.
- `main -> development` wird ausschließlich als Synchronisierung akzeptiert.

## Verbindliches Commitformat

Commit-Nachrichten folgen Conventional Commits:

```text
<typ>(optionaler-scope)!: beschreibung
```

Der Scope und das Ausrufezeichen sind optional. Die Beschreibung ist verpflichtend.

Beispiele:

```text
feat(governance): Issue-Template ergänzen
fix(backup): leeres Zielverzeichnis ablehnen
docs: Restore-Ablauf beschreiben
ci(actions): Branch-Konventionen prüfen
feat(api)!: veraltete Schnittstelle entfernen
```

## Zulässige Typen

| Typ | Verwendung |
|---|---|
| `feat` | neue rückwärtskompatible Funktion oder Fähigkeit |
| `fix` | Fehlerbehebung |
| `docs` | ausschließlich Dokumentation |
| `chore` | Wartung ohne direkte Produktfunktion |
| `refactor` | interne Umstrukturierung ohne Funktionsänderung |
| `test` | Tests hinzufügen oder ändern |
| `ci` | CI/CD- und GitHub-Actions-Änderungen |
| `build` | Buildsystem, Images oder Abhängigkeiten des Builds |
| `security` | Security-Hardening oder Sicherheitskorrektur |
| `revert` | Rücknahme eines früheren Commits |

Andere Typen sind nicht zulässig, bis dieser Standard ausdrücklich erweitert wurde.

## Scopes

Scopes benennen den primär betroffenen technischen oder organisatorischen Bereich.

Zulässige Scopes sind insbesondere:

```text
governance
architecture
docs
actions
deployment
backup
security
monitoring
logging
network
docker
ansible
traefik
postgres
n8n
shopify
deconetwork
```

Regeln:

- Scopes verwenden ausschließlich Kleinbuchstaben, Ziffern und Bindestriche.
- Mehrteilige Scopes verwenden `kebab-case`.
- Der Scope beschreibt einen stabilen Bereich, kein Ticket und keine Person.
- Der Scope ist optional, aber bei technisch klar abgrenzbaren Änderungen empfohlen.
- Ein Commit verwendet genau einen primären Scope.
- Neue Scopes sind zulässig, wenn sie einen wiederverwendbaren Repository-Bereich eindeutig benennen.

Nicht zulässig:

```text
feat(Alex): Änderung
fix(issue-43): Prüfung korrigieren
chore(misc): Dateien aktualisieren
```

## Beschreibung

Die Beschreibung nach dem Doppelpunkt:

- beginnt mit einem Kleinbuchstaben oder technischen Bezeichner,
- verwendet den Imperativ beziehungsweise beschreibt die konkrete Änderung,
- endet nicht mit einem Punkt,
- bleibt kurz und eindeutig,
- enthält keine alleinstehende Issue-Nummer als Beschreibung.

Bevorzugt:

```text
fix(backup): fehlendes Zielverzeichnis ablehnen
```

Nicht zulässig:

```text
fix: Fixed stuff.
chore: #43
update files
```

## Commit-Body

Ein Body ist optional und wird durch eine Leerzeile vom Betreff getrennt.

Er erklärt insbesondere:

- Motivation und Kontext,
- technische Auswirkungen,
- Migrationsbedarf,
- Risiken oder Einschränkungen,
- bewusst nicht umgesetzte Alternativen.

Der Body wiederholt nicht lediglich den Betreff.

## Breaking Changes

Nicht rückwärtskompatible Änderungen werden mit `!` im Betreff markiert:

```text
feat(api)!: veraltete Schnittstelle entfernen
```

Zusätzlich wird im Commit-Body ein Footer verwendet:

```text
BREAKING CHANGE: Die bisherige API-Route /v1/orders entfällt. Nutzer müssen auf /v2/orders migrieren.
```

Ein Breaking Change muss mindestens dokumentieren:

- was nicht mehr kompatibel ist,
- welche Systeme oder Betriebsabläufe betroffen sind,
- welche Migration erforderlich ist,
- welches Rollback möglich ist,
- ob eine MAJOR-Version notwendig wird.

Das Ausrufezeichen ohne dokumentierte Auswirkung ist nicht ausreichend.

## Footer und Referenzen

Issue-Referenzen stehen im Footer oder PR-Text:

```text
Refs #43
Closes #43
```

`Closes` wird nur verwendet, wenn der Merge das Issue tatsächlich vollständig erledigt. Da Issues im Projekt erst nach Promotion und Verifikation geschlossen werden, ist in normalen Arbeits-PRs meist `Refs` korrekt.

Weitere zulässige Footer:

```text
Co-authored-by: Name <mail@example.com>
Reviewed-by: Name <mail@example.com>
```

Secrets, interne Zugangsdaten oder personenbezogene Informationen gehören nicht in Commit-Nachrichten.

## Revert-Commits

Reverts verwenden den Typ `revert` und nennen den zurückgenommenen Commit:

```text
revert(deployment): fehlerhaften Rollout zurücknehmen
```

Der Body enthält mindestens:

```text
Reverts: <commit-sha>
Reason: <begründung>
```

## Pull-Request-Titel

Der Pull-Request-Titel folgt derselben Struktur wie eine Commit-Nachricht. Dadurch bleibt auch ein Squash-Merge nachvollziehbar.

Beispiel:

```text
feat(governance): Branch-Prüfung ergänzen
```

Bei einem Breaking Change:

```text
feat(deployment)!: produktives Verzeichnislayout ändern
```

## Squash-Merges

Bei Squash-Merges wird der Pull-Request-Titel als Commit-Betreff verwendet. Deshalb muss der Titel vor dem Merge dem verbindlichen Format entsprechen.

Die PR-Beschreibung enthält weiterhin:

- Zusammenfassung,
- Tests und Validierung,
- Risiken und Rollback,
- Issue-Referenzen,
- Breaking-Change-Hinweis, sofern relevant.

## Automatische Prüfung

Der Workflow `.github/workflows/governance.yml` läuft bei Pull Requests nach `development`, `staging` und `main`.

Geprüft werden:

1. Branchname und erlaubter Zielbranch
2. Pull-Request-Titel
3. Commit-Betreffzeilen im Pull Request

Das derzeit geprüfte Muster lautet sinngemäß:

```regex
^(feat|fix|docs|chore|refactor|test|ci|build|security|revert)(\([a-z0-9-]+\))?!?: .+
```

Damit sind Typ, optionaler Scope, optionales Breaking-Change-Zeichen und eine Beschreibung technisch vorbereitet.

Die semantische Qualität von Scope, Beschreibung, Body und Breaking-Change-Dokumentation bleibt zusätzlich Bestandteil des Reviews.

Der Workflow verwendet einen GitHub-hosted Standardrunner mit `ubuntu-latest`, ein Zeitlimit von fünf Minuten und minimale Leseberechtigungen.

## Kostenkontrolle

Der Governance-Workflow enthält keine externen Paketinstallationen und keine Artefakt-Uploads. Durch `concurrency` werden ältere Läufe desselben Pull Requests abgebrochen, sobald ein neuer Commit eingeht.

## Gültige Beispiele

```text
feat(ansible): Bootstrap-Rolle ergänzen
fix(traefik): ungültige Router-Regel ablehnen
docs(governance): Commit-Scopes dokumentieren
security(ssh): Passwortanmeldung deaktivieren
ci(actions): Commit-Betreff prüfen
chore(dependencies): Action-Version aktualisieren
refactor(backup): Restore-Validierung aufteilen
test(postgres): Wiederherstellungstest ergänzen
feat(network)!: bestehendes Zonenschema ersetzen
```

## Ungültige Beispiele

```text
Update README
fixed bug
FEAT: neue Funktion
feat_governance: Regel ergänzen
feat(Governance): Regel ergänzen
feat: #43
chore(misc): stuff
```

## Ausnahmen

Merge-Commits werden bei der Prüfung der Commit-Nachrichten übersprungen.

Automatisch erzeugte Commits externer Werkzeuge dürfen nur dann abweichen, wenn das Werkzeug nicht auf das verbindliche Format konfiguriert werden kann. Die Abweichung muss dokumentiert und möglichst über einen nachfolgenden Squash-Merge normalisiert werden.

Abweichungen vom regulären Promotion-Fluss sind nur bei dokumentierten Notfällen zulässig und müssen anschließend bereinigt werden.

## Definition of Done für Issue #43

- Conventional Commits sind verbindlich festgelegt.
- zulässige Typen sind vollständig dokumentiert.
- Scope-Regeln und Beispiele sind definiert.
- Breaking Changes über `!` und `BREAKING CHANGE:` sind geregelt.
- gültige und ungültige Beispiele sind vorhanden.
- die automatische Prüfung über `.github/workflows/governance.yml` ist beschrieben und vorbereitet.

## Referenzen

- `docs/10-development-guidelines.md`
- `docs/14-branch-protection.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/governance.yml`
- Issue #29
- Issue #43
- Epic #23
- Epic #35
