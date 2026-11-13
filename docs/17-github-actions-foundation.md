# GitHub-Actions-Grundstruktur

## Zweck

Dieses Dokument beschreibt die modulare Grundstruktur der GitHub-Actions-Workflows im Repository.

Ziel ist eine klare Trennung zwischen:

- auslösenden Workflows,
- wiederverwendbarer Prüfungslogik,
- Governance-Prüfungen,
- späteren Deployment-Workflows.

## Aktuelle Workflows

### `tests.yml`

Der Workflow `Repository Tests` ist der auslösende Workflow für Pull Requests und Pushes auf:

- `development`
- `staging`
- `main`

Er enthält bewusst keine eigene fachliche Testlogik mehr, sondern ruft den wiederverwendbaren Workflow `reusable-static-validation.yml` auf.

### `reusable-static-validation.yml`

Dieser Workflow wird über `workflow_call` eingebunden und enthält die derzeitigen statischen Prüfungen:

- Repositorystruktur
- Service-Referenzstruktur

Der sichtbare Jobname bleibt:

```text
Static repository tests
```

Dadurch bleibt der bestehende Statuscheck nachvollziehbar und kann später als Merge-Bedingung verwendet werden, sofern der GitHub-Tarif dies technisch erlaubt.

### `governance.yml`

Der Governance-Workflow bleibt eigenständig, weil er ausschließlich auf Pull-Request-Metadaten und Git-Historie arbeitet.

Geprüft werden:

- Branchname
- Zielbranch
- Pull-Request-Titel
- Commit-Nachrichten

## Berechtigungen

Alle aktuellen Workflows verwenden minimale Leseberechtigungen:

```yaml
permissions:
  contents: read
```

Der Governance-Workflow benötigt zusätzlich:

```yaml
pull-requests: read
```

Schreibberechtigungen, Secrets oder Deployment-Zugriffe sind in der aktuellen CI-Grundstruktur nicht enthalten.

## Trigger

Die statischen Repository-Tests laufen bei:

- Pull Requests nach `development`, `staging` und `main`
- Pushes auf `development`, `staging` und `main`

Der Governance-Workflow läuft nur bei Pull Requests, weil seine Prüfungen Pull-Request-Daten benötigen.

## Concurrency

Der auslösende Testworkflow verwendet `concurrency` und bricht ältere Läufe für denselben Workflow und Git-Ref ab.

Dadurch werden unnötige parallele Läufe reduziert, ohne neue Artefakte oder externe Dienste einzuführen.

## Fehlerverhalten

Ein fehlgeschlagener Testschritt beendet den jeweiligen Job mit einem Fehlerstatus.

Vor einem Merge müssen mindestens folgende Checks erfolgreich sein:

- `Static repository tests`
- `Branch and commit conventions`

Wenn der aktuelle GitHub-Tarif diese Checks nicht technisch erzwingen kann, bleibt die manuelle Prüfung vor dem Merge verbindlich.

## Erweiterungsmodell

Neue Prüfungen werden nach folgender Regel ergänzt:

1. Wiederverwendbare fachliche Prüfungen kommen in einen `workflow_call`-Workflow.
2. Auslösende Workflows definieren Ereignisse, Branches und Concurrency.
3. Komplexe Prüfungslogik wird möglichst in versionierten Skripten unter `tests/` oder `scripts/` abgelegt.
4. Deployment-Workflows werden getrennt von CI- und Governance-Prüfungen aufgebaut.
5. Secrets werden erst bei konkretem Deployment-Bedarf und je Umgebung getrennt eingeführt.

## Deployment-Vorbereitung

Die Grundstruktur bereitet spätere Deployment-Workflows vor, aktiviert aber noch kein Deployment.

Spätere Workflows sollen:

- ausschließlich freigegebene Branches oder Tags verwenden,
- je Zielumgebung getrennte Berechtigungen besitzen,
- GitHub Environments nur einsetzen, soweit dies technisch und tariflich sinnvoll ist,
- keine produktiven Secrets an Pull-Request-Workflows weitergeben,
- Rollback- und Verifikationsschritte enthalten.

## Kostenkontrolle

Alle aktuellen Workflows verwenden weiterhin:

```yaml
runs-on: ubuntu-latest
```

Es werden keine größeren Runner, Artefakt-Uploads oder externen Paketinstallationen verwendet.

Die Laufzeiten werden regelmäßig kontrolliert. Solange die Nutzung deutlich unter dem monatlichen Freikontingent bleibt, ist kein selbst gehosteter Runner vorgesehen.

## Referenzen

- `.github/workflows/tests.yml`
- `.github/workflows/reusable-static-validation.yml`
- `.github/workflows/governance.yml`
- `docs/14-branch-protection.md`
- `docs/15-branch-commit-conventions.md`
- Issue #31
- Epic #23
