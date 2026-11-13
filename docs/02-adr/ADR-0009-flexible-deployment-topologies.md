# ADR-0009: Flexible Deployment-Topologien und Placement

- Status: proposed
- Datum: 2026-09-15
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Merchfactory Infrastructure wird aktuell auf einem einzelnen VPS als Development-Umgebung aufgebaut. Für den späteren Betrieb soll die Plattform jedoch nicht an eine feste Anzahl physischer Server gekoppelt sein.

Je nach Budget, Last und Betriebsreife müssen mindestens folgende Modelle möglich bleiben:

1. ein einzelner Host für Production, Staging und Development,
2. ein Production-Host für Application und Database plus ein gemeinsamer Development-/Staging-Host,
3. getrennte Production-Application- und Production-Database-Hosts plus ein gemeinsamer Development-/Staging-Host.

Eine Modellierung nach dem Muster "eine Umgebung entspricht genau einem Server" würde diese Ausbaustufen unnötig koppeln und spätere Migrationen erzwingen.

## Entscheidung

Environment, Host-Rolle und physisches Placement werden als drei getrennte Konzepte behandelt.

### Environments

Verbindliche Environments:

- `development`
- `staging`
- `production`

Ein Environment beschreibt Release-Stand, Konfiguration, Secrets und Datenkontext. Es beschreibt nicht die Anzahl oder Identität physischer Hosts.

### Host-Rollen

Verbindliche logische Host-Rollen:

- `host_baseline`
- `edge`
- `application`
- `database`
- `monitoring_server`
- `monitoring_agent`
- `backup_agent`

Ein physischer Host darf mehrere Rollen tragen. Eine Rolle darf in einer anderen Topologie auf einen anderen Host verschoben werden, ohne die fachliche Service-Struktur zu ändern.

### Placement

Die konkrete Zuordnung von Rollen und Environments zu physischen Hosts ist ein Placement. Die Plattform unterstützt verbindlich vier Profile:

| Profil | Hosts | Verwendung |
|---|---:|---|
| `development-only` | 1 | aktuelle Aufbauphase, nur Development |
| `compact` | 1 | Production + Staging + Development auf einem Host |
| `standard` | 2 | Production App + DB gemeinsam; Development + Staging gemeinsam |
| `split-production` | 3 | Production App und DB getrennt; Development + Staging gemeinsam |

Die maschinenlesbare Quelle ist `configuration/deployment-topologies.json`.

### Gemeinsame Hosts

Teilen mehrere Environments einen Host, bleibt logische Isolation verpflichtend. Mindestens getrennt werden:

- Compose-Projekt
- Docker-Netzwerke
- persistente Daten
- Runtime-Secrets
- Datenbank-Credentials

Production, Staging und Development dürfen nicht dieselben Datenbank-Credentials oder persistenten Datensätze verwenden.

### Application-/Database-Kopplung

Anwendungen dürfen keinen festen physischen Datenbankhost voraussetzen. Die Datenbankverbindung wird über einen environment-spezifischen Endpoint beziehungsweise Runtime-Wert wie `DATABASE_HOST` aufgelöst.

Damit kann PostgreSQL:

- auf demselben Host wie die Anwendung,
- auf einem anderen Host,
- oder später hinter einem internen DNS-/Service-Endpunkt

betrieben werden, ohne das Anwendungsdeployment strukturell neu zu bauen.

### Monitoring

`monitoring_agent` läuft auf jedem verwalteten Host. `monitoring_server` wird pro Topologie genau einmal platziert.

Dadurch können Node Exporter, cAdvisor und Collector hostnah laufen, während Prometheus, Loki, Grafana und Alertmanager zentral betrieben werden.

### Aktueller Zustand

Bis Staging oder Production tatsächlich bereitgestellt werden, ist `development-only` das verbindliche aktuelle Profil.

Die Definition der späteren Profile erzeugt keine laufenden Staging- oder Production-Systeme und erfordert heute keine zusätzlichen VPS.

## Konsequenzen

### Positiv

- Serveranzahl kann an Budget und Last angepasst werden.
- Ein späterer Wechsel von 1 auf 2 oder 3 Hosts erfordert keine neue Servicearchitektur.
- Development und Staging können kostengünstig einen Host teilen.
- Production Application und Database können zunächst gemeinsam und später getrennt betrieben werden.
- CI kann Topologieannahmen maschinenlesbar gegen Drift prüfen.

### Negativ

- Inventories und Deploymentlogik benötigen eine zusätzliche Placement-Schicht.
- Gemeinsame Hosts besitzen eine gemeinsame Fehlerdomäne.
- Ein `compact`-Betrieb bietet trotz logischer Isolation keine physische Isolation zwischen Environments.

### Risiken und Maßnahmen

- **Fehlkonfiguration auf Shared Hosts:** verpflichtende Isolation über Netzwerke, Daten, Secrets und Credentials.
- **Development beeinflusst Production:** Ressourcenlimits, getrennte Compose-Projekte und environment-spezifische Deployments.
- **Falsche Datenbankzuordnung:** getrennte Credentials und Endpoint-Indirection.
- **Hostausfall betrifft mehrere Environments:** akzeptiertes Risiko für kompakte Profile; Split-Topologien bleiben verfügbar.

## Betrachtete Alternativen

### Ein dedizierter Server pro Environment und Rolle

- Vorteil: maximale physische Trennung.
- Nachteil: hoher Kosten- und Betriebsaufwand.
- Grund der Ablehnung: für die aktuelle Größe und Budgetlage unverhältnismäßig und unnötig starr.

### Eine Umgebung entspricht genau einem Host

- Vorteil: einfaches Inventarmodell.
- Nachteil: verhindert App-/DB-Split und erzwingt zusätzliche Hosts für Development und Staging.
- Grund der Ablehnung: widerspricht dem gewünschten flexiblen Ausbau.

## Umsetzung und Übergang

- Aktuelles Profil bleibt `development-only`.
- Bestehender Development-Bootstrap bleibt unverändert funktionsfähig.
- Neue Deployments müssen Environment und Placement getrennt behandeln.
- Spätere Host-Inventories referenzieren Rollen statt impliziter Environment-Host-Zuordnung.
- Wechsel zwischen den Profilen erfolgt kontrolliert über Inventar-/Placement-Änderung und Migration persistenter Daten.

## Referenzen

- Issue: Refs #271
- Architektur: `docs/01-architecture.md`, `docs/03-server-layout.md`, `docs/06-deployment.md`
- Verwandte ADRs: ADR-0002, ADR-0004, ADR-0005, ADR-0008
