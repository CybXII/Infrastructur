# ADR-0008: Monitoring- und Observability-Stack

- Status: accepted
- Datum: 2026-09-15
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Mit Abschluss von v0.5 steht eine validierte Containerplattform mit Traefik, TLS, Netzwerksegmentierung, Persistenz, Secret-Management, Ressourcenlimits, Log-Rotation sowie Update-/Rollback-Verfahren zur Verfügung.

Epic #83 benötigt darauf aufbauend einen verbindlichen Monitoring-Stack für:

- Hostmetriken,
- Containerressourcen,
- zentrale Logs,
- Dashboards,
- Alerting,
- DNS-/TLS-/HTTP-Probes,
- später Backup- und Restore-Signale.

Die Architektur muss zur Security-First-Baseline passen und darf insbesondere nicht leichtfertig die Docker-API oder Monitoring-Administrationsoberflächen öffentlich verfügbar machen.

## Entscheidung

### Zentraler Stack

Für v0.6 werden folgende Komponenten verbindlich eingesetzt:

| Funktion | Komponente | Baseline-Version |
|---|---|---:|
| Metriken / Rules | Prometheus | 3.14.0 |
| Alert-Routing | Alertmanager | 0.34.0 |
| Dashboards | Grafana OSS | 13.2.2 |
| Logspeicher | Loki | 3.7.7 |
| Host-Logcollector | Grafana Alloy | 1.19.2 |
| Hostmetriken | Node Exporter | 1.12.1 |
| Containermetriken | cAdvisor | 0.60.5 |
| DNS/TLS/HTTP-Probes | Blackbox Exporter | 0.28.0 |

Versionen sind die verbindliche Ausgangsbasis vom 15.09.2026. Änderungen erfolgen nur per Pull Request und müssen vor Deployment erneut auf Release-, Security- und Image-Digest-Stand geprüft werden.

### Metrikmodell

Prometheus bleibt Pull-basiert.

- Prometheus scrapt Exporter und Plattformdienste.
- Der Prometheus Remote-Write-Receiver ist in der Baseline deaktiviert.
- Scrape- und Rule-Evaluationsintervall starten mit 30 Sekunden.
- Rohmetriken erhalten zunächst 30 Tage Retention.
- Eine zusätzliche Größenobergrenze ist verpflichtend.
- Die endgültige Kapazitäts- und Langzeitretention wird in #96 festgelegt.

Damit bleibt das native Prometheus-Modell mit `up`, Staleness und zentral kontrollierter Discovery erhalten.

### Hostmetriken

Node Exporter wird als systemd-verwalteter Host-Agent installiert.

Er läuft nicht als öffentlicher Dienst. Der Zugriff wird auf den Prometheus-Scrapepfad und lokale Administration begrenzt.

### Containermetriken

cAdvisor wird auf dem Docker-Host als systemd-verwalteter Host-Agent betrieben.

Grund:

- vollständige Host-/cgroup-Sicht ohne privilegierten Standard-Compose-Container,
- keine Aufweichung von `privileged=false` und `host network` der v0.5-Compose-Baseline,
- klare Trennung zwischen normalen Plattformcontainern und privilegierter Host-Telemetrie.

Der Exporter wird nur für Prometheus erreichbar gemacht und nicht öffentlich exponiert.

### Logpipeline

Grafana Alloy ist der verbindliche Logcollector.

Promtail wird nicht eingeführt.

Alloy läuft als vertrauenswürdiger systemd-Host-Agent und sammelt:

- journald/Systemlogs,
- Docker-Containerlogs über den lokalen Docker-Unix-Socket,
- eigene Collector-Telemetrie.

Der bestehende Docker-`local`-Logging-Driver bleibt unverändert.

Alloy sendet Logs an Loki. Sein Positions-/Agent-State liegt persistent unter:

```text
/var/lib/merchfactory/alloy
```

### Docker-Socket-Vertrauensgrenze

Kein normaler Container erhält den rohen Docker-Socket.

Es wird kein Docker-Daemon-TCP-Endpunkt als Monitoring-Schnittstelle aktiviert.

Alloy ist die explizite Ausnahme als hochprivilegierter Host-Agent. Seine Konfiguration:

- ist root-owned,
- wird über Ansible verwaltet,
- besitzt keine öffentliche UI,
- erhält keinen unnötigen Netzwerk-Ingress,
- wird selbst überwacht,
- verarbeitet keine Secrets aus Containerumgebungen als Loglabels.

Diese Vertrauensgrenze muss in #90 gesondert getestet werden.

### Loki

Loki startet in v0.6 als monolithischer Single-Binary-Dienst mit TSDB und lokalem Filesystem-Storage.

Begründung:

- ein primärer Plattformhost,
- geringe bis mittlere anfängliche Datenmenge,
- weniger Betriebs- und Ressourcenkomplexität als ein verteilter Loki-Cluster.

Simple Scalable Deployment wird nicht als neue Baseline eingeführt.

