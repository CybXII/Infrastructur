# Traefik Reverse Proxy und TLS

## Zweck

Dieser Bereich stellt die versionierte Traefik-Baseline der Merchfactory Container Platform bereit.

Traefik übernimmt die zentrale HTTP-/HTTPS-Routing-Schicht. Die Konfiguration trennt öffentliche Web-EntryPoints vom administrativen Dashboard und enthält einen ACME-Resolver für automatische Zertifikatsausstellung und -erneuerung.

## Struktur

```text
platform/traefik/
├── compose.yaml
├── config/
│   ├── traefik.yaml
│   └── dynamic/
│       └── dashboard.yaml
├── scripts/
│   ├── prepare-acme-storage.sh
│   ├── backup-acme-storage.sh
│   └── check-acme-errors.py
└── tests/
    ├── compose.test.yaml
    ├── example-route.yaml
    └── test-routing.sh
```

## EntryPoints

Die statische Konfiguration definiert:

- `web` auf Container-Port 8080,
- `websecure` auf Container-Port 8443,
- `admin` auf Container-Port 8081.

HTTP wird permanent auf HTTPS umgeleitet. Die ACME-HTTP-01-Challenge nutzt weiterhin den `web`-EntryPoint; Traefik behandelt die Challenge intern.

Die Compose-Datei bindet die Ports standardmäßig weiterhin nur an Loopback:

```text
TRAEFIK_HTTP_BIND=127.0.0.1:18080
TRAEFIK_HTTPS_BIND=127.0.0.1:18443
TRAEFIK_ADMIN_BIND=127.0.0.1:18081
```

Traefik ist Mitglied des gemeinsam verwalteten externen Edge-Netzes `merchfactory-edge`. Das Netz wird vor dem Start mit `bash platform/network/scripts/prepare-edge-network.sh` angelegt bzw. validiert.

Für einen produktiven Load-Balancer-Host werden HTTP und HTTPS bewusst über Umgebungsvariablen auf `0.0.0.0:80` und `0.0.0.0:443` gebunden. Der Admin-Port bleibt auf Loopback. Voraussetzung ist das gehärtete Firewall-Profil `load_balancer`.

Das vollständige Segmentierungs- und Kommunikationsmodell ist in `docs/49-docker-network-model.md` dokumentiert.

## ACME-Resolver

Der Resolver heißt `letsencrypt` und verwendet HTTP-01:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      storage: /var/lib/traefik/acme/acme.json
      httpChallenge:
        entryPoint: web
```

Service-Router aktivieren den Resolver später explizit mit `certResolver: letsencrypt`.

Für eine erfolgreiche öffentliche Ausstellung müssen DNS, Port 80 und die externe Erreichbarkeit des Zielhosts korrekt konfiguriert sein.

Traefik übernimmt die automatische Erneuerung ausgestellter ACME-Zertifikate. Ein separater Cronjob zum Erneuern der Zertifikate ist nicht vorgesehen.

## Geschützter Zertifikatsspeicher

Der Hostpfad wird über `TRAEFIK_ACME_DIR` gesetzt. Standard:

```text
/srv/merchfactory/persistent/traefik/acme
```

Vor einem Start auf einem verwalteten Host wird der Speicher vorbereitet:

```bash
sudo platform/traefik/scripts/prepare-acme-storage.sh
```

Erwarteter Zustand:

- Verzeichnis: Modus `0700`
- `acme.json`: Modus `0600`

Der Pfad wird als einziges beschreibbares persistentes Traefik-Verzeichnis in den ansonsten read-only Container gemountet.

`acme.json` kann private Schlüssel enthalten und darf weder committed noch ungeschützt kopiert werden. Im Persistenzmodell ist der ACME-Speicher Klasse D (Secret-/Credential-Material). Das lokale Backup ist deshalb nur ein geschützter Sicherungsbaustein; Offsite-Verschlüsselung und Secret-Recovery werden mit #73 und der übergreifenden Backup-Strategie abgestimmt.

## Backup

Für den ACME-Speicher existiert ein explizites Backup-Werkzeug:

```bash
sudo platform/traefik/scripts/backup-acme-storage.sh
```

Standardziel:

```text
/srv/merchfactory/shared/backups/traefik-acme
```

Das Backup:

- verweigert unsichere Quellrechte,
- schreibt Sicherungen mit Modus `0600`,
- erzeugt eine SHA-256-Prüfsumme,
- arbeitet über eine temporäre Datei und anschließendes `mv`.

Die übergreifende Backup-/Retention-Strategie bleibt Bestandteil der späteren Plattform- und Backup-Arbeitspakete.

## ACME-Fehlersignal

`check-acme-errors.py` liest Traefik-Logs von stdin und liefert einen Fehlerstatus, wenn bekannte ACME-Ausstellungs- oder Erneuerungsfehler erkannt werden.

Beispiel:

```bash
docker compose -f platform/traefik/compose.yaml logs --since 15m --no-color traefik \
  | python3 platform/traefik/scripts/check-acme-errors.py
