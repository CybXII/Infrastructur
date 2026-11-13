# Branch-Schutz und kostenbewusste GitHub-Governance

## Zweck

Dieses Dokument definiert den Schutz der dauerhaften Branches `development`, `staging` und `main` unter der Vorgabe, den GitHub-Betrieb nach Möglichkeit ohne zusätzliche Kosten zu führen.

Dabei wird klar zwischen drei Ebenen unterschieden:

1. organisatorisch verbindlichen Regeln,
2. aktuell kostenlos nutzbaren GitHub-Funktionen,
3. optionalen technischen Schutzmechanismen, die vom gebuchten GitHub-Tarif abhängen.

## Dauerhafte Branches

- `development` – Integration laufender Änderungen
- `staging` – freigegebener Release Candidate
- `main` – produktiv freigegebener Stand

Kurzlebige Arbeitsbranches werden von `development` erstellt und über Pull Requests zurückgeführt.

## Verbindlicher Arbeitsablauf

Unabhängig von technisch verfügbaren Rulesets gilt:

```text
Arbeitsbranch -> development -> staging -> main
```

Zusätzlich darf `main` nach einer abgeschlossenen Promotion über einen reinen Synchronisierungs-PR zurück nach `development` geführt werden, damit `development` nicht hinter `main` zurückbleibt.

Verbindliche Regeln:

- keine regulären direkten Änderungen auf `development`, `staging` oder `main`
- keine regulären Force Pushes auf dauerhafte Branches
- dauerhafte Branches werden nicht gelöscht
- Arbeitsbranches zielen auf `development`
- Promotion erfolgt ausschließlich über separate Pull Requests
- offene Issues werden in Pull Requests mit `Refs #...` referenziert
- Issues werden erst nach Promotion nach `main` und fachlicher Abnahme geschlossen
- fehlgeschlagene Repository-Tests werden vor dem Merge behoben

Diese Regeln gelten auch dann, wenn GitHub sie im aktuellen Tarif nicht vollständig technisch erzwingen kann.

## Aktueller GitHub-Actions-Betrieb

Die bestehenden Repository-Tests laufen weiterhin auf GitHub-hosted Standardrunnern:

```yaml
runs-on: ubuntu-latest
```

Ein selbst gehosteter Runner wird derzeit nicht eingerichtet.

Begründung:

- die vorhandenen Repository-Tests benötigen nur sehr wenig Laufzeit,
- aktuell wurden erst rund 24 Minuten des monatlichen Freikontingents genutzt,
- ein eigener Runner würde zusätzlichen Betriebs-, Wartungs- und Sicherheitsaufwand erzeugen,
- ein Runner auf einem produktiven VPS würde eine zusätzliche Vertrauensgrenze und Angriffsfläche schaffen.

## Kostenkontrolle für GitHub Actions

Für die kostenbewusste Nutzung gelten folgende Regeln:

- nur GitHub-hosted Standardrunner wie `ubuntu-latest` verwenden
- keine kostenpflichtigen größeren Runner aktivieren
- Workflow-Laufzeiten regelmäßig unter den GitHub-Abrechnungseinstellungen kontrollieren
- Artefakte und Caches nur bei tatsächlichem Bedarf anlegen
- Aufbewahrungszeiten für Artefakte möglichst kurz halten
- redundante Workflow-Ausführungen vermeiden
- bei deutlich steigendem Verbrauch vor einer Überschreitung des Freikontingents neu bewerten

Solange die monatliche Nutzung deutlich unter dem enthaltenen Kontingent bleibt, ist kein Wechsel auf selbst gehostete Runner vorgesehen.

## Repository-Tests

Der bestehende Workflow `Repository Tests` bleibt Teil des verbindlichen Prozesses.

Der relevante Statuscheck lautet aktuell:

```text
Static repository tests
```

Vor einem Merge ist manuell zu prüfen, dass der Workflow erfolgreich abgeschlossen wurde, sofern der aktuelle GitHub-Tarif den Check nicht technisch als verpflichtende Merge-Bedingung erzwingen kann.

## Regeln für `development`

`development` ist der Integrationsbranch.

Organisatorisch verbindlich:

