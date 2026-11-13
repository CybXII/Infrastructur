# Prometheus-Betrieb

## Zweck

Dieses Dokument beschreibt die v0.6-Prometheus-Implementierung aus Issue #85.

Prometheus ist der zentrale Pull-basierte Metrikspeicher und Rule-Evaluator der Merchfactory Monitoring-Plattform.

## Version und Image

Baseline:

```text
Prometheus 3.14.0
quay.io/prometheus/prometheus
```

Deployment erfolgt ausschließlich über den in `configuration/monitoring-stack.json` festgeschriebenen SHA-256-Digest.

## Netzwerk

Prometheus besitzt:

- keinen Host-Port,
- keinen Edge-Netzwerkzugang,
- keinen regulären Traefik-Router.

Es hängt ausschließlich am gemeinsamen internen Netz:

```text
merchfactory-monitoring
```

Das Netz ist Docker-`internal=true` und wird über:

```bash
bash platform/network/scripts/prepare-monitoring-network.sh
```

idempotent erstellt oder geprüft.

Spätere Monitoring-Komponenten wie Grafana, Loki, Alertmanager und Blackbox Exporter verwenden denselben internen Core.

## Storage

TSDB-Pfad auf dem Host:

```text
/srv/merchfactory/persistent/monitoring/prometheus
```

Containerpfad:

```text
/prometheus
```

Owner:

```text
65534:65534
```

Der Integrationstest verifiziert, dass das gepinnte Prometheus-Image den `nobody`-User tatsächlich mit diesen IDs bereitstellt.

## Retention

Initiale Baseline:

```text
--storage.tsdb.retention.time=30d
--storage.tsdb.retention.size=8GiB
```

Beide Grenzen gelten gleichzeitig. Prometheus entfernt Daten, sobald eine der Retentionbedingungen greift.

Das 8-GiB-Cap ist bewusst konservativ und verhindert unkontrolliertes Wachstum, bis #96 reale Ingestion, Cardinality und Hostkapazität bewertet.

## Konfiguration

Quelle:

```text
monitoring/prometheus/prometheus.yml
```

Global:

```text
scrape_interval: 30s
evaluation_interval: 30s
```

Runtime-Kontext wird über `external_labels` gesetzt:

- `environment`
- `host`

Prometheus 3 expandiert dort Environment-Variablen standardmäßig.

## Self-Scrape

Prometheus scrapt:

```text
http://127.0.0.1:9090/metrics
```

Job:

```text
prometheus
```

Stabile Target-Labels:

- `service=prometheus`
- `component=metrics`

## Node Exporter

Seit #86 scrapt Prometheus den Host-Agent über `file_sd`:

```text
monitoring/prometheus/targets/node-exporter.yml
```

Scrapeziel:

```text
172.30.250.1:9100
```

Prometheus und Node Exporter kommunizieren ausschließlich über das interne `merchfactory-monitoring`-Netz. Host-Alertregeln stehen in `monitoring/prometheus/rules/node-exporter.yml`.

## cAdvisor

Seit #87 scrapt Prometheus die Container-Metrikquelle über `file_sd`:

```text
monitoring/prometheus/targets/cadvisor.yml
```

Scrapeziel:

```text
172.30.250.1:8080
```

Der Agent liefert CPU-, Working-Set-RAM-, Netzwerk-, Filesystem- und Startzeitmetriken. `monitoring/prometheus/rules/cadvisor.yml` normalisiert diese Daten über Recording Rules. Container-Neustarts werden aus Änderungen von `container_start_time_seconds` als `container:restarts:15m` sichtbar.

Ungefilterte Docker-Labels werden nicht übernommen. Freigegeben sind nur die Merchfactory-Management-Labels sowie Docker-Compose-Projekt und -Service.

## Self-Monitoring-Rules

Datei:

```text
monitoring/prometheus/rules/self-monitoring.yml
```

Enthalten sind:

- `PrometheusConfigurationReloadFailure`
- `PrometheusRuleEvaluationFailures`
- `PrometheusTSDBCompactionsFailing`
- `PrometheusSelfScrapeDown`

Alertmanager wird erst mit #91 angebunden. Bis dahin werden Rules ausgewertet und Alerts lokal sichtbar, aber nicht zugestellt.

Ein vollständiger Prometheus-Prozessausfall kann naturgemäß nicht allein vom ausgefallenen Prometheus selbst alarmiert werden. Die unabhängige Außenperspektive folgt mit #95.

## Health

Liveness:

```text
GET http://127.0.0.1:9090/-/healthy
```

Readiness intern:

```text
GET http://prometheus:9090/-/ready
```

