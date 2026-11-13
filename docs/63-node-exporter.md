# Node Exporter – Hostmetriken

## Zweck

Dieses Dokument beschreibt die Node-Exporter-Implementierung aus Issue #86.

Node Exporter erfasst Hostmetriken für:

- CPU,
- Arbeitsspeicher,
- Dateisysteme und Inodes,
- Netzwerk,
- Boot-/Systemzustand,
- Systemzeit.

## Version und Herkunft

Baseline:

```text
Node Exporter 1.12.1
linux-amd64
```

Upstream-Artefakt:

```text
https://github.com/prometheus/node_exporter/releases/download/v1.12.1/node_exporter-1.12.1.linux-amd64.tar.gz
```

Verbindlicher SHA256:

```text
b51d8a76aa2a9156a55d501aca6276fae09e262259a5e4e831d2c2222f084e63
```

Die Prüfsumme stammt aus den offiziellen GitHub-Release-Asset-Metadaten und wird durch Ansible vor der Installation verifiziert.

Es wird kein ungepinnter EPEL-/Drittanbieter-Paketstand verwendet.

## Betriebsform

Node Exporter läuft als systemd Host-Agent.

Ansible-Rolle:

```text
ansible/roles/node_exporter/
```

Der Bootstrap führt die Rolle nach dem Docker-Runtime-Setup aus.

Systembenutzer:

```text
node_exporter
```

Binary:

```text
/usr/local/bin/node_exporter
```

Der Benutzer besitzt:

- kein Login-Shell,
- kein Home-Verzeichnis,
- keine sudo-Rechte,
- keine Linux-Capabilities.

## Netzwerk und Zugriffsschutz

### Monitoring-Netz

```text
Name:      merchfactory-monitoring
Subnetz:   172.30.250.0/24
Gateway:   172.30.250.1
Bridge:    mf-monitoring0
internal:  true
```

### Listener

Node Exporter lauscht ausschließlich auf:

```text
172.30.250.1:9100
```

Nicht verwendet werden:

```text
0.0.0.0:9100
[::]:9100
127.0.0.1:9100
```

Dadurch ist Port 9100 weder am öffentlichen Interface noch am normalen LAN-/Provider-Interface gebunden.

Die systemd-Unit ergänzt Defense in Depth:

```text
IPAddressDeny=any
IPAddressAllow=172.30.250.0/24
```

Port `9100/tcp` wird **nicht** in `firewall_allowed_ports` oder einem öffentlichen Rollenprofil geöffnet.

### Datenfluss

```text
Prometheus Container
       |
       | merchfactory-monitoring
       v
172.30.250.1:9100
       |
       v
Node Exporter systemd Host-Agent
```

Das ist der aktuell verbindliche Single-Primary-Host-Pfad. Ein späteres Multi-Host-Modell benötigt eine neue Netzwerkentscheidung, da das interne Docker-Netz bewusst keinen allgemeinen Egress bereitstellt.

## Prometheus-Scrape

Targetdefinition:

```text
monitoring/prometheus/targets/node-exporter.yml
```

Prometheus nutzt `file_sd`.

Job:

```text
node-exporter
```

Stabile Labels:

- `service=node-exporter`
- `component=host-metrics`

`environment` und `host` werden durch die Prometheus-`external_labels` des aktuellen Primärhosts ergänzt.

## Kernmetriken

Der Runtime-Test verlangt mindestens:

```text
node_cpu_seconds_total
node_memory_MemAvailable_bytes
node_filesystem_avail_bytes
node_network_receive_bytes_total
node_boot_time_seconds
node_time_seconds
```

Damit sind die DoD-Bereiche CPU, Speicher, Dateisystem, Netzwerk und Systemzustand direkt abgedeckt.

## Netzwerkmetriken und systemd-Sandbox

Node Exporter 1.12.1 verwendet für den `netdev`-Collector standardmäßig Netlink.

Die Merchfactory-systemd-Unit erlaubt absichtlich nur:

```text
AF_UNIX
AF_INET
AF_INET6
```

und gibt `AF_NETLINK` nicht frei. Damit Netzwerkzähler trotzdem zuverlässig erfasst werden, wird Node Exporter explizit mit:

```text
--collector.netdev.netlink=false
```

gestartet. Der `netdev`-Collector liest dadurch die Host-Netzwerkzähler aus:

```text
/proc/net/dev
```

Das erhält die bestehende systemd-Härtung und liefert weiterhin die benötigten Metriken wie `node_network_receive_bytes_total` und `node_network_transmit_bytes_total`.

Der Managed-Host-Test prüft zusätzlich, dass der `netdev`-Collector erfolgreich scrapt.

