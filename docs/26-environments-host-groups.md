# Umgebungen und Hostgruppen

## Zweck

Dieses Dokument definiert die verbindlichen Betriebsumgebungen, Hostgruppen und Regeln zur Konfigurationsvererbung der Merchfactory Infrastructure Platform.

## Umgebungen

| Umgebung | Kennung | Git-Quelle | Zweck | Zulässige Daten |
|---|---|---|---|---|
| Development | `dev` | `development` | Integration, technische Entwicklung und frühe Tests | synthetisch oder anonymisiert |
| Test | `test` | Arbeitsbranch oder expliziter Teststand | isolierte Funktions-, Migrations- und Wiederherstellungstests | ausschließlich synthetisch |
| Staging | `stg` | `staging` | produktionsnahe Abnahme und Release Candidate | keine unkontrollierte Produktivkopie |
| Production | `prd` | `main` | freigegebener produktiver Betrieb | produktiv |
| Management | `mgmt` | freigegebene Management-Konfiguration | umgebungsübergreifende Administration, Backup und Runner | keine fachlichen Produktivdaten |
| Lab | `lab` | expliziter Versuchszweig oder lokaler Stand | zeitlich begrenzte Experimente | synthetisch |

## Abgrenzungsregeln

- Jede Umgebung besitzt eigene Konfigurationen, Secrets, Netzwerke und Datenbestände.
- Production-Secrets dürfen nur in Production-Deployments referenziert werden.
- Staging und Development verwenden eigene technische Benutzer und SSH-Schlüssel.
- Test- und Lab-Systeme erhalten keinen direkten Zugriff auf produktive Datenbanken.
- Produktive Daten dürfen nur nach dokumentierter Anonymisierung außerhalb von Production verwendet werden.
- Promotion erfolgt ausschließlich über `development -> staging -> main`.
- Test und Lab sind keine Abkürzung für den Promotion-Prozess.

## Hostgruppen nach Rolle

| Gruppe | Zweck | Typische Hosts |
|---|---|---|
| `edge` | Reverse Proxy, TLS und öffentliche Eintrittspunkte | `prd-fsn-edge-01` |
| `application` | Anwendungen, APIs, Worker und Integrationen | `prd-fsn-app-01` |
| `database` | PostgreSQL und weitere zustandsbehaftete Datendienste | `prd-fsn-db-01` |
| `observability` | Monitoring, Logging und Alerting | `prd-fsn-obs-01` |
| `backup` | Backup, Restore und Offsite-Transfer | `prd-fsn-bkp-01` |
| `management` | Bootstrap, Administration und Konfigurationssteuerung | `mgmt-local-mgmt-01` |
| `runner` | Build- und Automatisierungsrunner | `mgmt-local-runner-01` |
| `storage` | dedizierte Datei- oder Objektspeicher | `prd-fsn-storage-01` |
| `ai` | lokale KI- und rechenintensive Verarbeitung | `lab-local-ai-01` |

Ein Host kann mehreren logischen Rollen dienen. Die primäre Rolle bestimmt den Hostnamen; zusätzliche Rollen werden über Inventargruppen abgebildet.

## Hostgruppen nach Standort

Standortgruppen verwenden die im Servernamensstandard definierten Kennungen, beispielsweise:

```text
fsn
nbg
hel
local
cloud
```

Beispiele für kombinierte Gruppen:

```text
prd
prd_fsn
prd_application
prd_fsn_application
stg_application
mgmt_runner
```

In Ansible dürfen Gruppen Unterstriche verwenden, obwohl technische Host-, Datei- und Containernamen Bindestriche verwenden.

## Empfohlenes Ansible-Inventar

```text
inventories/
├── development/
│   ├── hosts.yaml
│   ├── group-vars/
│   └── host-vars/
├── test/
│   ├── hosts.yaml
│   ├── group-vars/
│   └── host-vars/
├── staging/
│   ├── hosts.yaml
│   ├── group-vars/
│   └── host-vars/
├── production/
│   ├── hosts.yaml
│   ├── group-vars/
│   └── host-vars/
└── management/
    ├── hosts.yaml
    ├── group-vars/
    └── host-vars/
```

## Beispielinventar