```

Exit-Code `1` ist ein Alarmzustand und kann vom späteren Monitoring übernommen werden. Das eigentliche zentrale Alert-Transport- und Eskalationsmodell gehört nicht in diesen Task.

## Dashboard und Adminzugriff

Das Dashboard läuft weiterhin ausschließlich auf dem getrennten `admin`-EntryPoint. `api.insecure` bleibt deaktiviert.

Remote-Zugriff erfolgt über SSH-Tunnel:

```bash
ssh -L 8081:127.0.0.1:18081 bootstrap@SERVER
```

## Tests

Der Integrationstest erzeugt für die CI ein kurzlebiges selbstsigniertes Zertifikat und prüft ohne Kontakt zu einer öffentlichen CA:

1. Traefik startet mit aktiviertem ACME-Resolver.
2. HTTP wird permanent auf HTTPS umgeleitet.
3. HTTPS-Routing zum internen Beispielservice funktioniert.
4. Middleware-Header werden über TLS ausgeliefert.
5. Aktiver Readiness-Healthcheck nimmt ein absichtlich fehlerhaftes Backend aus der Rotation.
6. Nach Recovery wird das Backend wieder aufgenommen.
7. Dashboard bleibt auf dem separaten lokalen Admin-EntryPoint.
8. Das externe Edge-Netz wird idempotent vorbereitet und validiert.
9. App- und Data-Netze sind intern und die Testdienste besitzen ausschließlich die vorgesehenen Netzwerkmitgliedschaften.
10. Kein Beispielservice veröffentlicht einen direkten Host-Port.
11. ACME-Speicher wird mit `0700/0600` vorbereitet.
12. Backup und SHA-256-Prüfung funktionieren.
13. Ein simulierter Erneuerungsfehler löst das ACME-Fehlersignal aus.
14. Normale Traefik-Logs erzeugen keinen falschen ACME-Alarm.

Die CI kontaktiert bewusst keine Let's-Encrypt-Produktiv- oder Staging-CA. Eine reale Ausstellung benötigt öffentliche DNS-/Port-Erreichbarkeit und wird beim späteren Development-Rollout zusätzlich verifiziert.

## Service-Readiness

Für öffentlich geroutete HTTP-Services verwendet die Plattform aktive Traefik-Load-Balancer-Healthchecks gemäß `docs/54-healthcheck-standards.md`. Nicht bereite Backends werden aus der Routing-Rotation genommen; dies ist bewusst unabhängig vom Docker-Liveness-Status.

## Ressourcenprofil

Traefik ist als kritischer Plattformdienst klassifiziert und verwendet standardmäßig:

```text
TRAEFIK_CPU_LIMIT=1.0
TRAEFIK_CPU_SHARES=1024
TRAEFIK_MEMORY_LIMIT=512m
TRAEFIK_MEMORY_RESERVATION=256m
TRAEFIK_PIDS_LIMIT=128
```

Das höhere CPU-Gewicht priorisiert den Ingress unter CPU-Konkurrenz. Die harten Limits bleiben bewusst gesetzt, damit auch ein Fehler im Reverse Proxy nicht unbegrenzt Hostressourcen verbraucht.

Details stehen in `docs/55-container-resource-limits.md`.

## Container-Härtung

Die Traefik-Definition folgt weiterhin #68:

- Image per SHA-256-Digest gepinnt,
- `restart: unless-stopped`,
- read-only Root-Dateisystem,
- `cap_drop: ALL`,
- `no-new-privileges:true`,
- kein Docker-Socket,
- expliziter Healthcheck,
- CPU-, Memory- und PID-Limits.

## Abgrenzung

Noch nicht Bestandteil dieses Tasks sind:

- Secret-Management (#73),
- Registry-Strategie und Image-Scanning (#74),
- vollständiges Service-Template (#75),
- zentrale Monitoring-/Alert-Infrastruktur,
- Update und Rollback (#79).
