# v0.5 Container Platform – Validierung und Freigabe für Monitoring

## Zweck

Dieses Dokument fasst die funktionale, sicherheitstechnische und betriebliche Validierung der v0.5 Container Platform zusammen und setzt Issue #81 um.

Die Einzeltests wurden bereits im Verlauf von #68 bis #80 aufgebaut. #81 erzeugt bewusst **keine zweite parallele Testlandschaft**, sondern bündelt diese Nachweise in einer maschinenlesbaren Evidence-Matrix:

```text
configuration/platform-validation.json
```

Damit bleibt eindeutig, welche reale CI-Prüfung welche Plattformanforderung abdeckt.

## Ergebnis

**Freigabeentscheidung: APPROVED für die Implementierung des Monitoring-Stacks.**

Das bedeutet:

- die Containerplattform ist als Runtime-Grundlage für Monitoring-Dienste validiert,
- Routing, TLS, Netzwerkisolation, Persistenz und Rollback sind technisch geprüft,
- zentrale Fehlerfälle besitzen reproduzierbare Tests,
- die Monitoring-Implementierung kann auf dieser Plattform beginnen.

Es bedeutet **nicht**:

- dass bereits ein Monitoring-Produktstack installiert ist,
- dass öffentliche DNS-/ACME-Bereitstellung durch CI vollständig simuliert wird,
- dass v0.5 als Milestone bereits geschlossen werden kann.

Der formale Abschlussreview aus #82 ist in `docs/60-v0.5-review.md` dokumentiert. Nach Merge des Abschluss-PRs verbleiben keine v0.5-Abschlussblocker.

## Evidenzmatrix

| Bereich | Reale Prüfung | Nachweis |
|---|---|---|
| Routing | Traefik routing integration | Router, Middleware, Backend-Routing, Admin-Trennung |
| TLS | Traefik routing + Reference service deployment | HTTP→HTTPS, TLS-Termination, HTTPS-Servicepfad |
| Isolation | Traefik routing integration | Edge/App/Data-Netze, exakte Membership, keine direkten App-Hostports |
| Persistenz | Reference service deployment | Bind-Mount-Daten überleben vollständigen Container-Recreate |
| Persistenzmodell | Static repository tests | erlaubte Pfade, Ownership, Volume-Klassifikation, Backup-Methode |
| Rollback | Update and rollback | absichtlich fehlerhafter Digest → letzte known-good Version |
| Health/Readiness | Traefik routing integration | Backend 500 → aus Rotation; Recovery → wieder aufgenommen |
| Ressourcen | Resource limits and OOM behavior | CPU/Memory/PID cgroups, OOM-Isolation, Host/Docker bleibt verfügbar |
| Logging | Docker log rotation | alter Logbestand rotiert, neue Logs bleiben abrufbar |
| Secrets | Static repository tests | sichere Dateiinjektion, Rotation, Path-Traversal-Abwehr |
| Image Security | Container Image Security | Allowlist, Digestpflicht, Trivy-Scans |
| Docker Lifecycle | Docker retention cleanup | Dry-Run, Safety-Gate, Rollback-Digests, managed Container, Images, Build-Cache, Volume-Ausschluss |

## Definition-of-Done-Abgleich

### Routing getestet

Erfüllt.

Der Traefik-Integrationstest startet Proxy und Testservices und prüft reales HTTP-/HTTPS-Routing.

### TLS getestet

Erfüllt innerhalb der CI-Grenzen.

CI erzeugt ein temporäres selbstsigniertes Zertifikat und prüft damit TLS-Termination und HTTPS-Routing.

Die produktive ACME-Konfiguration selbst ist versioniert und besitzt einen Fehlerdetektor. CI ruft bewusst keine öffentliche Certificate Authority auf.

Ein echter DNS-/Let's-Encrypt-Lauf bleibt deshalb ein Staging-/Deployment-Smoke-Test und kein Pull-Request-Test.

### Isolation getestet

Erfüllt.

Geprüft werden:

