# Volume-Namenskonventionen

## Zweck

Dieses Dokument definiert verbindliche Namen für persistente und temporäre Docker-Volumes der Merchfactory Infrastructure Platform.

Ziel ist, dass Umgebung, Service, Datenklasse und Backup-Relevanz eindeutig erkennbar sind und Volumes in Docker, Backup, Monitoring, Restore und Dokumentation konsistent verwendet werden.

## Verbindliches Schema

Volumes verwenden folgendes Format:

```text
<umgebung>-<service>-<datenklasse>-<backupklasse>
```

Beispiele:

```text
prd-n8n-data-bkp
prd-postgres-db-bkp
prd-traefik-acme-bkp
stg-n8n-data-bkp
prd-n8n-cache-nobkp
```

## Umgebungskennungen

| Kennung | Bedeutung |
|---|---|
| `dev` | Development |
| `stg` | Staging |
| `prd` | Production |
| `mgmt` | umgebungsübergreifende Management-Dienste |
| `lab` | isolierte Labor- oder Testumgebung |

## Service-Segment

Das Service-Segment verwendet den stabilen technischen Servicenamen.

Beispiele:

```text
traefik
n8n
postgres
redis
prometheus
grafana
loki
backup-agent
shopify-bridge
deco-bridge
```

Regeln:

- ausschließlich Kleinbuchstaben, Ziffern und Bindestriche
- keine Versionsnummern
- keine Kunden- oder Personennamen
- keine temporären Begriffe wie `new`, `old` oder `test2`

## Datenklassen

| Datenklasse | Verwendung |
|---|---|
| `data` | allgemeine persistente Anwendungsdaten |
| `db` | Datenbankdatenverzeichnis |
| `uploads` | hochgeladene Dateien |
| `files` | verwaltete Dateiablage |
| `config` | veränderliche Laufzeitkonfiguration |
| `acme` | Zertifikats- und ACME-Daten |
| `metrics` | Metrikdaten |
| `logs` | persistente Logdaten |
| `queue` | persistente Queue- oder Jobdaten |
| `cache` | rekonstruierbare Cache-Daten |
| `tmp` | temporäre Laufzeitdaten |
| `backup` | lokaler Backup-Staging-Bereich |

Neue Datenklassen dürfen nur nach dokumentierter Erweiterung dieses Standards eingeführt werden.

## Backupklassen

| Kennung | Bedeutung |
|---|---|
| `bkp` | muss regelmäßig gesichert werden |
| `nobkp` | wird bewusst nicht gesichert und ist rekonstruierbar |
| `external` | Sicherung erfolgt außerhalb des Volume-Backups durch einen dokumentierten Mechanismus |

Die Backupklasse beschreibt die Behandlung, nicht die Wichtigkeit des Services.

`external` ist beispielsweise zulässig, wenn PostgreSQL über konsistente Dumps oder WAL-basierte Sicherung gesichert wird und das rohe Datenvolume nicht direkt kopiert wird.

## Persistente Volumes

Persistente Volumes müssen einen stabilen, expliziten Namen erhalten.

Beispiel:

```yaml
volumes:
  n8n-data:
    name: prd-n8n-data-bkp
```

Der tatsächliche Docker-Volumename darf nicht unbeabsichtigt vom lokalen Verzeichnis oder Compose-Projektnamen abhängen.

## Temporäre Daten

Für rein temporäre Daten gilt:

- bevorzugt `tmpfs` verwenden,
- alternativ ein Volume mit Datenklasse `tmp` und Backupklasse `nobkp`,
- temporäre Daten dürfen keine einzige Quelle für fachlich relevante Daten sein.

Beispiel:

```yaml
services:
  app:
    tmpfs:
      - /tmp
```

Alternativ:

```text
prd-shopify-bridge-tmp-nobkp
```

## Beispiele nach Service

### Traefik

```text
prd-traefik-acme-bkp
prd-traefik-config-bkp
```

### n8n

```text
prd-n8n-data-bkp
prd-n8n-files-bkp
prd-n8n-cache-nobkp
```

### PostgreSQL

```text
prd-postgres-db-external
prd-postgres-backup-bkp
```

### Monitoring

```text
prd-prometheus-metrics-bkp
prd-grafana-data-bkp
prd-loki-logs-bkp
```

