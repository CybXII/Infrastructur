# Docker-Netzwerkmodell

## Zweck

Dieses Dokument definiert das verbindliche Netzwerkmodell der Merchfactory Container Platform ab v0.5. Ziel ist eine nachvollziehbare Segmentierung zwischen öffentlichem Ingress, anwendungsinterner Kommunikation und datenführenden Diensten.

Das Modell setzt Issue #71 um und ergänzt die Docker-/Compose-Standards aus `docs/48-docker-compose-standards.md`.

## Sicherheitsprinzipien

Es gelten folgende Grundsätze:

- Services erhalten nur die Netzwerke, die sie für ihre Aufgabe benötigen.
- Öffentliche Erreichbarkeit erfolgt ausschließlich über Traefik.
- Anwendungs- und Datennetze sind stack-lokal und `internal: true`.
- Datenbanken, Caches und andere datenführende Dienste werden nicht an das Edge-Netz angeschlossen.
- Direkte Host-Portfreigaben von Anwendungsdiensten sind nicht Teil des Standardmodells.
- Administrative Ports bleiben an Loopback gebunden.
- Stack-lokale Netze erhalten keine festen globalen Namen; Compose kapselt sie über den Projektnamen.

## Netzwerkklassen

### Shared Edge

Das gemeinsame Edge-Netz heißt standardmäßig:

```text
merchfactory-edge
```

Eigenschaften:

- Docker-Treiber: `bridge`
- extern durch die Plattform verwaltet
- nicht `internal`, damit Traefik öffentliche Verbindungen terminieren und weiterleiten kann
- Mitglieder: Traefik und ausschließlich explizit ingress-fähige Service-Endpunkte
- keine Datenbanken, Caches oder rein internen Worker

Das Netz wird einmalig bzw. idempotent vorbereitet:

```bash
bash platform/network/scripts/prepare-edge-network.sh
```

Ein abweichender Name kann über `MERCHFACTORY_EDGE_NETWORK` gesetzt werden.

### App-Netz

Jeder Service-Stack darf ein stack-lokales Netz mit dem Compose-Schlüssel `app` definieren:

```yaml
networks:
  app:
    internal: true
```

Eigenschaften:

- nur innerhalb eines Compose-Projekts sichtbar
- kein fester globaler `name:`
- verbindet öffentliche Frontends mit internen Backends oder Workern
- Traefik gehört nicht in dieses Netz

### Data-Netz

Datenführende Kommunikation verwendet ein separates stack-lokales Netz mit dem Compose-Schlüssel `data`:

```yaml
networks:
  data:
    internal: true
```

Eigenschaften:

- nur innerhalb eines Compose-Projekts sichtbar
- kein fester globaler `name:`
- Mitglieder sind ausschließlich Dienste, die den jeweiligen Datenspeicher benötigen
- Datenbank- und Cache-Dienste besitzen weder Edge-Mitgliedschaft noch Host-Portfreigaben

## Kommunikationsmatrix

| Quelle | Ziel | Pfad | Standard |
|---|---|---|---|
| Internet | Traefik | Host 80/443 | erlaubt auf Load-Balancer-Hosts |
| Traefik | öffentlicher Service-Endpunkt | `edge` | erlaubt |
| öffentlicher Service-Endpunkt | interner Worker/Backend | `app` | erlaubt, wenn erforderlich |
| Anwendung/Worker | Datenbank oder Cache | `data` | erlaubt, wenn erforderlich |
| Traefik | Datenbank/Cache | keiner | verboten |
| Datenbank/Cache | `edge` | keiner | verboten |
| Service-Stack A | stack-lokales Netz B | keiner | verboten |
| Internet | Admin-EntryPoint | keiner | verboten |

Mitgliedschaft in einem Docker-Netz ist eine Vertrauensgrenze. Innerhalb desselben Netzes können Container grundsätzlich direkt miteinander kommunizieren. Deshalb dürfen Dienste nicht vorsorglich an zusätzliche Netze angeschlossen werden.

## Öffentliche Host-Ports

Traefik verwendet sichere Loopback-Defaults für lokale Tests und vorbereitete Hosts:

```text
TRAEFIK_HTTP_BIND=127.0.0.1:18080
TRAEFIK_HTTPS_BIND=127.0.0.1:18443
TRAEFIK_ADMIN_BIND=127.0.0.1:18081
```

Für einen produktiven Load-Balancer-Host werden HTTP und HTTPS explizit auf die öffentlichen Standardports gesetzt:

```text
TRAEFIK_HTTP_BIND=0.0.0.0:80
TRAEFIK_HTTPS_BIND=0.0.0.0:443
TRAEFIK_ADMIN_BIND=127.0.0.1:18081
```

Voraussetzung ist das bereits vorhandene Firewall-Rollenprofil `load_balancer`, das ausschließlich 80/tcp und 443/tcp zusätzlich öffnet. Provider-Firewalls oder Security Groups müssen separat geprüft werden.

## ACME

Die HTTP-01-Challenge von Let's Encrypt benötigt öffentliche Erreichbarkeit auf TCP/80. Eine reale Zertifikatsausstellung funktioniert daher erst, wenn:

1. DNS auf den Zielhost zeigt,
2. Traefik auf Host-Port 80 lauscht,
3. Host- und Provider-Firewall TCP/80 erlauben.

Port 443 wird für den regulären HTTPS-Betrieb benötigt.

## Egress

`app` und `data` sind mit `internal: true` bewusst ohne direkten externen Routingpfad definiert.

Ein Dienst, der ausschließlich intern arbeitet, aber aus fachlichen Gründen externen Egress benötigt, darf nicht allein deshalb an `edge` angeschlossen werden. Ein zusätzliches Egress-Modell wird bei Bedarf separat definiert und sicherheitsseitig geprüft.

## Beispiel

```yaml
services:
  web:
    networks:
      - edge
      - app

  worker:
    networks:
      - app
      - data

  database:
    networks:
      - data

networks:
  edge:
    external: true
    name: ${MERCHFACTORY_EDGE_NETWORK:-merchfactory-edge}

  app:
    internal: true

  data:
    internal: true
```

Damit ist `web` über Traefik erreichbar, `worker` bleibt vom Edge-Netz getrennt und `database` ist ausschließlich im Datennetz sichtbar.

## Validierung

Der Traefik-Integrationstest prüft automatisiert:

- idempotente Erstellung des Edge-Netzes,
- erwarteten Bridge-Treiber und Plattform-Labels,
- `internal=false` für Edge,
- `internal=true` für App und Data,
- Traefik ist ausschließlich Mitglied von Edge,
- der öffentliche Beispielservice ist Mitglied von Edge und App,
- der interne Worker ist Mitglied von App und Data,
- der Datenservice ist ausschließlich Mitglied von Data,
- kein Beispielservice besitzt eine direkte Host-Portfreigabe,
- Routing über Traefik funktioniert weiterhin.

## Abgrenzung

Nicht Bestandteil dieses Arbeitspakets sind:

- Persistenz- und Backup-Klassen (#72),
- Secret-Management (#73),
- Registry-Vertrauen und Image-Scanning (#74),
- vollständiges Service-Template (#75),
- allgemeine Healthcheck-Standards (#76),
- Ressourcenlimits (#77),
- Logging und Rotation (#78),
- Update und Rollback (#79),
- vollständiges Egress-Filtering.