Loki bleibt intern. Es gibt keinen öffentlichen Loki-API-Endpunkt.

Die Plattform ist zunächst Single-Tenant. Retention und Kapazitätsgrenzen folgen #96.

### Grafana

Grafana ist die einzige regulär über Traefik erreichbare Monitoring-Weboberfläche.

Pflicht:

- TLS über Traefik,
- anonyme Nutzung deaktiviert,
- Authentifizierung verpflichtend,
- Admin-Bootstrap-Secret über Datei,
- Datasources und Dashboards versioniert/provisioniert,
- keine direkte öffentliche Freigabe von Prometheus, Loki oder Alertmanager.

Für v0.6 genügt eine einzelne Grafana-Instanz mit persistenter lokaler State-Datenbank. Ein HA-Setup benötigt später eine externe Datenbank und ist nicht Bestandteil dieses Milestones.

### Alertmanager

Prometheus wertet Regeln aus und sendet Alerts an Alertmanager.

Alertmanager übernimmt:

- Gruppierung,
- Routing,
- Inhibition,
- Silences,
- Zustellung.

Alertmanager besitzt keinen öffentlichen Edge-Zugang. Benachrichtigungsziele benötigen expliziten Outbound-Egress.

Kanäle und Empfänger werden in #92 verbindlich festgelegt.

### Blackbox Exporter

Blackbox Exporter übernimmt aktive DNS-, TCP-, TLS- und HTTP-Probes.

Er benötigt kontrollierten Outbound-Egress, aber keinen öffentlichen Ingress.

Kritische externe Erreichbarkeit darf nicht ausschließlich vom überwachten Primärhost selbst geprüft werden. #95 muss daher mindestens einen unabhängigen Probe-Pfad außerhalb dieses Hosts vorsehen.

### Netzwerkmodell

Die Monitoring-Architektur verwendet drei logische Pfade:

1. **Monitoring Core** – Prometheus, Loki, Alertmanager, Grafana und Blackbox-Kommunikation; intern.
2. **Edge** – ausschließlich Grafana wird regulär über Traefik veröffentlicht.
3. **Monitoring Egress** – ausschließlich Komponenten mit begründetem Outbound-Bedarf, insbesondere Alertmanager und Blackbox Exporter.

Prometheus, Loki und Alertmanager erhalten keine öffentlichen Hostports.

Host-Exporter-Ports bleiben durch Firewall/Source-Allowlisting auf den Prometheus-Scrapepfad beschränkt.

### Persistenz

Verbindliche Pfade:

```text
/srv/merchfactory/persistent/monitoring/prometheus
/srv/merchfactory/persistent/monitoring/grafana
/srv/merchfactory/persistent/monitoring/loki
/srv/merchfactory/persistent/monitoring/alertmanager
/var/lib/merchfactory/alloy
```

Node Exporter, cAdvisor und Blackbox Exporter sind grundsätzlich zustandslos.

### Ressourcenbaseline

Initiale Obergrenzen:

| Komponente | CPU | Memory Limit | Reservation |
|---|---:|---:|---:|
| Prometheus | 1.0 | 1536 MiB | 768 MiB |
| Loki | 1.0 | 1536 MiB | 768 MiB |
| Grafana | 0.5 | 512 MiB | 256 MiB |
| Alertmanager | 0.25 | 256 MiB | 128 MiB |
| Blackbox Exporter | 0.25 | 128 MiB | 64 MiB |

Host-Agenten:

| Agent | CPUQuota | MemoryMax |
|---|---:|---:|
| Alloy | 50 % | 512 MiB |
| Node Exporter | 25 % | 128 MiB |
| cAdvisor | 50 % | 512 MiB |

Dies sind Startwerte und keine endgültige Kapazitätsfreigabe. #96 muss Wachstum, Retention und Host-Headroom prüfen.

### Security

Verbindlich:

- Containerimages werden per SHA-256-Digest deployt.
- Images werden vor Freigabe gescannt.
- Grafana ist der einzige reguläre Edge-Dienst.
- Anonymous Grafana ist deaktiviert.
- Prometheus Admin API bleibt deaktiviert.
- Prometheus Remote-Write-Receiver bleibt deaktiviert.
- Loki bleibt ohne öffentlichen API-Zugang.
- Alertmanager bleibt ohne öffentlichen UI/API-Zugang.
- Secrets werden als Dateien injiziert.
- Keine produktiven Secrets in Labels, Logs oder Dashboards.
- Keine rohen Docker-Socket-Mounts in Standardcontainern.
- Der privilegierte Alloy-Host-Agent ist eine explizite Security-Ausnahme und wird gesondert gehärtet.

## Konsequenzen

### Positiv

- etablierter, breit unterstützter Open-Source-Stack,
- klare Trennung von Metriken, Logs, Visualisierung und Alerting,
- bestehende v0.5-Containerplattform kann direkt genutzt werden,
- Prometheus bleibt im nativen Pull-Modell,
- Docker-`local`-Logrotation muss nicht zurückgebaut werden,
- kein privilegierter cAdvisor-Compose-Container erforderlich,
- keine öffentliche Docker-API,
- keine zusätzliche verteilte Storage-Plattform in v0.6 notwendig.

