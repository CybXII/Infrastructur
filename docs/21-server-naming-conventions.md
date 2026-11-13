# Server-Namenskonventionen

## Zweck

Dieses Dokument definiert das verbindliche Namensschema für physische und virtuelle Server der Merchfactory Infrastructure Platform.

Ziel ist, dass Hostnamen in Betriebssystem, DNS, Monitoring, Inventar, Backup und Dokumentation eindeutig, stabil und maschinenlesbar verwendet werden können.

## Verbindliches Schema

Servernamen verwenden folgendes Format:

```text
<umgebung>-<standort>-<rolle>-<nummer>
```

Beispiel:

```text
prd-fsn-app-01
```

Die Segmente bedeuten:

| Segment | Bedeutung | Beispiel |
|---|---|---|
| `umgebung` | Betriebsumgebung | `dev`, `stg`, `prd`, `mgmt` |
| `standort` | physischer oder logischer Standort | `fsn`, `nbg`, `local` |
| `rolle` | primäre technische Serverrolle | `edge`, `app`, `db`, `obs`, `bkp`, `mgmt`, `runner` |
| `nummer` | zweistellige laufende Nummer | `01`, `02` |

## Erlaubte Umgebungskennungen

| Kennung | Bedeutung |
|---|---|
| `dev` | Development |
| `stg` | Staging |
| `prd` | Production |
| `mgmt` | umgebungsübergreifende Management-Systeme |
| `lab` | isolierte Labor- oder Testsysteme außerhalb des regulären Promotion-Flows |

Neue Kennungen dürfen nur nach dokumentierter Erweiterung dieses Standards eingeführt werden.

## Standortkennungen

Standortkennungen bestehen aus zwei bis acht Kleinbuchstaben oder Ziffern.

Beispiele:

| Kennung | Bedeutung |
|---|---|
| `fsn` | Hetzner Falkenstein |
| `nbg` | Hetzner Nürnberg |
| `hel` | Hetzner Helsinki |
| `local` | interne Merchfactory-Hardware |
| `cloud` | logisch zugeordnetes Cloud-System ohne dauerhafte Standortbindung |

Ein Providername darf nur verwendet werden, wenn kein stabilerer Standortcode verfügbar ist. Standortkennungen müssen in der Infrastruktur-Dokumentation eindeutig erklärt werden.

## Rollenkennungen

Die Rolle beschreibt die primäre Verantwortung des Hosts, nicht jede darauf ausgeführte Anwendung.

| Kennung | Serverrolle |
|---|---|
| `edge` | Reverse Proxy, TLS und öffentliche Eintrittspunkte |
| `app` | Anwendungs- und Integrationsdienste |
| `db` | Datenbankdienste |
| `obs` | Monitoring, Logging und Alerting |
| `bkp` | Backup und Restore-Infrastruktur |
| `mgmt` | Management, Bootstrap und Administration |
| `runner` | Build- oder GitHub-Actions-Runner |
| `ai` | lokale KI- und rechenintensive Verarbeitung |
| `storage` | dedizierter Datei- oder Objektspeicher |

Bei konsolidierten Hosts wird die wichtigste betriebliche Rolle verwendet. Ein einzelner Start-VPS, der Edge, Anwendungen, Datenbank und Monitoring vereint, erhält daher beispielsweise die Rolle `app` oder `edge` entsprechend seiner primären Betriebsfunktion. Die zusätzlich konsolidierten Rollen werden im Inventar dokumentiert und nicht in den Hostnamen eingebaut.

## Laufende Nummer

Die Nummer ist immer zweistellig:

```text
01
02
03
```

Nummern werden pro Kombination aus Umgebung, Standort und Rolle vergeben.

Ein außer Betrieb genommener Name wird nicht unmittelbar neu vergeben. Dadurch bleiben historische Logs, Backups und Monitoring-Daten eindeutig zuordenbar.

## Beispiele

```text
prd-fsn-edge-01
prd-fsn-app-01
prd-fsn-db-01
prd-fsn-obs-01
prd-fsn-bkp-01
stg-fsn-app-01
dev-local-app-01
mgmt-local-mgmt-01
lab-local-ai-01
```

