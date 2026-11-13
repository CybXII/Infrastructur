# cAdvisor – Container-Metriken

## Zweck

Dieses Dokument beschreibt die cAdvisor-Implementierung aus Issue #87.

cAdvisor ergänzt Node Exporter um die Sicht auf einzelne Docker-Container und deckt die Definition of Done für:

- CPU,
- RAM,
- Netzwerk,
- Neustarts,
- konsistente Container-Labels und Namen

ab.

## Version und Herkunft

Baseline:

```text
cAdvisor 0.60.5
linux-amd64
```

Offizielles Upstream-Artefakt:

```text
https://github.com/google/cadvisor/releases/download/v0.60.5/cadvisor-v0.60.5-linux-amd64
```

Verbindlicher SHA256:

```text
6f258bed28113218c88729634c47ead8d928b81b1504b75fd911b98d29003a87
```

Ansible und der Runtime-Test prüfen denselben Wert.

## Betriebsform und Trust Boundary

cAdvisor läuft als systemd Host-Agent, nicht als normaler Docker-Container.

Der Agent benötigt lokale Sicht auf Docker und cgroups. Deshalb läuft er bewusst als `root` und greift auf:

```text
unix:///var/run/docker.sock
```

zu.

Der Docker-Socket ist funktional eine hochprivilegierte Host-Schnittstelle. cAdvisor wird daher als explizit vertrauenswürdiger Host-Agent behandelt. Diese Ausnahme ändert nicht die allgemeine Plattformregel: normale Monitoring- und Anwendungscontainer erhalten keinen rohen Docker-Socket und die Docker TCP API bleibt deaktiviert.

## Netzwerk

Monitoring-Netz:

```text
Name:      merchfactory-monitoring
Subnetz:   172.30.250.0/24
Gateway:   172.30.250.1
Bridge:    mf-monitoring0
internal:  true
```

Listener:

```text
172.30.250.1:8080
```

Nicht zulässig:

```text
0.0.0.0:8080
[::]:8080
öffentliche Traefik-Route
öffentliche firewalld-Freigabe
```

Die systemd-Unit ergänzt:

```text
IPAddressDeny=any
IPAddressAllow=172.30.250.0/24
```

## Label- und Namensmodell

cAdvisor wird mit:

```text
--store_container_labels=false
```

betrieben.

Freigegebene Docker-Labels:

- `com.merchfactory.managed`
- `com.merchfactory.cleanup.protect`
- `com.docker.compose.project`
- `com.docker.compose.service`

Dadurch bleiben betriebliche Zuordnung und Compose-Namen erhalten, ohne beliebige Anwendungslabels in die Prometheus-Cardinality zu übernehmen. Die nativen cAdvisor-Labels `name`, `image` und `id` bleiben ebenfalls verfügbar.

## Kernmetriken

Die Implementierung verlangt mindestens:

```text
container_cpu_usage_seconds_total
container_memory_working_set_bytes
container_network_receive_bytes_total
container_network_transmit_bytes_total
container_start_time_seconds
```

## Metrikprofile und Wiederherstellung

Die Baseline aus #341 deaktiviert `disk` und `diskIO` zusätzlich zu den Upstream-Defaults:

```yaml
cadvisor_disable_metrics: "advtcp,cpu_topology,cpuset,disk,diskIO,hugetlb,memory_numa,process,referenced_memory,resctrl,sched,tcp,udp"
```

Damit fehlen Container-Filesystem-Nutzung, Inodes und Disk-I/O. CPU, RAM, Netzwerk und Startzeit bleiben erhalten. Die aufwendige OverlayFS-Verzeichnisermittlung soll dadurch entfallen; eine gemessene Entlastung auf dem Zielhost ist noch nachzuweisen. Host-Storage bleibt über Node Exporter sichtbar. Die Recording Rule `container:filesystem_usage_bytes` wurde entfernt; externe Dashboards oder Abfragen benötigen eine gesonderte Prüfung.

Für die bisherige Filesystem-Erfassung ist ausschließlich der zweite unterstützte Wert vorgesehen:

```yaml
cadvisor_disable_metrics: ""
```