### Negativ

- der primäre Monitoring-Stack ist zunächst nicht hochverfügbar,
- Loki und Prometheus teilen den Ausfallbereich des primären Hosts,
- Alloy besitzt als Docker-Logcollector eine hochprivilegierte Hostrolle,
- langfristige Metrikretention über 30 Tage ist mit der Baseline noch nicht abschließend gelöst,
- ein unabhängiger externer Probe-Pfad benötigt zusätzliche Infrastruktur außerhalb des Primärhosts.

### Risiken und Maßnahmen

- **Monitoring-Ausfall mit Hostausfall:** unabhängige externe Probes in #95.
- **Alloy-Kompromittierung:** keine öffentliche UI, lokale Socket-Nutzung, root-owned Konfiguration, minimale Netzwerkfläche und eigene Alerts.
- **Speicherwachstum:** harte Retention/Size-Limits und Kapazitätsplanung in #96.
- **Alert-Verlust:** Alertmanager-State persistent, Zustellung und Fehlerpfade in #91/#98 testen.
- **Single-Node-Loki:** Backup-/Restore-Relevanz in v0.7 bewerten; kein falsches HA-Versprechen.

## Betrachtete Alternativen

### Grafana Cloud / vollständig externes SaaS

- Vorteile: weniger Betriebsaufwand, externe Ausfallperspektive.
- Nachteile: laufende externe Abhängigkeit, Daten-/Kosten-/Governance-Fragen.
- Grund der Ablehnung: v0.6 soll die zentrale Observability-Basis selbst betreiben. Externe Probes dürfen ergänzen.

### VictoriaMetrics statt Prometheus

- Vorteile: effiziente Langzeitretention und hohe Kompression.
- Nachteile: zusätzlicher Architekturwechsel gegenüber bestehender Roadmap und Prometheus-Issues.
- Grund der Ablehnung: Prometheus ist für die aktuelle Plattformgröße ausreichend und bereits als Zielkomponente vorgesehen.

### Mimir oder Thanos bereits in v0.6

- Vorteile: horizontale Skalierung und langfristige Metrikarchitektur.
- Nachteile: deutlich höhere Betriebs-, Storage- und Fehlerkomplexität.
- Grund der Ablehnung: für den aktuellen Single-Host-Scope nicht gerechtfertigt.

### Promtail statt Alloy

- Vorteile: historisch einfache Loki-Pipeline.
- Nachteile: Promtail ist nicht mehr die unterstützte Zukunftslösung.
- Grund der Ablehnung: Alloy ist der verbindliche Collector.

### Loki Simple Scalable Deployment

- Vorteile: getrennte Read-/Write-Komponenten.
- Nachteile: zusätzliche Komplexität und keine sinnvolle Notwendigkeit für die aktuelle Last.
- Grund der Ablehnung: monolithischer Single-Binary-Modus ist für den aktuellen Scope ausreichend.

### cAdvisor als privilegierter Standardcontainer

- Vorteile: verbreitetes Deploymentmuster.
- Nachteile: kollidiert mit der v0.5-Baseline gegen privilegierte Container und benötigt tiefe Hostzugriffe.
- Grund der Ablehnung: cAdvisor wird als expliziter Host-Agent geführt.

### Docker-Socket über TCP oder Netzwerkproxy

- Vorteile: Alloy könnte vollständig containerisiert werden.
- Nachteile: vergrößert die Docker-Daemon-Angriffsfläche und schafft eine zusätzliche Netzwerk-Vertrauensgrenze.
- Grund der Ablehnung: Docker-Socket-Zugriff bleibt lokal beim vertrauenswürdigen Host-Agent.

## Umsetzung und Übergang

- #85 implementiert Prometheus.
- #86 implementiert Node Exporter.
- #87 implementiert cAdvisor/Containermetriken.
- #88 implementiert Grafana.
- #89 implementiert Loki.
- #90 implementiert Alloy und die privilegierte Host-Agent-Grenze.
- #91 implementiert Alertmanager.
- #92 entscheidet Notification Channels.
- #93 provisioniert Dashboards.
- #94 integriert Backup-Signale.
- #95 implementiert lokale und unabhängige externe Probes.
- #96 legt endgültige Retention und Kapazität fest.
- #97 erstellt das Runbook.
- #98 testet Alerts und Eskalation.
- #99 führt den v0.6-Abschlussreview durch.

## Referenzen

- Issue: Refs #84
- Epic: #83
- Architektur: `docs/01-architecture.md`
- Monitoring-Baseline: `docs/08-monitoring.md`
- Containerplattform: `docs/60-v0.5-review.md`
- Verwandte ADRs: ADR-0005, ADR-0006
- Ersetzt: –
- Ersetzt durch: –
