# Monitoring

## Zweck

Dieses Verzeichnis enthält die versionierten Observability-, Logging-, Healthcheck-, Dashboard- und Alerting-Definitionen der v0.6 Monitoring-Plattform.

Die verbindliche Produktauswahl und Architektur stehen in:

- `docs/02-adr/ADR-0008-monitoring-stack.md`
- `docs/61-monitoring-stack.md`
- `configuration/monitoring-stack.json`

## App-eigene Monitoring-Definitionen

Apps definieren öffentliche Prüfpunkte im eigenen Repository und übergeben
sie zukünftig über den **bestehenden berechtigten Deploymentpfad**. Die
Infrastruktur betreibt den generischen Blackbox-Exporter und Prometheus-
Discovery; App-CI erhält keine Schreibrechte auf globale Monitoring-Dateien.
Der Offline-Compiler ist vorhanden, der Live-Handoff noch nicht freigegeben.
Kein zusätzlicher OIDC-/HTTP-Registrierungsdienst für #95.
Siehe [Service-Vertrag](../docs/75-monitoring-service-contract.md).

Eine spätere persönliche Betreiberübersicht für mehrere getrennte Kunden-
instanzen wird nur unter [Issue #325](https://github.com/Merchfactory/Infrastructure/issues/325)
vorgemerkt und gehört nicht zu diesem Monitoring-Release.

## Stack

Verbindliche Komponenten:

- Prometheus
- Alertmanager
- Grafana
- Loki
- Grafana Alloy
- Node Exporter
- cAdvisor
- Blackbox Exporter

Promtail ist nicht Bestandteil der Architektur.

## Geplante Struktur

```text
monitoring/
├── prometheus/
│   ├── prometheus.yml
│   ├── rules/
│   └── targets/
├── alertmanager/
│   └── alertmanager.yml
├── grafana/
│   ├── dashboards/
│   └── provisioning/
├── loki/
│   └── loki.yaml
├── alloy/
│   └── config.alloy
├── blackbox/
│   └── blackbox.yml
└── README.md
```

Die Verzeichnisse werden mit den jeweiligen Implementierungsissues angelegt. Prometheus ist mit Issue #85 unter `monitoring/prometheus/` umgesetzt. Node Exporter und die zugehörigen Prometheus-Targets/Alerts sind mit #86 integriert. cAdvisor und die Container-Metriken sind mit #87 umgesetzt. Loki ist mit #89 als interner, persistenter Single-Binary-TSDB-Dienst umgesetzt. Alloy ist mit #90 als gehärteter systemd-Host-Agent für journald- und Docker-Logs umgesetzt. Grafana ist mit #88 als authentifizierter, persistenter und ausschließlich interner Containerdienst mit versionierten Datasources und Dashboard-Provisioning umgesetzt; Betriebsdashboards folgen separat mit #93. Alertmanager ist mit #91 als einzelner, gehärteter und persistenter Container unter `172.30.250.30:9093` umgesetzt. Prometheus liefert Alerts intern an `alertmanager:9093`; reale Benachrichtigungskanäle und kontrollierter Egress folgen mit #92. Leere Platzhalterstrukturen ohne Laufzeitwert werden vermieden.

## Datenfluss

Metriken:

```text
Node Exporter / cAdvisor / Traefik / Anwendungen / Blackbox
                         ↓
                    Prometheus
                         ↓
                    Alertmanager
                         ↓
                Notification Channels
```

Logs:

```text
journald + Docker local logs
            ↓
           Alloy
            ↓
           Loki
            ↓
          Grafana
```

## Sicherheitsgrenzen

- Grafana erhält keinen öffentlichen Edge-Ingress und ist zunächst nur per SSH-Tunnel, später per VPN erreichbar.
- Prometheus, Alertmanager, Loki und Blackbox Exporter bleiben intern.
- Node Exporter und cAdvisor sind nur für den Prometheus-Scrapepfad erreichbar.
- Alloy läuft als vertrauenswürdiger Host-Agent.
- cAdvisor läuft als explizit privilegierter Host-Agent und verwendet nur den lokalen Docker-Unix-Socket.
- Kein normaler Container erhält den rohen Docker-Socket.
- Docker TCP API bleibt deaktiviert.
- Secrets werden dateibasiert eingebunden.

## Alertmanager-Betrieb

Alertmanager besitzt keinen Host-Port, keinen DNS-Eintrag und keine Traefik-Route. Der Zugriff erfolgt zunächst bei Bedarf über einen lokalen SSH-Tunnel:

```powershell
ssh -N -L 9093:172.30.250.30:9093 BENUTZER@SERVER-IP
```

Danach ist die Oberfläche lokal unter `http://127.0.0.1:9093` erreichbar. Der Laufzeitprozess verwendet UID/GID `65534:65534`; Silences und Notification Log liegen persistent unter `/srv/merchfactory/persistent/monitoring/alertmanager`.

Die versionierte Konfiguration gruppiert nach Umgebung, Service, Alertname und Severity und enthält Inhibition für Critical- sowie Down/Unavailable-Alarme. Alle Receiver sind in #91 absichtlich Null-Receiver. Zugangsdaten, echte Empfänger und der dafür kontrollierte Outbound-Pfad gehören ausschließlich zu #92. Auf dem einzelnen VPS wird keine Alertmanager-HA vorgetäuscht.

## Healthchecks

Es gilt weiterhin die verbindliche Trennung aus `docs/54-healthcheck-standards.md`:

- Docker-/Prozess-Liveness,
- Service-Readiness,
- unabhängige External Probe.

Für kritische öffentliche Endpunkte muss mindestens ein Probe-Pfad außerhalb des überwachten Primärhosts existieren.

## Versionierung

Baseline-Versionen sind in `configuration/monitoring-stack.json` festgeschrieben.

Containerdeployment verwendet trotzdem ausschließlich vollständige SHA-256-Digests. Binaries der Host-Agenten müssen mit Upstream-Prüfsummen verifiziert werden.

## Abgrenzung

Betriebsdaten und Messwerte werden nicht versioniert.

Deploymentartefakte gehören nach `deployment/`, Host-Agent-Installation nach `ansible/`, maschinenlesbare globale Policy nach `configuration/`.

## Referenzen

- Epic #83
- Issue #84
- `docs/08-monitoring.md`
- `docs/54-healthcheck-standards.md`
- `docs/60-v0.5-review.md`
- `docs/61-monitoring-stack.md`
