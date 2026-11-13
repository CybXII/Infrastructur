# Container-, Compose- und Service-Namenskonventionen

## Zweck

Dieses Dokument definiert verbindliche Namen für Docker-Compose-Projekte, Services, Container und Instanzen der Merchfactory Infrastructure Platform.

Ziel ist eine konsistente Verwendung in Docker, Logs, Monitoring, Backups, Dokumentation und Betriebsprozessen.

## Grundprinzip

Namen werden aus stabilen fachlichen Segmenten aufgebaut und enthalten keine zufälligen, personenbezogenen oder kundenspezifischen Bestandteile.

Verbindliche Reihenfolge:

```text
<umgebung>-<service>-<instanz>
```

Beispiel:

```text
prd-n8n-01
```

## Umgebungskennungen

| Kennung | Bedeutung |
|---|---|
| `dev` | Development |
| `stg` | Staging |
| `prd` | Production |
| `mgmt` | umgebungsübergreifende Management-Dienste |
| `lab` | isolierte Labor- oder Testdienste |

## Service-Namen

Service-Namen beschreiben die technische Funktion oder das Produkt und verwenden ausschließlich Kleinbuchstaben, Ziffern und Bindestriche.

Beispiele:

```text
traefik
n8n
postgres
redis
prometheus
grafana
loki
alloy
alertmanager
backup-agent
shopify-bridge
deco-bridge
```

Regeln:

- Produktnamen werden in ihrer üblichen technischen Kurzform verwendet.
- Mehrteilige Namen werden mit Bindestrichen getrennt.
- Keine Unterstriche.
- Keine Leerzeichen oder Sonderzeichen.
- Keine Versionsnummer im dauerhaften Servicenamen.
- Keine Kunden- oder Personennamen.
- Die Funktion bleibt auch bei Image- oder Versionswechsel stabil.

## Instanznummer

Die Instanz wird zweistellig angegeben:

```text
01
02
03
```

Die Nummer wird pro Kombination aus Umgebung und Service vergeben.

## Compose-Projektname

Compose-Projekte verwenden:

```text
<umgebung>-<service>
```

Beispiele:

```text
prd-traefik
prd-n8n
stg-n8n
dev-shopify-bridge
mgmt-monitoring
```

Der Projektname wird bevorzugt explizit gesetzt:

```bash
docker compose --project-name prd-n8n up -d
```

Alternativ kann in `compose.yaml` verwendet werden:

```yaml
name: prd-n8n
```

Der Compose-Projektname darf nicht vom lokalen Verzeichnisnamen oder vom ausführenden Benutzer abhängen.

## Compose-Service-Name

Innerhalb einer `compose.yaml` bleibt der Service-Name kurz und funktionsbezogen:

```yaml
services:
  app:
  db:
  redis:
  worker:
```

Bei eigenständigen Standardkomponenten kann der Produktname verwendet werden:

```yaml
services:
  traefik:
  prometheus:
  grafana:
```

Der Service-Name enthält normalerweise keine Umgebung, weil diese bereits durch den Compose-Projektnamen festgelegt ist.

## Containername

Container werden grundsätzlich durch Docker Compose aus Projekt-, Service- und Instanzinformationen erzeugt.

Das resultierende logische Schema lautet:

```text
<compose-projekt>-<service>-<instanz>
```

Beispiele:

```text
prd-n8n-app-01
prd-n8n-db-01
stg-n8n-app-01
prd-monitoring-prometheus-01
prd-monitoring-grafana-01
```

Ein explizites `container_name` wird nur verwendet, wenn eine konkrete technische Abhängigkeit es zwingend erfordert.

Begründung:

- feste Containernamen behindern horizontale Skalierung,
- Compose kann Instanzen nicht frei nummerieren,
- Namenskollisionen zwischen Projekten werden wahrscheinlicher,
- Rollouts und parallele Testinstanzen werden erschwert.

Bevorzugt:

```yaml
name: prd-n8n

services:
  app:
    image: example/n8n:1.0.0
```

Nicht bevorzugt:

