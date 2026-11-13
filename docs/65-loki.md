# Loki

## Zweck

Issue #89 stellt Loki als zentrale, durchsuchbare Logspeicherung für die v0.6 Monitoring-Plattform bereit.

Die Implementierung folgt ADR-0008:

- Loki 3.7.7,
- monolithischer Single-Binary-Modus,
- TSDB Schema v13,
- lokaler Filesystem-Object-Store,
- Single-Tenant,
- kein öffentlicher API-Endpunkt.

## Deployment

Artefakte:

```text
deployment/monitoring/loki/compose.yaml
monitoring/loki/loki.yaml
monitoring/loki/healthcheck.yaml
monitoring/loki/backup-policy.yaml
```

Loki hängt ausschließlich am extern vorbereiteten internen Docker-Netz:

```text
merchfactory-monitoring
```

Es gibt:

- keinen Host-Port,
- keinen Traefik-Router,
- keinen Edge-Zugang.

Alloy aus #90 wird später über dieses Netz beziehungsweise den internen Service-DNS-Namen `loki:3100` schreiben. Grafana aus #88 fragt Loki später ebenfalls intern ab.

## Image

Runtime:

```text
docker.io/grafana/loki@sha256:d70e4659623f3e109af669cae76fe2a5dd5be54e2298fe8aed380d982fbc2500
```

Upstream-Version:

```text
3.7.7
```

Der Digest wird in CI tatsächlich gepullt und über `RepoDigests` gegen den freigegebenen Wert geprüft. Das Image wird zusätzlich durch den bestehenden Container-Image-Security-Workflow mit Trivy geprüft.

Der Upstream-Container läuft als:

```text
UID 10001
GID 10001
```

Loki benötigt deshalb keinen Root-Container.

## Persistenz

Host:

```text
/srv/merchfactory/persistent/monitoring/loki
```

Container:

```text
/loki
```

Besitz:

```text
10001:10001
0750
```

Persistiert werden unter anderem:

- TSDB-Index,
- Chunks,
- Compactor-Arbeitsdaten,
- Retention-Marker.

Ein Container-Recreate darf den gespeicherten Logzustand nicht verlieren; der Integrationstest prüft das mit einem real geschriebenen und erneut abgefragten Logeintrag.

## Storage und Schema

Die Baseline verwendet:

```text
store: tsdb
schema: v13
object_store: filesystem
index period: 24h
```

Damit folgt die Neuinstallation dem aktuellen Loki-TSDB-Modell.

Der Filesystem-Store ist bewusst eine Single-Host-Lösung. Er ist kein HA- oder Cluster-Storage und soll auch nicht als solcher interpretiert werden.

## Tenantmodell

v0.6 startet bewusst als Single-Tenant:

```text
auth_enabled: false
tenant: fake / intern
```

Das ist nur zulässig, weil Loki keinerlei öffentlichen Ingress besitzt und ausschließlich innerhalb des Monitoring-Netzes erreichbar ist.

Ein späteres echtes Multi-Tenant-Modell benötigt eine eigene Architekturentscheidung und darf nicht durch frei gesetzte HTTP-Header simuliert werden.

## Labelmodell

Alloy #90 muss mindestens folgende stabilen Labels setzen:

- `environment`
- `host`
- `service`
- `component`

Optional bei begrenzter Kardinalität:

- `project`
- `container`
- `severity`

Nicht zulässig als Loki-Labels sind insbesondere:

- Request-IDs,
- Order-IDs,
- User-IDs,
- E-Mail-Adressen,
- dynamische URLs,
- freie Fehlermeldungen,
- Stacktraces.

Diese Daten dürfen im Loginhalt vorkommen, sofern sie nicht gegen Logging-/Datenschutzregeln verstoßen, aber nicht als hochkardinale Indexlabels.

## Retention für den aktuellen Development-Host

Der aktuelle reale Host ist ein ressourcenbegrenzter Development-VPS mit 80-GB-NVMe. Deshalb verwendet die Development-Baseline zunächst:

```text
retention_period: 168h
= 7 Tage
```

Retention wird durch den Loki-Compactor ausgeführt:

```text
retention_enabled: true
delete_request_store: filesystem
retention_delete_delay: 2h
```

Diese 7 Tage sind **keine Production-Retention-Freigabe**. Staging und Production existieren derzeit noch nicht als laufende Zielsysteme.

Issue #96 entscheidet später anhand echter Ingestion über:

- Retention je Logklasse,
- Production-/Staging-Werte,
- Diskbudget,
- Kapazitätsalarme,
- gegebenenfalls externen Object Storage.

## Kapazität

Loki mit Filesystem-Storage besitzt kein natives zuverlässiges „maximal X GiB und dann automatisch löschen“-Limit. Retention ist zeitbasiert.

Bis #96 gilt deshalb:

- 7 Tage Development-Retention,
- bestehende Host-Disk-Warnung ab 75 %,
- Critical ab 85 %,
- keine Behauptung eines harten Loki-Size-Caps,
- Storage-Wachstum wird über Node Exporter/Prometheus beobachtet.

Ein volles Dateisystem muss operativ verhindert werden; Loki löscht nicht allein aufgrund niedrigen freien Speichers.

## Ressourcen

Startgrenzen:

| Wert | Baseline |
|---|---:|
| CPU | 1.0 |
| CPU shares | 1024 |
| Memory Limit | 1536 MiB |
| Memory Reservation | 768 MiB |
| PIDs | 256 |

Diese Werte reservieren nicht pauschal den vollständigen RAM, sondern setzen Containergrenzen bzw. relative Priorisierung. #96 überprüft sie anhand realer Last.

## Security

Der Container verwendet:

- `read_only: true`,
- `cap_drop: ALL`,
- `no-new-privileges:true`,
- keine direkte Portfreigabe,
- nur das interne Monitoring-Netz,
- keine Docker-Socket-Freigabe,
- keine Secrets im Image oder Compose-Manifest,
- deaktivierte anonyme Usage-Analytics.

## Health

Docker-Liveness:

```text
/usr/bin/loki -version
```

Das offizielle Image ist distroless und enthält keinen Shell-/HTTP-Client.

Die eigentliche Readiness wird deshalb unabhängig aus dem Monitoring-Netz geprüft:

```text
GET http://loki:3100/ready
```

Der Runtime-Test schreibt zusätzlich einen echten Logeintrag über `/loki/api/v1/push`, fragt ihn über LogQL wieder ab und bestätigt dessen Persistenz nach einem Container-Recreate.

## Backup

Loki-Historie ist im aktuellen v0.6-Modell Datenklasse B und keine geschäftliche Primärdatenquelle.

Ein Verlust historischer Logs darf den Plattform-Wiederanlauf nicht blockieren. Die endgültige Backup-Entscheidung wird in #94 getroffen.

## Nächster Schritt

Nach Loki folgt gemäß Roadmap #90:

```text
Grafana Alloy
```

Alloy liefert anschließend erstmals echte Host- und Containerlogs an Loki.

## Referenzen

- Epic #83
- Issue #89
- ADR-0008
- `docs/61-monitoring-stack.md`
- `configuration/monitoring-stack.json`
- `configuration/logging-policy.json`
- `docs/50-volume-persistence-model.md`
