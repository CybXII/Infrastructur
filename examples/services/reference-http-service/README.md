# Reference HTTP Service

## Zweck

Dieser Dienst ist die **ausführbare Referenzbereitstellung** der v0.5 Container Platform für Issue #80.

Im Gegensatz zur abstrakten Struktur unter `examples/services/example-service/` verwendet diese Referenz ausschließlich ein real verfügbares, bereits allowgelistetes und per SHA-256-Digest gepinntes Image.

Image:

```text
docker.io/traefik/whoami@sha256:c4717a8d1f0134a7444e24f881160e033991f23027c6c5a9a3f8fd22e70d1d44
```

## Abgedeckte Plattformfunktionen

Die Referenz demonstriert gemeinsam:

- externes Shared-Edge-Netz,
- kein direkter Anwendungs-Hostport,
- Traefik-Routing,
- HTTPS/TLS,
- aktiven Readiness-Healthcheck,
- Docker-Liveness,
- CPU-/Memory-/PID-Limits,
- Ausführung als numerische UID/GID `65532:65532`,
- internen unprivilegierten Port `8080`,
- read-only Root-Dateisystem,
- Capability-Drop und `no-new-privileges`,
- stdout/stderr-Logging über die Plattformdefaults,
- persistenten Bind-Mount,
- reproduzierbaren Container-Recreate.

## Struktur

```text
reference-http-service/
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
└── README.md
```

## Produktiver Routing-Hinweis

`routing/route.yaml` enthält absichtlich den Dokumentationshost:

```text
reference-service.example.invalid
```

Vor einer echten externen Bereitstellung wird dieser Host durch einen realen DNS-Namen ersetzt. TLS wird dann über den bestehenden Resolver `letsencrypt` ausgestellt.

Der CI-Integrationstest verwendet stattdessen `reference-service.localhost` und ein nur zur Laufzeit erzeugtes selbstsigniertes Zertifikat. Es werden keine Test-Private-Keys committed.

## Persistenz

Host:

```text
/srv/merchfactory/persistent/reference-http-service/data
```

Container:

```text
/var/lib/reference-http-service
```

Für CI wird der Hostpfad über `REFERENCE_SERVICE_DATA_DIR` auf ein temporäres Verzeichnis umgebogen.

Der Integrationstest schreibt eine Datei über `docker cp` in den gemounteten Pfad, erzwingt einen Container-Recreate und liest die Datei anschließend wieder aus. Damit wird die Persistenz des Plattform-Mounts real geprüft.

## Logging

Der Dienst definiert **keinen** Compose-`logging:`-Override. Er erbt die Plattformvorgabe:

```text
Docker local driver
20 MiB × 5
compression enabled
```

Der Integrationstest prüft zusätzlich, dass der Dienst über `docker logs` Betriebslogs liefert.

## Health

Liveness:

```text
/whoami --help
```

Readiness:

```text
GET http://reference-http-service:8080/health -> HTTP 200
```

Traefik prüft Readiness aktiv und nimmt ein nicht bereites Backend aus der Rotation.

## Reproduzierbare Vorbereitung

Auf einem Plattformhost:

```bash
bash platform/network/scripts/prepare-edge-network.sh
sudo bash scripts/prepare-storage-directory.sh \
  /srv/merchfactory/persistent/reference-http-service/data \
  65532 65532 0750 persistent
```

Danach:

```bash
docker compose \
  -p reference-http-service \
  -f examples/services/reference-http-service/deployment/compose.yaml \
  pull

docker compose \
  -p reference-http-service \
  -f examples/services/reference-http-service/deployment/compose.yaml \
  up -d
```

Die Routing-Datei wird nach Anpassung des Hostnamens kontrolliert in die dynamische Traefik-Konfiguration übernommen.

## Automatischer Nachweis

CI führt `tests/integration/test-reference-service-deployment.sh` aus.

Der Test prüft:

1. Compose- und Image-Policy.
2. Edge-Netzwerk.
3. Traefik-Start.
4. HTTP→HTTPS-Redirect.
5. TLS-Routing zum Referenzservice.
6. HTTP 200 auf `/health`.
7. Docker-Liveness = healthy.
8. keine direkte Host-Portfreigabe des Services.
9. Betriebslogs über `docker logs`.
10. Persistenz über einen vollständigen Container-Recreate.
11. Cleanup aller Testressourcen.

Damit dient dieser Service als ausführbare Referenz für weitere Anwendungen.