Die Unit lässt dann `--disable_metrics` weg und verwendet die [Upstream-Defaults von v0.60.5](https://github.com/google/cadvisor/blob/v0.60.5/docs/runtime_options.md#metrics). Ein explizites leeres CLI-Flag hätte eine andere Bedeutung und wird nicht erzeugt. Die Einstellung stellt die Erfassung einschließlich ihrer möglichen I/O-Last wieder her, aber keine entfernte Recording Rule. Aktivierung und Rollback erfordern eine freigegebene Anwendung der Rolle mit Dienstneustart; Datenmigrationen sind nicht nötig. Es entstehen keine zusätzlichen Ressourcen oder Lizenzkosten.

## Neustarts

cAdvisor liefert keinen stabilen allgemeinen Docker-`restart_count` als Kernmetrik.

Neustarts werden deshalb aus der Änderung von:

```text
container_start_time_seconds
```

abgeleitet.

Prometheus stellt dafür die Recording Rule:

```text
container:restarts:15m
```

bereit.

## Prometheus

Target:

```text
monitoring/prometheus/targets/cadvisor.yml
```

Scrape-Job:

```text
cadvisor
```

Stabile Target-Labels:

- `service=cadvisor`
- `component=container-metrics`

Recording Rules:

```text
monitoring/prometheus/rules/cadvisor.yml
```

Sie normalisieren CPU, RAM, Netzwerk, Startzeit und Neustarts für spätere Dashboards aus #93.

Zusätzlich existiert `CAdvisorDown`. Die externe Zustellung folgt mit Alertmanager in #91.

## Ressourcen

Baseline:

```text
CPUQuota=50%
MemoryMax=1028M
TasksMax=256
```

#96 überprüft diese Werte später anhand realer Cardinality, Ingestion und Hostlast.

## systemd-Hardening

Die Unit verwendet unter anderem:

- `NoNewPrivileges=yes`,
- `PrivateTmp=yes`,
- `ProtectHome=yes`,
- `ProtectSystem=strict`,
- `ProtectKernelTunables=yes`,
- `ProtectKernelModules=yes`,
- `ProtectControlGroups=yes`,
- begrenzte Address Families,
- IP-Subnetzfilter,
- CPU-/Memory-/Task-Limits.

Da der lokale Docker-Socket selbst eine privilegierte Schnittstelle darstellt, ersetzt dieses Hardening keine Trust-Grenze. Der Agent bleibt Teil des privilegierten Host-Scopes.

## Ansible

Rolle:

```text
ansible/roles/cadvisor/
```

Der Bootstrap führt sie nach Node Exporter und nach dem Docker-Runtime-Setup aus.

Die Rolle:

1. validiert Version, SHA, Netzwerk und Docker-Endpunkt,
2. prüft den lokalen Docker-Socket,
3. stellt das interne Monitoring-Netz sicher,
4. lädt die gepinnte Binary,
5. verifiziert SHA256,
6. installiert die systemd-Unit,
7. aktiviert und startet cAdvisor,
8. prüft Listener und Kernmetriken.

## CI-Nachweis

`tests/integration/test-cadvisor.sh`:

1. lädt die echte Upstream-Binary,
2. prüft SHA256,
3. erstellt ein isoliertes Monitoring-Netz,
4. startet einen Docker-Testcontainer,
5. startet cAdvisor nur am Test-Gateway,
6. prüft CPU/RAM/Netzwerk/Startzeit und die profilabhängige Filesystem-Erwartung,
7. prüft die Label-Allowlist,
8. startet den Testcontainer neu und bestätigt die Startzeitänderung,
9. scrapt cAdvisor aus dem internen Docker-Netz,
10. validiert die Prometheus-Rules mit `promtool`.

Der Integrationstest verwendet standardmaessig das `lean`-Profil; `CADVISOR_METRICS_PROFILE=filesystem` prueft das Upstream-Profil in einem separaten Lauf. Unit-Tests pruefen die Profile und rendern die systemd-Unit bei vorhandenem Jinja2. Statische Tests belegen keine Zielhost-Entlastung oder Runtime-Kompatibilitaet. Nach einer freigegebenen Anwendung sind Scrape, Kernmetriken, Journal, CPU/RAM und I/O-Druck zu pruefen.

Es wird kein zusätzlicher GitHub-Actions-Runner-Job eingeführt. Der Test nutzt den bestehenden Job `Prometheus deployment`.

## Referenzen

- Issue #87
- Epic #83
- Issue #86
- Issue #91
- Issue #93
- Issue #96
- ADR-0008
- `docs/61-monitoring-stack.md`
- `docs/62-prometheus.md`
- `configuration/monitoring-stack.json`