```yaml
services:
  app:
    container_name: n8n
```

## Replikate und Worker

Mehrere Instanzen desselben Services werden über die Instanznummer unterschieden:

```text
prd-api-app-01
prd-api-app-02
prd-api-worker-01
prd-api-worker-02
```

Die Instanznummer ist keine fachliche Identität und darf bei automatischer Skalierung dynamisch vergeben werden.

## Docker-, Logging- und Monitoring-Kompatibilität

Die Namen müssen als stabile technische Labels verwendbar sein.

Empfohlene Labels:

```yaml
labels:
  merchfactory.environment: production
  merchfactory.project: prd-n8n
  merchfactory.service: app
  merchfactory.component: n8n
```

Empfohlene Monitoring-Dimensionen:

```text
environment=production
project=prd-n8n
service=app
container=prd-n8n-app-01
```

Logs sollen mindestens Umgebung, Projekt, Service und Containerinstanz zuordenbar machen.

## Zulässige Zeichen

Verbindlich:

- Kleinbuchstaben `a-z`
- Ziffern `0-9`
- Bindestriche als Trenner
- keine Unterstriche
- keine Leerzeichen
- keine Umlaute oder Sonderzeichen
- kein führender oder abschließender Bindestrich
- keine mehrfachen aufeinanderfolgenden Bindestriche

## Validierungsregex

Für vollständige logische Containernamen:

```regex
^(dev|stg|prd|mgmt|lab)-[a-z0-9]+(?:-[a-z0-9]+)*-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]{2}$
```

Für Compose-Projektnamen:

```regex
^(dev|stg|prd|mgmt|lab)-[a-z0-9]+(?:-[a-z0-9]+)*$
```

## Gültige Beispiele

```text
prd-traefik-traefik-01
prd-n8n-app-01
prd-n8n-db-01
stg-n8n-app-01
dev-shopify-bridge-api-01
prd-monitoring-prometheus-01
prd-monitoring-grafana-01
mgmt-backup-agent-runner-01
```

## Verbotene Beispiele

```text
n8n
N8N-PROD
prod_n8n
alex-n8n
kunde-a-app
new-container
container123
prd-n8n-v1
192-0-2-10-app
```

Gründe:

- fehlende Umgebung oder Instanz
- Großbuchstaben
- Unterstriche
- personenbezogene oder kundenspezifische Namen
- vergängliche Begriffe wie `new`
- Versionsbindung im dauerhaften Namen
- IP-Adresse als Identität

## Netzwerk- und DNS-Namen

Interne Docker-DNS-Auflösung verwendet den Compose-Service-Namen, nicht den vollständigen Containernamen.

Beispiel:

```text
app -> db:5432
```

Externe oder umgebungsübergreifende DNS-Namen werden separat verwaltet und dürfen nicht von zufälligen Docker-Containernamen abhängen.

## Umbenennung und Migration

Eine Umbenennung muss mindestens berücksichtigen:

1. Compose-Projektname
2. Volumes und Netzwerke
3. Monitoring- und Logging-Zuordnung
4. Backup-Jobs
5. Reverse-Proxy-Router und Labels
6. interne Service-Referenzen
7. Dokumentation und Betriebsinventar

Persistente Volumes dürfen bei einer Umbenennung nicht versehentlich neu erzeugt oder getrennt werden.

## Ausnahmen

Abweichungen sind nur zulässig, wenn ein externes System oder eine technische Einschränkung eine andere Benennung erzwingt.

Jede Ausnahme benötigt:

- Begründung
- betroffenen Service
- technische Einschränkung
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #37

- Schema für Service, Umgebung und Instanz ist dokumentiert.
- Compose-Projekt-, Service- und Containernamen sind voneinander abgegrenzt.
- Docker-, Logging- und Monitoring-Kompatibilität ist beschrieben.
- gültige und verbotene Beispiele sind vorhanden.
- Validierungsregeln und Ausnahmeprozess sind definiert.

## Referenzen

- `docs/03-server-layout.md`
- `docs/21-server-naming-conventions.md`
- Issue #37
- Epic #35
