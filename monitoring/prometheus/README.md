# Prometheus

## Zweck

Dieser Bereich enthält die versionierte Prometheus-Konfiguration der v0.6 Monitoring-Plattform.

## Baseline

- Prometheus 3.14.0
- Pull-basiertes Scraping
- 30 Sekunden Scrape-Intervall
- 30 Sekunden Rule-Evaluation
- 30 Tage Zeitretention
- 8 GiB vorläufiges TSDB-Size-Cap
- kein Public Ingress
- keine Prometheus Admin API
- kein Remote-Write-Receiver

## Self-Monitoring

Prometheus scrapt sich selbst unter:

```text
127.0.0.1:9090
```

Self-Monitoring-Rules liegen unter `rules/`.

Alertmanager wird erst mit Issue #91 angebunden. Bis dahin sind Alerts in Prometheus auswertbar, werden aber nicht extern zugestellt.

## Konfiguration

`environment` und `host` werden über Prometheus `external_labels` aus Runtime-Environment-Variablen gesetzt.

Der Self-Scrape erhält zusätzlich:

- `service=prometheus`
- `component=metrics`

Node Exporter wird über `file_sd` aus `targets/node-exporter.yml` gescrapt.

Aktueller Host-Scrapepfad:

```text
Prometheus
  -> merchfactory-monitoring
  -> 172.30.250.1:9100
  -> Node Exporter
```

Stabile Target-Labels:

- `service=node-exporter`
- `component=host-metrics`

Die Host-Alerts liegen in `rules/node-exporter.yml`; die Promtool-Tests dazu unter `rules/tests/node-exporter.test.yml`.

## Deployment

Compose:

```text
deployment/monitoring/prometheus/compose.yaml
```

Shared Core Network:

```text
merchfactory-monitoring
```

Das Netzwerk ist `internal=true`. Prometheus erhält weder Edge-Netz noch Host-Port.

## Persistenz

TSDB:

```text
/srv/merchfactory/persistent/monitoring/prometheus
```

Owner:

```text
65534:65534
```

Die numerische Runtime-ID entspricht dem `nobody`-User des gepinnten Prometheus-Busybox-Images und wird im Integrationstest verifiziert.

## Backup

Die TSDB ist Klasse B und keine geschäftliche Primärdatenquelle.

Ein vollständiges TSDB-Backup ist in v0.6 nicht verpflichtend. Bei Verlust wird Prometheus mit leerer TSDB reproduzierbar neu gestartet und sammelt ab diesem Zeitpunkt neue Messwerte.

Konfiguration und Rules sind Klasse C und werden aus Git wiederhergestellt.

Die Entscheidung wird in #96 und der späteren Backup-Umsetzung erneut bewertet.

## Referenzen

- Issue #85
- Issue #86
- Epic #83
- ADR-0008
- `docs/61-monitoring-stack.md`
- `docs/50-volume-persistence-model.md`
- `monitoring/prometheus/backup-policy.yaml`
- `monitoring/prometheus/healthcheck.yaml`
- `docs/63-node-exporter.md`