- Änderungen über Pull Requests aus Arbeitsbranches
- erfolgreicher Workflow `Repository Tests`
- keine offenen Blocker
- nachvollziehbare Beschreibung, Tests, Risiken und Rollback im Pull Request
- keine fachfremden Sammeländerungen

Solange nur `@CybXII` als Maintainer und Code Owner verfügbar ist, wird keine verpflichtende unabhängige Freigabe vorausgesetzt. Eine Self-Review-Sperre darf nicht entstehen.

## Regeln für `staging`

`staging` enthält ausschließlich freigegebene Stände aus `development`.

Organisatorisch verbindlich:

- reguläre Quelle ausschließlich `development`
- separater Promotion-Pull-Request
- erfolgreiche Repository-Tests
- Release-Hinweise, Risiken und Rollback dokumentiert
- keine direkten Feature-PRs nach `staging`

## Regeln für `main`

`main` enthält ausschließlich produktiv freigegebene Stände aus `staging`.

Organisatorisch verbindlich:

- reguläre Quelle ausschließlich `staging`
- separater Promotion-Pull-Request
- erfolgreiche Staging-Verifikation
- dokumentierter Rollback- und Wiederherstellungsweg
- keine direkten Feature- oder Arbeitsbranch-PRs nach `main`

Notfallabweichungen müssen ausdrücklich dokumentiert und nachträglich bereinigt werden.

## Branch Protection und Rulesets

Branch Protection und Repository Rulesets werden nur aktiviert, soweit sie im aktuell gebuchten GitHub-Tarif ohne zusätzliche Kosten verfügbar sind.

Nicht als vorhandener Ist-Zustand dokumentiert werden dürfen Funktionen, die im aktuellen Tarif nicht aktiviert werden können.

Kostenfrei verfügbare Schutzoptionen dürfen genutzt werden, sofern sie den bestehenden Einzelmaintainer-Prozess nicht blockieren. Dazu können je nach Tarif und Repositorytyp gehören:

- Pull Requests vor Merge
- Sperre von Force Pushes
- Schutz vor Branch-Löschung
- Conversation Resolution
- erforderliche Statuschecks

Falls einzelne Optionen nicht verfügbar sind, bleiben die entsprechenden Regeln organisatorisch verbindlich und werden manuell geprüft.

## Spätere Zielkonfiguration

Sobald entweder

- ein passender GitHub-Tarif vorhanden ist oder
- ein zweiter unabhängiger Maintainer dauerhaft zur Verfügung steht,

können folgende Schutzmechanismen ergänzt werden:

- Required approvals: `1`
- Review durch Code Owner
- Verwerfen veralteter Freigaben nach neuen Commits
- Freigabe des letzten reviewbaren Pushes
- verpflichtende Statuschecks
- verpflichtend aktueller Branch-Stand
- restriktive Bypass-Regeln

Diese Erweiterung ist eine spätere Governance-Entscheidung und kein Bestandteil des aktuellen kostenfreien Betriebs.

## Prüfverfahren

Der aktuelle Prozess wird mit ungefährlichen Dokumentationsänderungen geprüft:

1. Arbeitsbranch von `development` erstellen.
2. Pull Request nach `development` öffnen.
3. Ausführung von `Repository Tests` kontrollieren.
4. Merge erst nach erfolgreichem Workflow durchführen.
5. Promotion `development -> staging -> main` über separate Pull Requests prüfen.
6. Danach bei Bedarf `main -> development` synchronisieren.
7. Monatlichen GitHub-Actions-Verbrauch kontrollieren.

Technische Negativtests für nicht verfügbare Ruleset-Funktionen sind nicht erforderlich und dürfen nicht als erfolgreich aktiviert dokumentiert werden.

## Verantwortlichkeit

Die Repository-Governance liegt aktuell bei `@CybXII`.

Regelmäßig zu prüfen sind:

- Einhaltung des Branch-Flows
- erfolgreiche Repository-Tests vor dem Merge
- GitHub-Actions-Minuten und Artefaktnutzung
- Verfügbarkeit neuer kostenloser Schutzoptionen
- Bedarf für einen zweiten Maintainer oder einen isolierten selbst gehosteten Runner

## Referenzen

- `docs/05-cicd.md`
- `docs/10-development-guidelines.md`
- `.github/CODEOWNERS`
- Issue #28
- Epic #23
