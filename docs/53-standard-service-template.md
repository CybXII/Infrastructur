# Standardisiertes Service-Template

## Zweck

Dieses Dokument beschreibt die verbindliche Vorlage für neue containerisierte Dienste der Merchfactory Container Platform. Es setzt Issue #75 um und bündelt die in #68–#74 definierten Plattformverträge in einer renderbaren Service-Struktur.

Die Vorlage liegt unter:

```text
templates/services/container-service/
```

Sie ist keine produktive Konfiguration, sondern der Ausgangspunkt für einen neuen Dienst.

## Enthaltene Bereiche

Nach dem Rendern entsteht:

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
└── README.md
```

Damit enthält die Baseline bereits Compose, Routing, Healthcheck, Logging, Backup und Dokumentation.

## Platzhalter

Die erlaubten Platzhalter sind ausschließlich in `template.json` deklariert. Syntax:

```text
{{PLACEHOLDER_NAME}}
```

Erforderlich sind `SERVICE_NAME`, `IMAGE_REFERENCE`, `CONTAINER_PORT`, `PUBLIC_HOSTNAME`, `HEALTHCHECK_COMMAND`, `READINESS_PATH`, `SERVICE_UID`, `SERVICE_GID`, `OWNER` und `ESCALATION_CONTACT`.

Der Renderer lehnt fehlende und unbekannte Platzhalter ab. Nach erfolgreichem Rendering darf kein `{{...}}`-Platzhalter übrig bleiben.

## Rendering

```bash
python3 scripts/render-service-template.py \
  --output /tmp/my-service \
  --set SERVICE_NAME=my-service \
  --set IMAGE_REFERENCE=ghcr.io/merchfactory/my-service@sha256:<digest> \
  --set CONTAINER_PORT=8080 \
  --set PUBLIC_HOSTNAME=my-service.example.invalid \
  --set 'HEALTHCHECK_COMMAND=/app/healthcheck' \
  --set READINESS_PATH=/ready \
  --set SERVICE_UID=10001 \
  --set SERVICE_GID=10001 \
  --set OWNER=platform-team \
  --set ESCALATION_CONTACT=platform-oncall
```

Für produktive Nutzung muss der Zielpfad fachlich passend gewählt werden; `/tmp` dient nur der Demonstration.

## Eingabevalidierung

Der Renderer prüft Servicename, vollständige Digest-Image-Referenz, TCP-Port, DNS-Hostname, numerische UID/GID und vollständige Platzhalterbelegung. Er erzeugt keine Secrets.

## Compose und Routing

Die Compose-Datei enthält die bestehende Plattform-Baseline: read-only Root-FS, Capability-Drop, `no-new-privileges`, Persistenz, tmpfs, file-basiertes Secret, Healthcheck, Edge-/App-Netz, keine direkte Host-Portfreigabe sowie `com.merchfactory.managed=true` für den kontrollierten Docker-Lifecycle.

`routing/route.yaml` definiert für Traefik Host-Regel, `websecure`, den Resolver `letsencrypt` und den Upstream `http://SERVICE_NAME:CONTAINER_PORT`. Rendering aktiviert die Route nicht automatisch; sie wird erst nach Review kontrolliert in Traefik übernommen.

## Healthcheck, Logging und Ressourcen

Das Template folgt `docs/54-healthcheck-standards.md`:

- Compose-Liveness: 30s Intervall, 5s Timeout, 3 Retries,
- Traefik-Readiness: 10s Intervall, 3s Timeout, HTTP 200,
- externer Probe: 30s Intervall, 5s Timeout.

Der beim Rendering gesetzte `READINESS_PATH` wird sowohl in die Traefik-Route als auch in die Monitoring-Policy übernommen.

Logging folgt `docs/56-log-rotation.md`: stdout/stderr, Docker-`local`-Driver, 20 MiB × 5 lokale Segmente mit Kompression und keine servicebezogenen Logging-Overrides. Die gerenderte `logging/policy.yaml` ordnet zusätzlich die zentrale Retention-Klasse zu.

Das Template enthält das Standard-Ressourcenprofil aus `docs/55-container-resource-limits.md`:

- 1.0 CPU,
- 512 MiB Memory Hard Limit,
- 256 MiB Memory Reservation,
- 256 PIDs,
- CPU Shares 512.

Die Werte sind über klar benannte `SERVICE_*`-Variablen anpassbar. Für Production müssen abweichende Workloads mit realistischen Lasten validiert werden.

## Backup und Restore

Jeder neue Service erhält eine eigene `backup/policy.yaml`. Fachlich noch offene Backup-/Restore-Methoden sind mit `CHANGE_ME` markiert und müssen vor produktiver Nutzung ersetzt werden.

## Update und Rollback

Das Compose-Manifest verwendet `SERVICE_IMAGE_REFERENCE` als kontrollierten Runtime-Digest und fällt ohne Release-State auf den beim Rendering fest gepinnten Basisdigest zurück.

Verwaltete Releases nutzen `deployment/service-release.py` und `docs/57-update-rollback.md`. Der Controller verwaltet aktuellen und vorherige bekannte gute Digests, Freigabe-/Backup-Referenzen sowie Update- und Rollback-Verifikation.

## Automatische Validierung

Die Vorlage besitzt drei Ebenen: Renderer-Unit-Tests, Compose-/Image-Policy-Validierung eines gerenderten Beispiels und eine echte Docker-Beispielbereitstellung.

Der Smoke-Test rendert mit `docker.io/traefik/whoami`, verwendet nur künstliche Secrets, erstellt ein isoliertes Edge-Testnetz, veröffentlicht ausschließlich im Testoverlay einen localhost-Port, startet den Container, prüft `GET /health` auf HTTP 200 und räumt anschließend alle Testressourcen wieder auf.

Damit wird nicht nur die Syntax, sondern die tatsächliche Bereitstellbarkeit der Vorlage geprüft.

Zusätzlich liegt unter `examples/services/reference-http-service/` eine vollständig ausführbare Plattformreferenz. Deren eigener Integrationstest startet Traefik und den Dienst gemeinsam und validiert TLS, Routing, Health, Logging und Persistenz über einen Container-Recreate. Sie bildet damit den Nachweis aus Issue #80.

## Abgrenzung

Die Struktur ist mit #75 vollständig. #76 bis #79 sowie #231 sind in die Vorlage integriert; der Host-Lifecycle für alte managed Container und Images ist in `docs/59-docker-retention-cleanup.md` geregelt.
