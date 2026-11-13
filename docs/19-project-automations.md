# GitHub-Project-Automationen

## Zweck

Dieses Dokument definiert die Zuordnung zwischen GitHub-Issues, Statuslabels und dem GitHub Project für `Merchfactory/Infrastructure`.

## Statusmodell

| Statuslabel | Bedeutung | Board-Spalte |
|---|---|---|
| `status: backlog` | Erfasst, noch nicht begonnen | Backlog |
| `status: in-progress` | Aktive Bearbeitung | In Progress |
| `status: review` | Umsetzung liegt zur Prüfung oder Promotion vor | Review |
| `status: blocked` | Durch Abhängigkeit oder Entscheidung blockiert | Blocked |
| `status: done` | In `main`, geprüft und abgeschlossen | Done |

Pro Issue darf nur ein `status:*`-Label aktiv sein.

## Automatische Aufnahme

Neue Issues aus dem Repository sollen automatisch in das Project aufgenommen werden.

Empfohlener Filter:

```text
repo:Merchfactory/Infrastructure is:issue
```

Pull Requests bleiben über `Refs #<issue>` mit dem jeweiligen Arbeitspaket verbunden.

## Statuswechsel

### Backlog

Neue Aufgaben erhalten `status: backlog` und werden der Spalte `Backlog` zugeordnet.

### In Progress

Bei tatsächlichem Arbeitsbeginn wird das bisherige Statuslabel durch `status: in-progress` ersetzt und die Karte nach `In Progress` verschoben.

### Review

Sobald ein vollständiger Pull Request gegen `development` vorliegt, wird `status: review` gesetzt und die Karte nach `Review` verschoben. Dieser Status bleibt bestehen, solange die Änderung nur in `development` oder `staging` liegt.

### Blocked

Kann eine Aufgabe nicht fortgesetzt werden, wird `status: blocked` gesetzt, der Blocker im Issue beschrieben und die Karte nach `Blocked` verschoben.

### Done

Ein Issue wird erst abgeschlossen, wenn:

1. die Änderung nach `main` promoted wurde,
2. die erforderlichen Checks erfolgreich waren,
3. die fachliche Verifikation abgeschlossen ist,
4. keine offenen Nacharbeiten zum Scope bestehen.

Dann wird `status: done` gesetzt, das Issue als abgeschlossen markiert und die Karte nach `Done` verschoben. Ein Merge nach `development` oder `staging` reicht dafür nicht aus.

## Empfohlene Project-Workflows

Im GitHub Project sollen folgende Workflows aktiviert werden:

1. **Auto-add to project** mit dem Filter `repo:Merchfactory/Infrastructure is:issue`
2. **Item added to project** setzt den Project-Status auf `Backlog`
3. **Item closed** setzt den Project-Status auf `Done`
4. **Item reopened** setzt den Project-Status auf `Backlog`

Die Statuswerte `In Progress`, `Review` und `Blocked` werden parallel zu den entsprechenden Issue-Labels gepflegt. Falls keine direkte Label-zu-Status-Automation verfügbar ist, wird die Board-Spalte manuell angepasst.

## Abgleich zwischen Labels und Board

Das Statuslabel ist die repository-nahe Statusquelle. Das Board ist die visuelle Projektansicht.

Bei Abweichungen wird zuerst der tatsächliche Arbeitsstand geprüft, anschließend das Statuslabel korrigiert und danach die Board-Spalte angeglichen.

## Validierung

Die Konfiguration wird mit einem temporären Test-Issue geprüft:

1. Test-Issue anlegen und automatische Aufnahme kontrollieren.
2. Wechsel von `Backlog` zu `In Progress` prüfen.
3. Wechsel zu `Review` prüfen.
4. Wechsel zu `Blocked` und zurück prüfen.
5. Issue schließen und den Wechsel zu `Done` prüfen.
6. Issue erneut öffnen und den Wechsel zu `Backlog` prüfen.

## Verantwortlichkeit

`CybXII` konfiguriert die Project-Workflows und kontrolliert die Statuskonsistenz.

## Technische Grenze

Die verwendete GitHub-Integration kann Issues, Labels und Pull Requests verwalten, aber keine GitHub-Project-Spalten oder Project-Workflow-Einstellungen ändern. Diese Konfiguration muss daher einmalig direkt in der GitHub-Oberfläche erfolgen.

## Definition of Done für Issue #33

- Auto-add ist aktiviert.
- Board-Spalten und Statuslabels sind abgestimmt.
- Close- und Reopen-Automationen sind aktiviert.
- Ein Test-Issue hat alle relevanten Statuswechsel erfolgreich durchlaufen.
- Das Ergebnis ist in Issue #33 dokumentiert.

## Referenzen

- Issue #33
- Epic #23
- `docs/15-branch-commit-conventions.md`
- `docs/17-github-actions-foundation.md`
