# Ressourcenlimits für Container

## Zweck

Dieses Dokument definiert die verbindlichen CPU-, Speicher- und Prozessgrenzen für containerisierte Merchfactory-Dienste. Es setzt Issue #77 um und ergänzt die Compose-, Monitoring- und Service-Template-Standards.

Ziel ist, dass ein einzelner fehlerhafter oder überlasteter Container nicht unkontrolliert CPU, RAM oder Prozessslots des Hosts verbraucht.

## Grundprinzip

Jeder dauerhaft laufende Container erhält:

- ein hartes CPU-Limit,
- ein hartes Memory-Limit,
- eine Memory-Reservation als Soft-Limit,
- ein PID-Limit,
- eine relative CPU-Priorität über `cpu_shares`.

Unbegrenzte Standard-Services sind nicht zulässig.

## Standardprofil

Ausgangspunkt für einen normalen Service:

```text
cpus: 1.0
memory limit: 512 MiB
memory reservation: 256 MiB
pids limit: 256
cpu shares: 512
```

Diese Werte sind eine sichere Plattform-Baseline, keine universelle Produktionsdimensionierung.

Vor Production müssen Dienste mit realistischen Lastprofilen geprüft werden. Datenbanken, Odoo-Worker, Rendering-, Import- oder andere speicherintensive Prozesse erhalten servicebezogen angepasste Grenzen.

## Prioritätsklassen

Die Plattform trennt Priorität von harter Kapazität.

### Critical

```text
cpu_shares: 1024
```

Geeignet für Reverse Proxy, zentrale Infrastrukturkomponenten und geschäftskritische request-serving Services.

### Standard

```text
cpu_shares: 512
```

Normale dauerhaft laufende Anwendungen.

### Background

```text
cpu_shares: 256
```

Geeignet für Worker, Batch-Jobs und zeitunkritische Verarbeitung.

`cpu_shares` ist eine relative Gewichtung und wirkt vor allem bei CPU-Konkurrenz. Es ist keine garantierte CPU-Reservation.

## CPU

`cpus` ist das harte CPU-Zeit-Limit.

```yaml
cpus: 1.0
cpu_shares: 512
```

Ein Dienst darf unter freier Hostkapazität bis zu seinem `cpus`-Limit arbeiten. Unter Konkurrenz verteilt der Scheduler CPU-Zeit zusätzlich relativ anhand von `cpu_shares`.

Kritische Dienste erhalten nicht automatisch unbegrenzt CPU.

## Speicher

Jeder Service definiert:

```yaml
mem_limit: 512m
mem_reservation: 256m
```

`mem_limit` ist die harte Obergrenze. `mem_reservation` ist eine kleinere weiche Zielgrenze unter Host-Speicherdruck und keine garantierte Reservation.

Überschreitet ein Container seine cgroup-Speichergrenze dauerhaft, darf der Kernel Prozesse innerhalb des Containers per OOM-Killer beenden. Dieses Verhalten ist gewollt: Ein einzelner Container soll eher beendet werden als den gesamten Host in einen systemweiten OOM-Zustand zu bringen.

`oom_kill_disable: true` ist in der Plattform-Baseline verboten.

## PIDs

Jeder Service erhält ein `pids_limit`.

Standard:

```text
256
```

Damit werden unkontrollierte Prozess-/Thread-Explosionen begrenzt. `-1` beziehungsweise unbegrenzte PIDs sind für Standard-Services nicht zulässig.

## Traefik

Traefik wird als kritischer Plattformdienst klassifiziert:

```text
cpus: 1.0
memory limit: 512 MiB
memory reservation: 256 MiB
pids limit: 128
cpu shares: 1024
```

Der höhere CPU-Share-Wert priorisiert Ingress bei Host-CPU-Konkurrenz, ohne Traefik unbegrenzte CPU zu geben.

## Host-Headroom

Containerlimits dürfen nicht so dimensioniert werden, dass der Host nur dann stabil bleibt, wenn nie mehrere Container gleichzeitig ihre Limits erreichen.