- Edge-Netz ist extern/bridge und nicht `internal`,
- App-/Data-Netze sind `internal: true`,
- Traefik hängt ausschließlich am Edge-Netz,
- datenführende Services hängen nicht am Edge-Netz,
- Service-Memberships entsprechen exakt dem Modell,
- Anwendungen veröffentlichen keine direkten Hostports.

### Persistenz getestet

Erfüllt.

Der Reference HTTP Service schreibt Testdaten in einen Bind-Mount, wird vollständig per `--force-recreate` ersetzt und liest dieselben Daten anschließend im neuen Container wieder aus.

Zusätzlich validieren statische Tests Pfade, Ownership und Backup-Metadaten.

### Rollback getestet

Erfüllt.

Der Deployment-Test:

1. deployt eine known-good Digest-Version,
2. versucht absichtlich eine ungeeignete zweite Version,
3. erkennt den fehlgeschlagenen Smoke-Test,
4. stellt die vorherige Digest-Version wieder her,
5. verifiziert `state.json`, `release.env`, Containerimage und HTTP-Health,
6. lässt den ursprünglichen Release korrekt als fehlgeschlagen enden.

## Getestete Fehlerfälle

### Backend ist nicht bereit

**Simulation:** Whoami-`/health` wird auf HTTP 500 gesetzt.

**Erwartung:** Traefik entfernt das Backend aus der Rotation und liefert bei nur einer Instanz 503.

**Recovery:** Nach HTTP 200 wird das Backend wieder aufgenommen.

### ACME-/Zertifikatserneuerungsfehler

**Simulation:** synthetischer ACME-Fehlerlog.

**Erwartung:** `check-acme-errors.py` liefert einen Fehlerstatus; normale Logs verursachen keinen False Positive.

### Netzwerkdrift

**Simulation/Nachweis:** exakte Docker-Network-Membership wird inspiziert.

**Erwartung:** zusätzliche oder fehlende Netzwerkmitgliedschaft lässt den Integrationstest scheitern.

### Container-OOM

**Simulation:** begrenzter Testcontainer erzeugt gezielt Speicherdruck.

**Erwartung:**

- `OOMKilled=true`,
- OOM bleibt containerlokal,
- Docker bleibt anschließend erreichbar.

### PID-Erschöpfung

**Simulation:** Testcontainer erzeugt Prozesse bis zum cgroup-Limit.

**Erwartung:** weitere Prozessstarts werden im Container begrenzt; Host wird nicht erschöpft.

### Log-Flood

**Simulation:** künstlich hohe Lograte mit sehr kleinen Test-Rotationsgrenzen.

**Erwartung:** alter Logmarker wird rotiert, aktueller Logbestand bleibt über `docker logs` verfügbar.

### Fehlerhafter Release

**Simulation:** known-good Whoami-Digest wird durch einen für den Testservice ungeeigneten, aber gültig gepinnten Traefik-Digest ersetzt.

**Erwartung:** Smoke-Test scheitert, automatischer Rollback auf known-good, Release bleibt fehlgeschlagen.

### Container-Recreate

**Simulation:** vollständiger Recreate des Referenzservices.

**Erwartung:** persistente Daten bleiben unverändert erhalten und die Route wird danach wieder healthy.

### Secret Path Traversal

**Simulation:** ungültiger Secretname mit Pfadnavigation.

**Erwartung:** Installation wird abgelehnt.

### Cleanup bei instabilem Release-State

**Simulation:** letzter Deploymentstatus ist `failed-manual-intervention-required`.

**Erwartung:** Apply wird vollständig übersprungen; Container, Images und Build-Cache bleiben unverändert.

### Cleanup und Rollback-Artefakte

**Simulation:** Current-/Previous-Digests liegen parallel zu cleanup-fähigen Altartefakten auf dem Runner.

**Erwartung:** cleanup-fähige managed Altartefakte werden entfernt, Current-/Previous-Digests, laufende Containerimages und Docker-Volumes bleiben bestehen.

## Security- und Betriebsnachweise

Neben der minimalen DoD von #81 sind außerdem aktiv getestet:

