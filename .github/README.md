# `.github`

## Zweck

Dieses Verzeichnis enthält GitHub-spezifische Governance und Automatisierung.

## Einstieg

Hier werden insbesondere GitHub Actions, Issue- und Pull-Request-Templates, CODEOWNERS sowie weitere Repository-Regeln abgelegt.

## CODEOWNERS

Die Datei `.github/CODEOWNERS` ordnet kritische Repositorybereiche einer verbindlichen Review-Verantwortung zu. Aktuell ist `@CybXII` als verantwortlicher Owner für das Repository sowie insbesondere für Security, Deployment, Backup, Restore, Monitoring, Architektur und Governance hinterlegt.

Damit CODEOWNERS als verbindliche Review-Pflicht wirkt, muss die Branch Protection für die geschützten Zielbranches zusätzlich die Option für erforderliche Reviews durch Code Owner aktivieren. Die Datei allein fordert Reviews an, ersetzt aber keine Branch-Protection-Regel.

Neue Teams oder Verantwortliche werden ergänzt, sobald weitere Maintainer dauerhaft Zugriff und fachliche Zuständigkeit erhalten. Änderungen an `.github/CODEOWNERS` selbst unterliegen ebenfalls der Governance-Verantwortung.

## Bootstrap-Workflows

Die Bootstrap-Prüfungen sind in zwei Workflows getrennt:

- `bootstrap-validation.yml` führt bei relevanten Pull Requests ausschließlich
  statische Prüfungen ohne Secrets und ohne Serverzugriff aus.
- `bootstrap-fresh-host.yml` läuft ausschließlich aus `development` oder über
  einen bewussten manuellen Start und greift auf den freigegebenen
  Development-Testhost zu.

Der Fresh-Host-Job ist zusätzlich durch die Repository-Variable
`DEVELOPMENT_BOOTSTRAP_FRESH_HOST_ENABLED` geschützt. Nur der exakte Wert
`true` aktiviert den Job. Details stehen in `docs/46-bootstrap-runbook.md`.

## Abgrenzung

Fachliche Deployment-, Prüf- und Betriebsskripte gehören in `deployment/`, `tests/` oder `scripts/`. Secrets und produktive Konfigurationen gehören nicht in dieses Verzeichnis.

## Referenzen

- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`
- `docs/46-bootstrap-runbook.md`
- Issue #27
