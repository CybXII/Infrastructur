# Netzwerk-Namenskonventionen

## Zweck

Dieses Dokument definiert verbindliche Namen für Docker-Netzwerke, VLANs, Subnetze und interne Sicherheitszonen der Merchfactory Infrastructure Platform.

Ziel ist eine eindeutige, maschinenlesbare und sicherheitsorientierte Benennung in Docker, Firewall-Regeln, Monitoring, Inventar und Dokumentation.

## Grundprinzip

Netzwerknamen verwenden stabile Segmente und machen mindestens Umgebung, Sicherheitszone und Zweck erkennbar.

## Docker-Netzwerke

Verbindliches Schema:

```text
<umgebung>-<zone>-<zweck>
```

Beispiele:

```text
prd-public-web
prd-app-internal
prd-data-postgres
prd-observability-metrics
prd-backup-transfer
stg-app-internal
dev-app-internal
mgmt-admin-internal
```

### Umgebungskennungen

| Kennung | Bedeutung |
|---|---|
| `dev` | Development |
| `stg` | Staging |
| `prd` | Production |
| `mgmt` | umgebungsübergreifendes Management |
| `lab` | isolierte Labor- oder Testumgebung |

### Sicherheitszonen

| Zone | Zweck |
|---|---|
| `public` | öffentlich erreichbare Eintrittspunkte |
| `edge` | Reverse Proxy, TLS und vorgeschaltete Sicherheitsdienste |
| `app` | interne Anwendungsdienste |
| `data` | Datenbanken und zustandsbehaftete Datendienste |
| `observability` | Monitoring, Logging und Alerting |
| `backup` | Backup-, Restore- und Transferpfade |
| `management` | Administration, Bootstrap und interne Steuerung |
| `restricted` | besonders eingeschränkte interne Komponenten |

Die Zone beschreibt den Sicherheitskontext. Produktnamen oder einzelne Container ersetzen keine Zone.

### Zwecksegment

Das Zwecksegment beschreibt die konkrete Funktion innerhalb der Zone.

Beispiele:

```text
web
internal
postgres
redis
metrics
logs
alerts
transfer
admin
```

Mehrteilige Zwecke werden mit Bindestrichen geschrieben.

## Compose-Verwendung

Netzwerke werden in `compose.yaml` explizit und verständlich benannt:

```yaml
networks:
  public-web:
    name: prd-public-web
  app-internal:
    name: prd-app-internal
  data-postgres:
    name: prd-data-postgres
```

Interne Compose-Referenzen dürfen kurz bleiben. Der tatsächliche Docker-Netzwerkname muss jedoch dem verbindlichen Schema entsprechen.

## Trennungsregeln

- Production, Staging und Development verwenden getrennte Netzwerke.
- Datenbanknetzwerke sind nicht direkt öffentlich erreichbar.
- Nur Edge- oder Public-Netzwerke dürfen veröffentlichte Eintrittspunkte enthalten.
- Management-Netzwerke werden nicht an öffentliche Reverse-Proxy-Routen angebunden.
- Backup-Netzwerke verwenden getrennte Zugangsdaten und möglichst getrennte Ziele.
- Observability erhält nur die für Telemetrie notwendigen Zugriffe.
- Ein Container wird nur mit den tatsächlich benötigten Netzwerken verbunden.

## VLAN-Namen

Verbindliches Schema:

```text
<standort>-<umgebung>-<zone>-vlan<id>
```

Beispiele:

```text
local-prd-management-vlan10
local-prd-app-vlan20
local-prd-data-vlan30
local-stg-app-vlan120
```

Die VLAN-ID wird dezimal ohne führende Nullen angegeben.

VLAN-Namen werden nur verwendet, wenn tatsächlich ein Layer-2-VLAN existiert. Logische Docker-Netzwerke dürfen nicht als VLAN bezeichnet werden.

## Subnetz-Bezeichnungen

Subnetze verwenden in Inventar und Dokumentation:

```text
<umgebung>-<zone>-<zweck>-subnet
```

Beispiele:

```text
prd-app-internal-subnet
prd-data-postgres-subnet
stg-app-internal-subnet
mgmt-management-admin-subnet
```