- Digest-Pinning und Registry-Allowlist,
- Vulnerability-Scanning der Plattformimages,
- read-only Root-FS,
- Capability-Drop,
- `no-new-privileges`,
- Ressourcenlimits,
- Log-Rotation,
- Secret-Injection,
- Health-/Readiness-Semantik,
- ACME-Speicherrechte,
- Update-/Rollback-State,
- rollback-sicheres Docker-Retention-Cleanup.

Damit ist die Freigabe für den nächsten Observability-/Monitoring-Schritt nicht nur auf Routing-Funktionalität gestützt.

## CI-Grenzen

CI kann bestimmte produktive Randbedingungen nicht vollständig nachbilden.

### Öffentliche ACME-Ausstellung

Pull Requests rufen keine öffentliche ACME-CA auf.

Stattdessen werden geprüft:

- Resolver-Konfiguration,
- ACME-Speicher,
- HTTP→HTTPS-Verhalten,
- TLS-Termination,
- Fehlerdetektion.

Live-DNS und echte Zertifikatsausstellung werden erst auf einem freigegebenen Staging-/Deployment-Ziel geprüft.

### Produktionslast

Die Resource-Tests beweisen Isolation und Grenzverhalten, nicht das endgültige Sizing von Odoo, PostgreSQL oder Monitoring-Komponenten.

Produktionslimits bleiben workloadabhängig.

### Externe Monitoring-Unabhängigkeit

Die Plattform ist für Monitoring **freigegeben**; die konkrete Monitoring-Architektur muss anschließend sicherstellen, dass kritische externe Probes nicht ausschließlich auf dem überwachten Host laufen.

## Abschlussstatus

### #231 – Docker-Retention und Cleanup automatisieren

Erledigt.

Die Plattform besitzt einen dry-run-fähigen, rollback-sicheren Lifecycle für managed Stopped-Container, ungenutzte/Dangling Images und Build-Cache. Current-/Previous-Digests sowie laufende Containerimages bleiben geschützt; persistente Volumes werden nicht automatisch bereinigt.

Runtime-Evidenz: `tests/integration/test-docker-retention-cleanup.sh`.

### #82 – v0.5 Review & Abschluss

Erledigt durch den Abschlussreview in `docs/60-v0.5-review.md`.

Der Review bestätigt:

- keine verbleibenden v0.5-Arbeitspakete außer dem formalen Abschluss selbst,
- vollständige Plattformtests,
- vollständige v0.5-Dokumentation,
- getestetes Update-/Rollback-Verfahren,
- Freigabe von Epic #83 als nächsten Entwicklungsschritt.

## Maschinenlesbare Prüfung

```bash
python3 scripts/validate-platform-validation.py
```

Die Prüfung stellt sicher:

- alle verpflichtenden Fähigkeiten besitzen reale Evidenz,
- referenzierte Testdateien existieren,
- referenzierte Workflow-Jobs existieren,
- zentrale Fehlerfälle dokumentiert sind,
- #231 und #82 als abgeschlossene Arbeitspakete geführt werden,
- keine offenen v0.5-Abschlussblocker verbleiben,
- #83 als nächster Epic und #84 als erster fachlicher Task festgelegt sind,
- Monitoring-Freigabe und Milestone-Abschluss nicht verwechselt werden.

## Freigabe

**Container Platform v0.5: freigegeben als Grundlage für Monitoring.**

**Epic #67: nach Merge des Abschluss-PRs schließbar.**

**Offene v0.5-Abschlussblocker: 0.**

Nächster Epic: **#83 – v0.6 Monitoring**.

## Referenzen

- `configuration/platform-validation.json`
- `docs/49-docker-network-model.md`
- `docs/50-volume-persistence-model.md`
- `docs/51-secret-management.md`
- `docs/52-container-registry-security.md`
- `docs/54-healthcheck-standards.md`
- `docs/55-container-resource-limits.md`
- `docs/56-log-rotation.md`
- `docs/57-update-rollback.md`
- `docs/59-docker-retention-cleanup.md`
- `docs/60-v0.5-review.md`
- `docs/08-monitoring.md`