## Filesystem-Filter

Pseudo-/Container-Dateisysteme werden aus dem normalen Filesystem-Collector gefiltert, insbesondere:

- `/proc`,
- `/sys`,
- Docker-Layer unter `/var/lib/docker`,
- `overlay`,
- `tmpfs`,
- `devtmpfs`,
- weitere Kernel-/Pseudo-Filesystemtypen.

Das reduziert irrelevante Serien und verhindert unnötige Cardinality.

## Ressourcen

Systemd-Baseline:

```text
CPUQuota=25%
MemoryMax=128M
TasksMax=128
```

Diese Werte entsprechen ADR-0008 bzw. `configuration/monitoring-stack.json`.

## systemd-Hardening

Die Unit verwendet unter anderem:

- `NoNewPrivileges=yes`,
- `PrivateTmp=yes`,
- `ProtectHome=yes`,
- `ProtectSystem=strict`,
- `ProtectKernelTunables=yes`,
- `ProtectKernelModules=yes`,
- `ProtectControlGroups=yes`,
- leeres `CapabilityBoundingSet`,
- leere `AmbientCapabilities`,
- `RestrictSUIDSGID=yes`,
- `RestrictRealtime=yes`,
- begrenzte Address Families,
- IP-Subnetzfilter,
- CPU-/Memory-/Task-Limits.

Node Exporter benötigt keinen Docker-Socket.

## Alerts

Regeln:

```text
monitoring/prometheus/rules/node-exporter.yml
```

Enthalten:

- `NodeExporterDown`,
- `HostHighCPUUtilization`,
- `HostMemoryPressure`,
- `HostFilesystemSpaceLow` (75–85 % Belegung: warning, nach 15 Minuten),
- `HostFilesystemSpaceCritical` (>85 % Belegung: high, nach 5 Minuten),
- `HostFilesystemInodesLow`,
- `HostNetworkErrors`,
- `HostClockSkew`.

Alertmanager-Zustellung folgt mit #91. Die Regeln werden bereits jetzt von Prometheus ausgewertet.

## Alert-Tests

Promtool-Testdefinition:

```text
monitoring/prometheus/rules/tests/node-exporter.test.yml
```

Der Test prüft synthetisch das Auslöseverhalten für:

- Down,
- CPU,
- Memory,
- Filesystem Space,
- Inodes,
- Network Errors,
- Clock Skew.

## Ansible-Deployment

Der reguläre Bootstrap installiert Node Exporter automatisch:

```bash
ansible-playbook \
  -i <inventory> \
  ansible/playbooks/bootstrap.yml
```

Die Rolle:

1. validiert Version, SHA und Netzwerkparameter,
2. legt Benutzer/Gruppe an,
3. stellt das interne Monitoring-Netz sicher,
4. lädt das gepinnte Release herunter,
5. verifiziert SHA256,
6. installiert die Binary,
7. installiert die gehärtete systemd-Unit,
8. startet und aktiviert den Dienst,
9. prüft Listener und Kernmetriken.

Der zweite Bootstrap-Lauf muss weiterhin `changed=0` liefern.

## Update

Ein Versionsupdate benötigt einen PR mit:

1. neuer exakter Version,
2. neuer offizieller Release-URL,
3. neuer offizieller SHA256-Prüfsumme,
4. Runtime-Test,
5. Alert-/Prometheus-Regressionstests.

Es wird kein bewegliches `latest` verwendet.

## CI-Nachweis

`tests/integration/test-node-exporter.sh` führt auf einem echten Linux-Runner aus:

1. offizielles Release herunterladen,
2. SHA256 verifizieren,
3. internes Test-Monitoring-Netz mit fester Gateway-IP erstellen,
4. Node Exporter ausschließlich an diese Gateway-IP binden,
5. Kernmetriken und erfolgreichen `netdev`-Collector mit Procfs-Fallback prüfen,
6. bestätigen, dass `127.0.0.1:9100` nicht erreichbar ist,
7. Scrape aus einem Container im internen Netz prüfen,
8. Alertregeln mit `promtool check rules` prüfen,
9. alle zentralen Alerts mit `promtool test rules` auslösen.

Zusätzlich prüft der Bootstrap-Validation-Workflow die Ansible-Syntax. Ein freigegebener Fresh-/Managed-Host-Test bestätigt später die tatsächliche systemd-Unit auf EL9.

## Referenzen

- Issue #86
- Epic #83
- ADR-0008
- `docs/61-monitoring-stack.md`
- `docs/62-prometheus.md`
- `configuration/monitoring-stack.json`
