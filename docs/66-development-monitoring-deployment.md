# Development Monitoring-Core Deployment

## Zweck

Dieser Deploymentpfad trennt die Host-Baseline von den containerisierten Environment-Services.

Der Host-Bootstrap verwaltet weiterhin ausschließlich hostweite Grundlagen wie SSH, Firewall, Fail2ban, Docker, Node Exporter und cAdvisor. Prometheus und Loki werden dagegen als Development-Environment-Services über einen eigenen Releasepfad ausgerollt.

## Trigger und Gates

Reusable Workflow:

```text
.github/workflows/deploy-development-monitoring.yml
```

Der Repository-Default-Branch bleibt bewusst `main`. Deshalb verwendet der Development-Deploypfad **kein** `workflow_run`-Event: solche Empfänger müssen bei GitHub auf dem Default Branch vorhanden sein und würden die gewünschte Development-only-Pipeline sonst nicht zuverlässig auslösen.

Stattdessen ruft `.github/workflows/tests.yml` den Deploymentworkflow nach einer vollständig erfolgreichen Repository-Testsuite per `workflow_call` direkt aus demselben Development-Commit auf.

Vor dem eigentlichen Deployment wartet der Gate-Schritt zusätzlich auf:

```text
Container Image Security = success
```

für exakt denselben Commit. Erst dann darf der VPS verändert werden.

Für Monitoring-Core-relevante Konfigurationsänderungen startet der Image-Security-Workflow ebenfalls, damit kein relevanter Development-Deploy ohne dieses Gate stattfinden kann.

Zusätzlich wird der Commit-Diff geprüft. Unabhängige Änderungen deployen den Monitoring-Core nicht neu.

## Zielhost

Aktuell gilt das Topologieprofil `development-only`.

Der Workflow verwendet denselben verwalteten Development-Host und dieselben SSH-Secrets wie der Managed-Host-Bootstrap. Dadurch entsteht kein zweiter impliziter Hostvertrag.

## Release-Artefakt

Der freigegebene Repository-Stand wird revisionsbezogen abgelegt:

```text
/srv/merchfactory/releases/development-monitoring/<commit-sha>/
```

Nach erfolgreichem Deployment zeigt:

```text
/srv/merchfactory/releases/development-monitoring/current
```

auf den verifizierten Release.

Konfigurationsdateien werden damit nicht aus einem flüchtigen Runner- oder `/tmp`-Pfad in Container gemountet.

## Service-State

Prometheus:

```text
/srv/merchfactory/deployments/development-prometheus/
├── release.env
├── state.json
└── .deployment.lock
```

Loki:

```text
/srv/merchfactory/deployments/development-loki/
├── release.env
├── state.json
└── .deployment.lock
```

Beide verwenden `deployment/service-release.py`.

Der Controller unterstützt weiterhin `SERVICE_IMAGE_REFERENCE` als Default, erlaubt aber explizite service-spezifische Keys wie `PROMETHEUS_IMAGE_REFERENCE` und `LOKI_IMAGE_REFERENCE`.

## Gemeinsamer Release und Rollback

Prometheus und Loki bleiben getrennte Compose-Projekte:

```text
merchfactory-development-prometheus
merchfactory-development-loki
```

Vor dem Deployment werden der vorherige `current`-Release und beide Service-States gesichert.

Scheitert einer der Dienste, werden die vorherigen State-Dateien und – sofern vorhanden – die vorherigen Compose-Konfigurationen wiederhergestellt. Bei einem allerersten fehlgeschlagenen Release werden Teildeployments entfernt.

Erst wenn beide Services erfolgreich verifiziert wurden, wird `current` auf den neuen Commit gesetzt.

## Netzwerk und Persistenz

Vor jedem Deployment werden idempotent vorbereitet:

```text
merchfactory-monitoring
/srv/merchfactory/persistent/monitoring/prometheus
/srv/merchfactory/persistent/monitoring/loki
```

Besitz:

```text
Prometheus  65534:65534  0750
Loki        10001:10001  0750
```

## Post-Deployment-Verifikation

`scripts/verify-monitoring-service.py` prüft auf dem Zielhost:

- exakt einen laufenden Compose-Service,
- erwarteten Image-Digest,
- kein Host-Portbinding,
- ausschließlich `merchfactory-monitoring`,
- Container nicht unhealthy,
- internen Readiness-Endpunkt direkt über die Container-IP.

Readiness:

```text
Prometheus  /-/ready :9090
Loki        /ready   :3100
```

Damit muss kein Monitoring-API-Port für Deploymentchecks veröffentlicht werden.

## Sicherheitsmodell

- Deployment erst nach CI- und Image-Security-Gate.
- SSH Host-Key-Checking bleibt aktiv.
- Der verwaltete `bootstrap`-Account benötigt weiterhin erfolgreich `sudo -n`.
- Release-Inhalte werden root-owned abgelegt.
- Keine Secrets werden in den Release-Tarball geschrieben.
- Keine Monitoring-API wird öffentlich exponiert.
- Host-Baseline und Environment-Service-Deployment bleiben getrennte Workflows.

## Nächster Schritt

Nach real erfolgreichem Prometheus-/Loki-Deployment kann #90 Grafana Alloy als Host-Agent umgesetzt werden. Alloy erhält dann ein tatsächlich laufendes Loki-Ziel.

## Referenzen

- Issue #279
- ADR-0009
- `docs/06-deployment.md`
- `docs/57-update-rollback.md`
- `docs/62-prometheus.md`
- `docs/65-loki.md`