Es müssen Reserven verbleiben für Kernel, Docker Engine/containerd, SSH, Monitoring, Backup, Dateisystemcache und ungeplante Lastspitzen.

## OOM-Verhalten

Bei einem containerlokalen OOM gilt:

1. Containerstatus und `OOMKilled` prüfen.
2. Hostzustand und andere Container prüfen.
3. keine automatische pauschale Erhöhung des Limits.
4. Ursache bestimmen: Leak, Lastspitze, fehlerhafte Parallelität oder zu knappe Dimensionierung.
5. erst nach Messung Limit oder Anwendung anpassen.

Ein OOM ist ein Betriebsereignis und muss überwacht werden.

## Überlastungsverhalten

### CPU

CPU-Überlast führt zur cgroup-basierten Drosselung am gesetzten CPU-Limit. Kritische Container erhalten unter Konkurrenz über `cpu_shares` ein höheres relatives Gewicht.

### Speicher

Memory-Überlast wird durch das harte Limit auf den Container begrenzt. Der OOM-Killer bleibt aktiv.

### Prozesse

Erreicht ein Container sein PID-Limit, schlägt das Erzeugen weiterer Prozesse oder Threads fehl. Der Host bleibt außerhalb dieses cgroup-Limits verfügbar.

## Monitoring

Zu überwachen sind mindestens CPU-Nutzung relativ zum Limit, CPU-Throttling, Memory-Nutzung relativ zu Reservation und Limit, OOM-Ereignisse/`OOMKilled`, Restart-Zähler nach OOM und PID-Nutzung relativ zum Limit.

Wiederkehrendes Erreichen von Limits ist kein Normalzustand und benötigt Ursachenanalyse oder Kapazitätsanpassung.

## Ausnahmen

Abweichungen vom Standardprofil sind erlaubt, wenn sie fachlich begründet sind. Erforderlich sind Service-Owner, gemessener oder plausibel abgeleiteter Bedarf, dokumentierte Werte, Last-/Smoke-Test und Bewertung des Host-Headrooms.

Verboten bleiben ohne separate Architektur-/Security-Entscheidung:

- kein Memory-Limit,
- kein CPU-Limit,
- unbegrenzte PIDs,
- deaktivierter OOM-Killer.

## Service-Template

Das Standard-Service-Template verwendet sichtbare Defaults:

```text
SERVICE_CPU_LIMIT=1.0
SERVICE_CPU_SHARES=512
SERVICE_MEMORY_LIMIT=512m
SERVICE_MEMORY_RESERVATION=256m
SERVICE_PIDS_LIMIT=256
```

Die Werte können service- oder umgebungsbezogen überschrieben werden.

## Tests

Die CI prüft zwei Ebenen.

### Policy-/Manifestprüfung

- CPU-, Memory- und PID-Limits vorhanden,
- Memory-Reservation kleiner als Hard Limit,
- `oom_kill_disable` nicht aktiviert,
- Template und zentrale Policy synchron.

### Runtime-Stresstest

Ein kurzlebiges lokales Testimage wird ohne externe Basis aus einem statisch gebauten Testprogramm erzeugt.

Geprüft werden:

- Docker übernimmt CPU-, Memory-, Reservation- und PID-Limits,
- PID-Druck wird am Containerlimit abgefangen,
- absichtliche Memory-Überlast endet mit containerlokalem `OOMKilled=true`,
- Docker bleibt danach erreichbar.

Der Test belastet ausschließlich einen stark begrenzten Testcontainer.

## Odoo-Ausblick

Für Odoo und PostgreSQL werden die endgültigen Limits erst anhand der tatsächlichen Architektur festgelegt. Insbesondere getrennt zu dimensionieren sind Odoo Web-/HTTP-Prozesse, Worker, Cron, PostgreSQL, eventuell Redis/Queues sowie Import-/ETL-Dienste.

Die Standardwerte dieses Dokuments dürfen nicht ungeprüft als produktive Odoo-Sizingwerte übernommen werden.

## Referenzen

- `configuration/resource-policy.json`
- `docs/08-monitoring.md`
- `docs/48-docker-compose-standards.md`
- `docs/53-standard-service-template.md`