## DNS-Kompatibilität

Hostnamen müssen mit DNS und den üblichen Betriebssystemkonventionen kompatibel sein.

Verbindliche Regeln:

- ausschließlich Kleinbuchstaben `a-z`
- Ziffern `0-9` sind zulässig
- Segmente werden mit genau einem Bindestrich getrennt
- keine Unterstriche
- keine Leerzeichen
- keine Umlaute oder Sonderzeichen
- der Name beginnt und endet nicht mit einem Bindestrich
- maximal 63 Zeichen pro DNS-Label
- der vollständige Hostname bleibt möglichst unter 32 Zeichen

Der interne oder öffentliche FQDN wird aus dem Hostnamen und einer separat verwalteten Domain gebildet, beispielsweise:

```text
prd-fsn-app-01.internal.example.com
```

Die konkrete Domain ist nicht Bestandteil dieses Standards und darf keine Secrets oder personenbezogenen Informationen enthalten.

## Monitoring und Inventar

Der technische Hostname ist die primäre Host-ID in:

- Betriebssystemkonfiguration
- Ansible-Inventar
- Monitoring und Alerting
- zentralem Logging
- Backup-Metadaten
- Betriebsdokumentation
- Incident- und Wartungsprotokollen

Zusätzliche Anzeigenamen sind erlaubt, dürfen die technische Host-ID aber nicht ersetzen.

Empfohlene Monitoring-Labels:

```text
environment=production
location=fsn
role=app
host=prd-fsn-app-01
```

## Verbotene Muster

Nicht zulässig sind insbesondere:

```text
server1
new-server
alex-vps
production_server
prodserver
web01
odoo-server
kunde-a-server
192-0-2-10
```

Gründe:

- keine erkennbare Umgebung oder Rolle
- persönliche oder kundenspezifische Namen
- Unterstriche oder uneinheitliche Schreibweise
- Bindung an eine einzelne Anwendung statt an die Serverrolle
- Verwendung einer IP-Adresse als dauerhafte Identität
- fehlende Standort- oder Nummernlogik

## Keine sensiblen Informationen im Namen

Hostnamen enthalten niemals:

- Kundennamen
- Personennamen
- Zugangsdaten
- interne Projekt-Codenamen mit Schutzbedarf
- vollständige IP-Adressen
- Vertrags- oder Accountnummern
- Sicherheitsklassifikationen

## Umbenennung bestehender Systeme

Eine Umbenennung erfolgt nur kontrolliert, da Hostnamen in mehreren Systemen referenziert werden können.

Vor der Änderung sind mindestens zu prüfen:

1. DNS-Einträge
2. SSH-Konfiguration und Known Hosts
3. Monitoring- und Logging-Zuordnung
4. Backup-Jobs und Restore-Pfade
5. Ansible-Inventar
6. Zertifikate und interne Dienste
7. Firewall- und Zugriffskontrollen
8. Dokumentation und CMDB beziehungsweise Inventar

Historische Namen werden mit Gültigkeitszeitraum dokumentiert.

## Validierung

Ein gültiger Hostname entspricht grundsätzlich diesem regulären Ausdruck:

```regex
^(dev|stg|prd|mgmt|lab)-[a-z0-9]{2,8}-(edge|app|db|obs|bkp|mgmt|runner|ai|storage)-[0-9]{2}$
```

Die technische Validierung kann später in Ansible, CI-Prüfungen oder Inventar-Skripten umgesetzt werden.

## Ausnahmen

Abweichungen sind nur zulässig, wenn ein externer Provider oder ein bestehendes technisches System eine andere Benennung erzwingt.

Jede Ausnahme benötigt:

- Begründung
- betroffenen Host
- technische Einschränkung
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #36

- Umgebung, Standort, Rolle und laufende Nummer sind im Schema enthalten.
- zulässige Kennungen sind dokumentiert.
- gültige und verbotene Beispiele sind vorhanden.
- DNS-, Monitoring- und Inventarkompatibilität sind geregelt.
- Validierungsregex und Ausnahmeprozess sind definiert.

## Referenzen

- `docs/03-server-layout.md`
- `docs/17-github-actions-foundation.md`
- Issue #36
- Epic #35
