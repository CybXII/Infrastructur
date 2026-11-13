# Docker- und Compose-Standards

## Zweck

Dieses Dokument definiert die verbindliche Baseline für containerisierte Dienste der Merchfactory Infrastructure Platform ab v0.5. Die Standards gelten für Compose-basierte Services, die über dieses Repository oder nachgelagerte Applikations-Repositories auf der Plattform betrieben werden.

Die Regeln ergänzen die in v0.4 bereitgestellte Docker-Runtime. Sie definieren den Service- und Deployment-Vertrag; Reverse Proxy, TLS, Netzwerksegmentierung, Persistenz, Secrets, Registry-Strategie und Rollback werden in den nachfolgenden v0.5-Issues weiter konkretisiert.

## Verbindliches Projektlayout

Ein Service folgt grundsätzlich diesem Layout:

```text
<service>/
├── configuration/
│   ├── service.yaml
│   └── secrets.yaml
├── deployment/
│   └── compose.yaml
├── routing/
│   └── route.yaml
├── monitoring/
│   └── healthcheck.yaml
├── logging/
│   └── policy.yaml
├── backup/
│   └── policy.yaml
├── operations/
│   └── runbook.md
├── tests/
└── README.md
```

Die verbindliche Ausgangsvorlage liegt unter `templates/services/container-service/` und wird mit `scripts/render-service-template.py` erzeugt. `examples/services/example-service/` bleibt eine vereinfachte Referenz. Details stehen in `docs/53-standard-service-template.md`.

Applikations-Repositories dürfen zusätzliche Verzeichnisse besitzen, sollen die grundlegende Trennung zwischen Deployment, Konfiguration, Routing, Monitoring, Logging, Backup, Operations und Tests aber beibehalten.

## Compose-Datei

Für neue Stacks wird `compose.yaml` verwendet. Das veraltete Top-Level-Feld `version` wird nicht verwendet.

Ein Stack muss einen expliziten Projektnamen über Deployment-Konvention oder CLI erhalten. `container_name` ist nicht zulässig, weil feste Containernamen Skalierung, parallele Umgebungen und Compose-eigene Namensräume behindern.

## Image-Pinning

Deployments konsumieren vorgebaute Images. Ein produktionsnahes Compose-Manifest verwendet deshalb kein `build:`, sondern eine explizite `image:`-Referenz.

Für die Plattform-Baseline gilt:

- Image-Referenzen werden unveränderlich über einen SHA-256-Digest gepinnt.
- Registry und Repository werden vollständig ausgeschrieben; implizite Docker-Hub-Kurzformen sind nicht zulässig.
- `:latest`, bewegliche Major-/Minor-Tags und rein tagbasierte Deployments sind nicht zulässig.
- Eigene Images liegen unter `ghcr.io/merchfactory/...`.
- Drittanbieter-Repositories sind Default-Deny und müssen in `configuration/container-image-policy.json` explizit allowgelistet sein.
- First-Party-Images benötigen eine verifizierbare Build-Provenance gemäß `docs/52-container-registry-security.md`.
- Image-Scans folgen den dort definierten Reporting- und Blocking-Gates.
- Der lesbare Release-Tag darf zusätzlich in Release-Metadaten dokumentiert werden; der laufende Sollzustand wird durch den Digest bestimmt.

Beispiel:

```yaml
image: ghcr.io/merchfactory/example-service@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

## Plattform-Management-Label

Jeder Standard-Service muss eindeutig als von der Merchfactory Container Platform verwaltet markiert sein:

```yaml
labels:
  com.merchfactory.managed: "true"
  com.merchfactory.cleanup.protect: "false"
```

Das Label `com.merchfactory.managed=true` ist Voraussetzung dafür, dass ein gestoppter Container später durch das kontrollierte Retention-Cleanup aus `docs/59-docker-retention-cleanup.md` berücksichtigt werden darf.

`com.merchfactory.cleanup.protect=true` schützt einen Container ausdrücklich vor automatischer Entfernung.

## Restart-Policy

Standard ist:

```yaml
restart: unless-stopped
```

Damit startet ein Service nach Host- oder Docker-Neustarts wieder, bleibt aber bewusst gestoppt, wenn ein Operator ihn explizit angehalten hat.

Abweichungen müssen im Service-README begründet werden. `restart: "no"` ist nur für bewusst einmalige Jobs zulässig und fällt nicht unter das Standard-Serviceprofil.

## Security-Baseline

Jeder dauerhaft laufende Service muss mindestens folgende Compose-Einstellungen besitzen:

```yaml
read_only: true
cap_drop:
  - ALL
