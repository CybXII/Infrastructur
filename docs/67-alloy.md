# Grafana Alloy

## Zweck

Issue #90 integriert Grafana Alloy 1.19.2 als zentralen Host-Logcollector der v0.6 Plattform.

Alloy sammelt:

- journald-/Systemlogs,
- Docker-Containerlogs über den lokalen Unix-Socket,
- eigene Prozess- und Pipeline-Metriken.

Die Logs werden ausschließlich an den internen Loki-Dienst gesendet.

## Release und Installation

Artefakt:

```text
https://github.com/grafana/alloy/releases/download/v1.19.2/alloy-linux-amd64.zip
```

SHA-256:

```text
3694ea4e1044b367e1c21ffe28117f209c5989fa5e604d000321809f871ab701
```

Installation:

```text
/usr/local/bin/alloy
/etc/alloy/config.alloy
/var/lib/merchfactory/alloy
```

Das Release-Artefakt wird vor der Installation per SHA-256 geprüft.

## Host-Agent-Vertrauensgrenze

Alloy ist kein normaler Plattformcontainer. Er läuft als systemd-Host-Agent unter dem dedizierten Benutzer `alloy`.

Zusätzliche Gruppen:

```text
docker
systemd-journal
adm
merchfactory-runtime
```

Der Zugriff auf die Gruppe `docker` ist sicherheitsrelevant: Docker-Socket-Zugriff entspricht faktisch einer hochprivilegierten Hostrolle. Diese Ausnahme ist in ADR-0008 ausdrücklich akzeptiert.

Nicht erlaubt:

- Docker TCP API,
- öffentlicher Alloy-Port,
- roher Docker-Socket in Standardcontainern,
- Secrets als Loglabels.

## Netzwerk

Alloy Self-Metrics/UI lauschen ausschließlich auf:

```text
172.30.250.1:12345
```

Loki erhält die reservierte Monitoring-IP:

```text
172.30.250.10:3100
```

Alloy schreibt an:

```text
http://172.30.250.10:3100/loki/api/v1/push
```

Die systemd-Sandbox erlaubt IP-Kommunikation nur innerhalb des Monitoring-Subnetzes `172.30.250.0/24`.

## Persistenter State

```text
/var/lib/merchfactory/alloy
```

Dieser Pfad hält den Alloy-Komponentenstate und Logpositionen über Neustarts hinweg. Der übergeordnete Runtime-Root `/var/lib/merchfactory` bleibt `0750` und gehört `root:merchfactory-runtime`; Alloy erhält den notwendigen Traverse-Zugriff ausschließlich über diese dedizierte Systemgruppe.

## Docker-Logs

Alloy verwendet ausschließlich:

```text
unix:///var/run/docker.sock
```

Docker-Discovery-Metadaten werden auf wenige stabile Labels reduziert. Compose-Service und -Projekt sowie der Containername dürfen als begrenzte Labels übernommen werden; Container-IDs werden nicht als Loki-Indexlabel verwendet.

Pflichtlabels bleiben:

```text
environment
host
service
component
```

## journald

Alloy liest das lokale systemd-Journal. Der Servicebenutzer erhält dafür ausschließlich die erforderlichen Gruppen `adm` und `systemd-journal`.

Journal-Logs erhalten zusätzlich das stabile Label `unit`.

## Self-Monitoring

Prometheus scrapt später:

```text
172.30.250.1:12345/metrics
```

Die Alloy-eigenen Loki-Write-Metriken bilden die Basis für Write-Retry- und Drop-Alerts.

## systemd-Hardening

Die Unit setzt unter anderem:

- `NoNewPrivileges=yes`
- `PrivateTmp=yes`
- `PrivateDevices=yes`
- `ProtectSystem=strict`
- `ProtectHome=yes`
- `WorkingDirectory=/var/lib/merchfactory/alloy`
- Journalpfade explizit read-only
- `ProtectKernelTunables=yes`
- `ProtectKernelModules=yes`
- `ProtectKernelLogs=yes`
- `ProtectControlGroups=yes`
- leeres Capability Bounding Set
- `IPAddressDeny=any`
- `IPAddressAllow=172.30.250.0/24`
- `CPUQuota=50%`
- `MemoryMax=512M`
- `TasksMax=256`
- `MemoryDenyWriteExecute=no` bewusst für den offiziellen Alloy-Build

Der einzige beschreibbare systemd-Pfad ist der Alloy-State. Die W^X-Sperre
`MemoryDenyWriteExecute=yes` wird nicht verwendet, weil offizielle Alloy-Builds
ausführbare Runtime-Mappings benötigen. Die übrige systemd-Sandbox bleibt aktiv.

Vor dem Service-Start prüft Ansible als Benutzer `alloy`, dass der persistente State-Pfad tatsächlich erreichbar und beschreibbar ist.

Bei einem Start- oder Metrics-Fehler erfasst Ansible automatisch `systemctl status` und die letzten 100 Journalzeilen des Alloy-Dienstes, bevor der Bootstrap fehlschlägt.

## Datenschutz und Kardinalität

Verbotene High-Cardinality-Labels bleiben:

- Request-ID,
- Order-ID,
- User-ID,
- E-Mail-Adresse,
- dynamische URL,
- Stacktrace,
- freie Meldung.

Diese Inhalte dürfen nicht zu Loki-Indexlabels gemacht werden.

## Validierung

Vor Merge werden Release-Checksum, Policy und Alloy-Konfiguration geprüft. Der Runtime-Test muss Docker- und Journal-Log-Ingest bis Loki, persistenten State sowie Self-Metrics nachweisen.

Nach Merge prüft der Managed-Host-Bootstrap zusätzlich:

- systemd-Dienst aktiv,
- Docker-Socket als Alloy-Benutzer nutzbar,
- Journalzugriff als Alloy-Benutzer,
- Listener nur am Monitoring-Gateway,
- Self-Metrics erreichbar.

## Referenzen

- Epic #83
- Issue #90
- ADR-0008
- `configuration/monitoring-stack.json`
- `configuration/logging-policy.json`
- `docs/61-monitoring-stack.md`
- `docs/65-loki.md`
- https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.docker/
- https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.journal/