Prometheus besitzt absichtlich keinen öffentlichen Readiness-Endpunkt.

## Security

Compose erzwingt:

- numerische UID/GID `65534:65534`,
- `read_only: true`,
- `cap_drop: ALL`,
- `no-new-privileges:true`,
- kein Host-Networking,
- keine Hostports,
- keine Docker-Socket-Mounts,
- CPU-/Memory-/PID-Limits.

Nicht aktiviert:

```text
--web.enable-admin-api
--web.enable-remote-write-receiver
--web.enable-lifecycle
```

Konfigurationsreload erfolgt später bei Bedarf über einen kontrollierten Container-Recreate oder SIGHUP, nicht über einen öffentlich mutierenden HTTP-Endpunkt.

## Ressourcen

Initial:

```text
CPU hard limit:        1.0
CPU shares:            1024
Memory limit:          1536 MiB
Memory reservation:    768 MiB
PID limit:             256
```

Diese Werte stammen aus `configuration/resource-policy.json` und werden in #96 anhand realer Last erneut bewertet.

## Backup und Restore

### TSDB

Klasse B – betriebsrelevante Daten.

Für v0.6 gilt:

```text
Backup required: false
Restore: leere TSDB erstellen und Scraping wieder aufnehmen
```

Begründung:

- historische Metriken sind wertvoll, aber keine geschäftliche Primärdatenquelle,
- ein TSDB-Verlust darf den Wiederanlauf nicht blockieren,
- die Plattformkonfiguration bleibt vollständig reproduzierbar,
- die Admin-API wird nicht allein für Snapshot-Erstellung geöffnet.

#96 und die spätere Backup-Umsetzung dürfen diese Entscheidung neu bewerten.

### Konfiguration und Rules

Klasse C – aus Git reproduzierbar.

Kein separates Datenbackup erforderlich.

## Deployment-Vorbereitung

Monitoring-Netz:

```bash
bash platform/network/scripts/prepare-monitoring-network.sh
```

Persistenzverzeichnis:

```bash
sudo install -d \
  -o 65534 \
  -g 65534 \
  -m 0750 \
  /srv/merchfactory/persistent/monitoring/prometheus
```

Vor Deployment:

```bash
python3 scripts/validate-compose-standards.py \
  deployment/monitoring/prometheus/compose.yaml

python3 scripts/validate-image-policy.py \
  deployment/monitoring/prometheus/compose.yaml
```

## Start

```bash
docker compose \
  -p monitoring-prometheus \
  -f deployment/monitoring/prometheus/compose.yaml \
  pull

docker compose \
  -p monitoring-prometheus \
  -f deployment/monitoring/prometheus/compose.yaml \
  up -d
```

## Prüfung

```bash
docker compose \
  -p monitoring-prometheus \
  -f deployment/monitoring/prometheus/compose.yaml \
  ps

docker compose \
  -p monitoring-prometheus \
  -f deployment/monitoring/prometheus/compose.yaml \
  logs --tail=100 prometheus
```

Prometheus ist nicht vom Host aus veröffentlicht. Diagnose erfolgt über Docker-/interne Monitoring-Pfade.

## Update und Rollback

Das Image ist kompatibel mit dem Digest-basierten Verfahren aus `docs/57-update-rollback.md`.

Da die TSDB über einen Bind-Mount erhalten bleibt, muss vor einem Versionsdowngrade geprüft werden, ob sich das TSDB-Format zwischen den betroffenen Prometheus-Versionen rückwärtskompatibel verhält.

Ein blindes Image-Downgrade gegen einen nicht kompatiblen TSDB-Zustand ist nicht zulässig.

## CI-Nachweis

`tests/integration/test-prometheus-deployment.sh` prüft:

1. internes Shared-Monitoring-Netz,
2. Compose- und Image-Policy,
3. Image-Digest-Pull,
4. Runtime-UID/GID,
5. `promtool check config`,
6. Health,
7. keine Hostports,
8. exakte Netzwerkmitgliedschaft,
9. Self-Scrape,
10. expandierte Runtime-Labels,
11. 30d/8GiB-Retention,
12. deaktivierte Admin-/Remote-Write-Funktionen,
13. geladene Self-Monitoring-Rules,
14. TSDB-Daten vor und nach Container-Recreate,
15. persistente Ownership.

## Referenzen

- Issue #85
- Issue #86
- Issue #87
- Epic #83
- ADR-0008
- `configuration/monitoring-stack.json`
- `configuration/resource-policy.json`
- `monitoring/prometheus/backup-policy.yaml`
- `docs/63-node-exporter.md`
- `docs/64-cadvisor.md`