security_opt:
  - no-new-privileges:true
```

Zusätzlich gilt:

- `privileged: true` ist verboten.
- `network_mode: host` ist verboten.
- Zusätzliche Linux-Capabilities dürfen nur explizit und begründet über `cap_add` freigegeben werden.
- Schreibbare Laufzeitpfade werden gezielt über Volumes oder `tmpfs` bereitgestellt.
- Der Docker-Socket wird nicht standardmäßig in Anwendungscontainer gemountet.
- Container laufen nach Möglichkeit mit einem nicht privilegierten Benutzer. Ob ein konkretes Image hierfür geeignet ist, wird servicebezogen geprüft.
- Host-Geräte, PID-/IPC-Namespaces und andere privilegierte Host-Schnittstellen sind keine Standardfreigaben.

## Netzwerk und Portfreigaben

Das verbindliche Netzwerkmodell ist in `docs/49-docker-network-model.md` beschrieben.

Für Standard-Services gilt:

- öffentliche Erreichbarkeit ausschließlich über Traefik und das gemeinsame externe `edge`-Netz,
- stack-lokale `app`- und `data`-Netze werden mit `internal: true` definiert,
- Datenbanken und Caches werden nicht an `edge` angeschlossen,
- Anwendungsdienste veröffentlichen keine direkten Host-Ports,
- administrative Ports bleiben an Loopback gebunden.

Direkte Host-Portfreigaben sind nur für Plattformkomponenten oder begründete Ausnahmen zulässig. Öffentliche Bindings müssen mit Host-Firewall und gegebenenfalls Provider-Firewall abgestimmt werden.

## Healthcheck

Das verbindliche Healthcheck-Modell ist in `docs/54-healthcheck-standards.md` beschrieben.

Jeder dauerhaft laufende Service benötigt einen aktiven Compose-Liveness-Check mit:

- `test`,
- `interval`,
- `timeout`,
- `retries`,
- `start_period`.

Standard:

```yaml
healthcheck:
  test: ["CMD-SHELL", "<lokaler Liveness-Befehl>"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

Liveness prüft den lokalen Prozess und darf keine optionalen Remote-Abhängigkeiten in einen Neustart-/Fehlerpfad koppeln.

Öffentlich geroutete HTTP-Dienste verwenden zusätzlich einen Traefik-Readiness-Check mit `10s` Intervall, `3s` Timeout und erwartetem HTTP 200. Externe Probes bleiben ein drittes unabhängiges Signal.

Ein Docker-`unhealthy`-Status führt nicht automatisch zu einem Container-Neustart.

## Ressourcen und Logging

Das verbindliche Ressourcenmodell ist in `docs/55-container-resource-limits.md` definiert.

Jeder dauerhaft laufende Standard-Service benötigt mindestens:

```yaml
cpus: 1.0
cpu_shares: 512
mem_limit: 512m
mem_reservation: 256m
pids_limit: 256
```

Die Werte sind Baseline-Defaults und dürfen servicebezogen angepasst werden. Dabei gilt:

- `cpus` bleibt ein hartes CPU-Limit,
- `cpu_shares` priorisiert relativ unter CPU-Konkurrenz,
- `mem_reservation` muss kleiner als `mem_limit` sein,
- `pids_limit` muss positiv und begrenzt sein,
- `oom_kill_disable: true` ist nicht zulässig.

Kritische Dienste verwenden standardmäßig ein höheres CPU-Gewicht; Hintergrunddienste ein niedrigeres. Absolute Produktionswerte benötigen Lastvalidierung und ausreichenden Host-Headroom.

Das verbindliche Logging-/Rotationsmodell steht in `docs/56-log-rotation.md`.

Standard-Services:

- schreiben Anwendungslogs nach stdout/stderr,
- erben den Docker-`local`-Driver,
- verwenden global `20m × 5` mit Kompression,
- dürfen keinen servicebezogenen `logging:`-Override definieren,
- schreiben keine unkontrollierten Anwendungslogdateien in den Container-Layer.

Damit kann ein einzelner Stack die hostweite Rotationsgrenze nicht unbemerkt umgehen.

## Persistenz und Secrets

Das verbindliche Persistenzmodell ist in `docs/50-volume-persistence-model.md` beschrieben.

Für Standard-Services gilt:

- persistente Daten gehören nicht in den Container-Layer,
- backup- und migrationsrelevante Dateidaten verwenden bevorzugt explizite Bind Mounts unter `/srv/merchfactory/persistent/<service>/...`,
- anonyme Volumes sind nicht zulässig,
- Named Volumes benötigen eine dokumentierte Datenklasse sowie Backup-/Restore-Zuordnung,
- direkte Zugriffe auf `/var/lib/docker/volumes` sind kein unterstützter Backup- oder Migrationsweg,
- temporäre Daten verwenden bevorzugt `tmpfs` oder `/var/tmp/merchfactory`,
- effektive UID/GID und benötigte Rechte persistenter Daten werden servicebezogen dokumentiert.

Das verbindliche Secret-Modell ist in `docs/51-secret-management.md` beschrieben.

Für Standard-Services gilt:

- Secret-Werte werden nicht in Compose-Dateien committed,
- produktive Secrets werden nicht als normale Environment-Variablen injiziert,
- file-basierte Compose-Secrets verweisen auf geschützte Hostdateien unter `/srv/merchfactory/secrets/<service>/...`,
- Services erhalten nur die explizit benötigten Secrets,
- Anwendungen lesen Secrets über `/run/secrets/<name>` oder eine unterstützte `*_FILE`-Konvention,
- Ownership und Mode der Quelldatei werden hostseitig vorbereitet,
- `.env`-Dateien mit echten Secrets bleiben aus Git ausgeschlossen.

## Automatische Validierung

Die Referenz-Compose-Datei wird über `scripts/validate-compose-standards.py` validiert.

Die Prüfung umfasst derzeit:

1. syntaktische Compose-Validierung über `docker compose config`,
2. unveränderliches Image-Pinning per SHA-256-Digest,
3. explizite Registry- und Repositorynamen,
4. First-Party-Namespace bzw. exakte Drittanbieter-Allowlist,
5. Verbot von `build`, `container_name`, `privileged` und Host-Netzwerk,
6. `restart: unless-stopped`,
7. read-only Root-Dateisystem,
8. `cap_drop: ALL`,
9. `no-new-privileges:true`,
10. vorhandenen Healthcheck,
11. CPU-, Memory- und PID-Limits,
12. Memory-Reservation unterhalb des Hard Limits,
13. aktiven OOM-Killer,
14. keinen servicebezogenen Logging-Override,
15. `com.merchfactory.managed=true`,
16. keine offensichtlich globale Host-Port-Bindung im Referenzprofil.

Die Repository Tests führen diese Prüfung bei Pull Requests und Pushes auf den permanenten Branches aus.

## Ausnahmen

Eine Abweichung von der Baseline ist nur zulässig, wenn:

1. sie technisch erforderlich ist,
2. die zusätzliche Vertrauensgrenze und das Risiko dokumentiert sind,
3. die Ausnahme im Service-README begründet ist,
4. passende Tests vorhanden sind,
5. die Änderung den normalen Review- und Promotion-Prozess durchläuft.

Sicherheitskritische Ausnahmen wie `privileged`, Docker-Socket-Mounts oder Host-Netzwerk gelten nicht als normale Konfigurationsabweichung und benötigen eine separate Architektur-/Security-Entscheidung.

## v0.5-Status

Die in diesem Dokument referenzierten v0.5-Verträge für Routing, TLS, Netzwerkmodell, Persistenz, Secrets, Registry, Healthchecks, Ressourcen, Logging, Update/Rollback und Docker-Retention sind umgesetzt und automatisiert validiert.

Der formale Milestone-Abschluss erfolgt über Issue #82 und Epic #67.