### Staging und Development

```text
stg-n8n-data-bkp
dev-n8n-data-nobkp
lab-postgres-db-nobkp
```

Development-Daten dürfen nur dann `nobkp` verwenden, wenn ein Verlust ausdrücklich akzeptiert und die Wiederherstellung dokumentiert ist.

## Backup- und Restore-Regeln

Für jedes Volume mit `bkp` oder `external` müssen dokumentiert sein:

- Backup-Methode
- Sicherungsintervall
- Aufbewahrung
- Verschlüsselung
- Offsite-Ziel
- Restore-Verfahren
- letzter erfolgreicher Restore-Test
- verantwortlicher Service

Ein Volume mit `nobkp` muss vollständig aus Repository, Images, Konfiguration oder Upstream-Daten rekonstruierbar sein.

## Docker-Compose-Verwendung

Beispiel:

```yaml
name: prd-n8n

services:
  app:
    volumes:
      - n8n-data:/home/node/.n8n
      - n8n-files:/files

volumes:
  n8n-data:
    name: prd-n8n-data-bkp
  n8n-files:
    name: prd-n8n-files-bkp
```

Der interne Compose-Schlüssel darf kürzer sein. Der explizite Docker-Volumename muss dem Standard entsprechen.

## Bind Mounts

Bind Mounts werden nur verwendet, wenn ein dokumentierter Hostpfad erforderlich ist.

Das Hostpfad-Schema folgt:

```text
/opt/merchfactory/data/<umgebung>/<service>/<datenklasse>/
```

Beispiele:

```text
/opt/merchfactory/data/prd/n8n/files/
/opt/merchfactory/data/prd/traefik/acme/
/opt/merchfactory/data/stg/n8n/uploads/
```

Bind Mounts unter persönlichen Home-Verzeichnissen oder beliebigen Pfaden sind für produktive Daten nicht zulässig.

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

```regex
^(dev|stg|prd|mgmt|lab)-[a-z0-9]+(?:-[a-z0-9]+)*-(data|db|uploads|files|config|acme|metrics|logs|queue|cache|tmp|backup)-(bkp|nobkp|external)$
```

## Verbotene Beispiele

```text
volume1
n8n_data
prod-data
alex-postgres
kunde-a-files
new-volume
prd-n8n-v1-data
prd-postgres-db
```

Gründe:

- Umgebung, Service, Datenklasse oder Backupklasse fehlt
- Unterstriche oder inkonsistente Schreibweise
- Personen- oder Kundenbezug
- Versionsnummern im dauerhaften Namen
- unklare Backup-Behandlung

## Migration bestehender Volumes

Eine Umbenennung ist keine reine Metadatenänderung. Vor einer Migration sind mindestens zu prüfen:

1. laufende Container stoppen oder konsistent quiescen
2. Backup und Prüfsumme erstellen
3. neues Volume anlegen
4. Daten kontrolliert kopieren
5. Besitzrechte und Dateimodi prüfen
6. Compose-Referenzen aktualisieren
7. Anwendung und Healthchecks testen
8. Backup- und Restore-Jobs aktualisieren
9. altes Volume erst nach erfolgreicher Verifikation entfernen

Produktive Volume-Migrationen durchlaufen Development, Staging und kontrollierte Promotion.

## Ausnahmen

Abweichungen sind nur zulässig, wenn ein Image, Provider oder bestehendes technisches System einen anderen Namen erzwingt.

Jede Ausnahme benötigt:

- Begründung
- betroffenes Volume
- technische Einschränkung
- Backup-Auswirkung
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #40

- Service, Umgebung und Datenklasse sind im Schema enthalten.
- Backup-Relevanz ist über `bkp`, `nobkp` oder `external` eindeutig erkennbar.
- persistente und temporäre Daten sind abgegrenzt.
- Compose-Volumes und Bind Mounts sind geregelt.
- gültige und verbotene Beispiele sind dokumentiert.
- Validierung, Migration und Ausnahmeprozess sind definiert.

## Referenzen

- `docs/03-server-layout.md`
- `docs/22-container-naming-conventions.md`
- `docs/23-network-naming-conventions.md`
- Issue #40
- Epic #35