CIDR-Blöcke sind Attribute des Subnetzes und nicht Bestandteil des dauerhaften Namens.

Nicht zulässig:

```text
10-10-20-0-24
subnet1
new-network
```

## Interne DNS-Zonen

Interne Zonen verwenden ein separates, dokumentiertes DNS-Suffix. Die logische Benennung folgt:

```text
<umgebung>.<zone>.<interne-domain>
```

Beispiele:

```text
prd.app.internal.example.com
prd.data.internal.example.com
stg.app.internal.example.com
mgmt.management.internal.example.com
```

Die konkrete interne Domain wird separat festgelegt. Sie darf keine Secrets, Kunden- oder Personennamen enthalten.

## Zulässige Zeichen

Verbindlich:

- Kleinbuchstaben `a-z`
- Ziffern `0-9`
- Bindestriche als Segmenttrenner
- keine Unterstriche
- keine Leerzeichen
- keine Umlaute oder Sonderzeichen
- kein führender oder abschließender Bindestrich
- keine mehrfachen aufeinanderfolgenden Bindestriche

## Validierungsregex

Docker-Netzwerke:

```regex
^(dev|stg|prd|mgmt|lab)-(public|edge|app|data|observability|backup|management|restricted)-[a-z0-9]+(?:-[a-z0-9]+)*$
```

VLAN-Namen:

```regex
^[a-z0-9]{2,8}-(dev|stg|prd|mgmt|lab)-(public|edge|app|data|observability|backup|management|restricted)-vlan[1-9][0-9]{0,3}$
```

Subnetz-Bezeichnungen:

```regex
^(dev|stg|prd|mgmt|lab)-(public|edge|app|data|observability|backup|management|restricted)-[a-z0-9]+(?:-[a-z0-9]+)*-subnet$
```

## Gültige Beispiele

```text
prd-public-web
prd-edge-proxy
prd-app-internal
prd-data-postgres
prd-observability-logs
prd-backup-transfer
prd-management-admin
stg-app-internal
dev-app-internal
local-prd-data-vlan30
prd-data-postgres-subnet
```

## Verbotene Beispiele

```text
network1
prod_net
public
postgres-network
alex-home
kunde-a-netz
new-network
192-168-1-0-24
prd-data
```

Gründe:

- Umgebung oder Sicherheitszone fehlt
- Unterstriche oder uneinheitliche Schreibweise
- Personen- oder Kundenbezug
- IP-Adresse als dauerhafte Identität
- vergängliche Begriffe wie `new`
- unklarer Zweck

## Monitoring und Inventar

Netzwerke sollen über Labels oder Inventarfelder mindestens folgende Metadaten erhalten:

```text
environment=production
security_zone=data
purpose=postgres
network=prd-data-postgres
```

Firewall-Regeln, Monitoring, Dokumentation und Backups verwenden denselben technischen Netzwerknamen.

## Änderungen und Migration

Eine Umbenennung oder Neuaufteilung muss mindestens berücksichtigen:

1. Compose-Dateien und externe Netzwerke
2. Containerzuordnungen
3. Firewall- und Routing-Regeln
4. Reverse-Proxy-Konfiguration
5. Monitoring und Logging
6. Backup- und Restore-Pfade
7. DNS und interne Service-Referenzen
8. Inventar und Dokumentation

Netzwerkänderungen dürfen nicht direkt in Production getestet werden. Sie durchlaufen Development, Staging und kontrollierte Promotion.

## Ausnahmen

Abweichungen sind nur zulässig, wenn ein Provider oder bestehendes technisches System eine andere Benennung erzwingt.

Jede Ausnahme benötigt:

- Begründung
- betroffenes Netzwerk
- technische Einschränkung
- Sicherheitsauswirkung
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #38

- Schema und zulässige Zeichen sind dokumentiert.
- Umgebung und Sicherheitszone sind erkennbar.
- Docker-Netzwerke, VLANs, Subnetze und interne Zonen sind abgegrenzt.
- typische gültige und verbotene Beispiele sind vorhanden.
- Validierungsregeln und Ausnahmeprozess sind definiert.

## Referenzen

- `docs/03-server-layout.md`
- `docs/21-server-naming-conventions.md`
- `docs/22-container-naming-conventions.md`
- Issue #38
- Epic #35
