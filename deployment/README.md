# Deployment

## Zweck

Dieses Verzeichnis enthält die reproduzierbare Bereitstellung und Aktualisierung von Plattformdiensten.

## Einstieg

Hier liegen Deployment-Manifeste, Service- und Stack-Definitionen, Migrationen, Rollback-Abläufe sowie Preflight- und Post-Deployment-Schritte.

Der Referenzcontroller für containerisierte Standardservices ist:

```text
deployment/service-release.py
```

Er verwaltet Digest-basierte Updates, bekannten guten Release-State, Verifikationsprobes und sichere Rollbacks. Details stehen in `docs/57-update-rollback.md`.

Der erste v0.6 Monitoring-Dienst liegt unter:

```text
deployment/monitoring/prometheus/compose.yaml
```

Betriebs-, Retention- und Self-Monitoring-Vertrag: `docs/62-prometheus.md`.

## Abgrenzung

Gemeinsame Konfigurationswerte gehören nach `configuration/`. GitHub Workflows orchestrieren Deployments aus `.github/`, enthalten aber möglichst keine fachliche Deployment-Logik.

## Referenzen

- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/09-repository-structure.md`
- `docs/57-update-rollback.md`
- `docs/62-prometheus.md`
