# CI Runner-Kosten und Ausfallsicherheit (2026-10-14)

## Grundsatz

Die Plattform verwendet den bestehenden `ephemeral-linux` Runner-Pool für
isolierte statische Prüfungen, Docker/Compose-Integrationstests und
Container-Image-Scans. Der Pool nutzt kurzlebige Runner mit getrenntem
Docker-in-Docker-Sidecar und `MAX_RUNNERS=2` (siehe
`docs/34-github-runner-host.md` und ADR-0010).

Hoständernde Workflows bleiben auf `ubuntu-24.04`, insbesondere
`bootstrap-fresh-host`, `bootstrap-managed-host`,
`bootstrap-idempotency`, Development Monitoring Deployment und
Backup-E2E-Installation. Sie können die Docker-/Netzwerk- oder Runner-Plattform
auf dem gemeinsamen VPS beeinflussen und dürfen nicht vom eigenen Runner
abhängen. Die Prometheus-Host-Integration bleibt wegen privilegierter
Host-/systemd-Tests ebenfalls GitHub-hosted.

## Kosten- und Laufzeitsteuerung

- `governance.yml` und normale `reusable-static-validation.yml`-Jobs
  verwenden `ephemeral-linux`.
- `bootstrap-validation.yml`, `image-security.yml` und
  `reusable-image-security.yml` verwenden `ephemeral-linux`.
- `reusable-static-validation.yml` bestimmt anhand des Commit-Diffs die
  betroffenen Integrationstests; bei reinen Dokumentationsänderungen wird
  insbesondere die GitHub-hosted Prometheus-Integration übersprungen.
- `image-security.yml` verwendet Path-Filter für PRs und Pushes; der
  wöchentliche Scan bleibt bestehen, läuft aber auf Self-hosted Runnern.
- Jobs haben Timeouts. Ein Timeout begrenzt den Job, garantiert aber nicht
  kurze Laufzeiten oder die Verfügbarkeit des Runner-Pools.
- `Repository Tests` läuft auf PRs und Pushes; ein reiner Dokumentations-Merge
  löst die kurzen Basistests erneut aus, aber keinen Backup-E2E-Deploy.
- Die Development-Monitoring-Deployment-Stufe prüft den Commit-Diff und
  überspringt den eigentlichen Deploy ohne relevante Änderungen.

## Sicherheitsgrenzen und Ausfallpfad

Self-hosted Runner sind für Jobs mit Auswirkungen auf den eigenen Controller,
die Host-Docker-Runtime, Netzwerk, Firewall oder Bootstrap **nicht** zulässig.
Die verbindlichen Guardrails in
`tests/static/test-runner-execution-guardrails.sh` prüfen diese Zuordnung.

Wenn Self-hosted Runner ausfallen, bleiben Bootstrap- und Recovery-Jobs über
GitHub-hosted Runner ausführbar. Andere CI-Jobs warten gegebenenfalls in der
Queue; sie fallen nicht automatisch auf GitHub-hosted Runner zurück. Ein
Fallback für diese Jobs erfordert eine bewusste Änderung und Prüfung.

## Noch zu validieren

Vor Merge: Self-hosted Image-Scan auf dem ephemeren Docker-in-Docker-Runner
inklusive Trivy-Setup und Image-Registry-Zugriff nachweisen; Static-/Bootstrap-
Validation erfolgreich. GitHub-hosted Integrations- und Deployment-Jobs
dürfen dabei nicht unbeabsichtigt ausgelöst werden.

GitHub Actions stellt keinen vollständigen Kosten-Stopp durch diese
Konfiguration bereit. Budget-/Spending-Limits im GitHub-Konto sind separat
zu konfigurieren und zu überwachen.