```yaml
all:
  children:
    prd:
      children:
        prd_fsn:
          children:
            prd_edge:
              hosts:
                prd-fsn-edge-01:
            prd_application:
              hosts:
                prd-fsn-app-01:
            prd_database:
              hosts:
                prd-fsn-db-01:
```

## Konfigurationsvererbung

Die Vererbung erfolgt von allgemein nach spezifisch:

```text
all
-> Umgebung
-> Standort
-> Rolle
-> kombinierte Gruppe
-> Host
```

Beispiel:

```text
group_vars/all.yaml
group_vars/prd.yaml
group_vars/fsn.yaml
group_vars/application.yaml
group_vars/prd_fsn_application.yaml
host_vars/prd-fsn-app-01.yaml
```

Spezifischere Werte dürfen allgemeinere Werte überschreiben. Host-spezifische Variablen sind nur zulässig, wenn die Abweichung technisch notwendig und dokumentiert ist.

## Verantwortlichkeit der Ebenen

### Global

- gemeinsame Zeitzone und Locale
- Basispakete
- allgemeines SSH-Hardening
- Standard-Logging
- gemeinsame Monitoring-Metadaten

### Umgebung

- Domain- und Endpoint-Zuordnung
- Ressourcenklassen
- Backup- und Aufbewahrungsniveau
- Deployment-Pfade
- Umgebungsspezifische Feature-Schalter

### Standort

- Provider- und Netzwerkeigenschaften
- interne DNS-Resolver
- Zeitsynchronisation
- Offsite- oder Peering-Ziele

### Rolle

- Dienstpakete
- Firewall-Anforderungen
- Monitoring-Exporter
- Verzeichnis- und Volume-Anforderungen

### Host

- IP-Adressen oder Provider-IDs
- bewusst abweichende Hardwareeigenschaften
- zeitlich begrenzte Migrationseinstellungen

## Secrets

Secrets werden nicht in normalen Inventardateien gespeichert.

Zulässig sind:

- GitHub Repository-Secrets für Deployments
- verschlüsselte Ansible-Vault-Dateien, sobald dieses Verfahren eingeführt und dokumentiert ist
- serverseitig geschützte Secret-Dateien außerhalb des Repositorys

Secret-Namen folgen der Umgebungszuordnung, beispielsweise:

```text
DEVELOPMENT_SSH_HOST
STAGING_SSH_HOST
PRODUCTION_SSH_HOST
```

## Verbotene Muster

Nicht zulässig sind:

- eine gemeinsame ungetrennte Inventardatei für alle Umgebungen
- Production-Zugangsdaten in Development- oder Testvariablen
- produktive Hostnamen in Lab-Gruppen ohne dokumentierten Grund
- Host-spezifische Kopien ganzer Rollenkonfigurationen
- nicht dokumentierte Overrides
- Kundennamen als Hostgruppen
- Gruppen wie `misc`, `other`, `server1` oder `new-hosts`

## Änderungen

Änderungen an Umgebungen oder Hostgruppen müssen mindestens prüfen:

1. Inventar und Gruppenhierarchie
2. Secrets und technische Benutzer
3. Netzwerke und Firewall
4. Monitoring und Logging
5. Backup- und Restore-Zuordnung
6. Deployment-Workflows
7. DNS und Zertifikate
8. Dokumentationsreferenzen

Änderungen an Production werden zuerst in Development und Staging validiert.

## Ausnahmen

Abweichungen benötigen:

- technische Begründung
- betroffene Umgebung und Hosts
- Sicherheits- und Betriebswirkung
- verantwortliche Person
- Gültigkeitsdauer oder Migrationsplan
- Referenz auf Issue oder ADR

## Definition of Done für Issue #42

- Development, Test, Staging und Production sind beschrieben.
- Management und Lab sind eindeutig abgegrenzt.
- Hostgruppen nach Rolle und Standort sind definiert.
- Konfigurationsvererbung und Override-Reihenfolge sind dokumentiert.
- Secret-, Daten- und Promotion-Grenzen sind festgelegt.

## Referenzen

- `docs/03-server-layout.md`
- `docs/18-github-environments.md`
- `docs/21-server-naming-conventions.md`
- `docs/23-network-naming-conventions.md`
- Issue #42
- Epic #35
