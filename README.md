# Infrastructure

Zentrales Infrastructure-as-Code-Repository für die Merchfactory-Infrastruktur.

## Server-Bootstrap

Der operative Einstiegspunkt für den v0.4-Server-Bootstrap ist:

- [`docs/46-bootstrap-runbook.md`](docs/46-bootstrap-runbook.md)

Das Runbook beschreibt Voraussetzungen, Inventory, Secrets, Ausführung, Rollenreihenfolge, Validierung, Troubleshooting und Rollback für unterstützte AlmaLinux-9- und Rocky-Linux-9-Server.

Der Bootstrap selbst liegt unter:

```text
ansible/playbooks/bootstrap.yml
```

Umgebungsspezifische Inventare liegen unter:

```text
ansible/inventories/development/
ansible/inventories/staging/
ansible/inventories/production/
```

## Self-hosted Runner

Das verbindliche Betriebsmodell für Runner-Host, Co-Location mit Development-
Workloads und den GitHub-hosted Bootstrap-/Recovery-Pfad ist dokumentiert in:

- [`docs/34-github-runner-host.md`](docs/34-github-runner-host.md)
- [`docs/02-adr/ADR-0010-self-hosted-runner-betriebsmodell.md`](docs/02-adr/ADR-0010-self-hosted-runner-betriebsmodell.md)
