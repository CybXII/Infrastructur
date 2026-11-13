# ADR-0005: Container Strategy

- Status: proposed
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Plattform soll mehrere unabhängige Dienste mit klaren Abhängigkeiten, reproduzierbaren Deployments und kontrollierter Persistenz betreiben. Gleichzeitig soll die Betriebsplattform für ein kleines Team beherrschbar bleiben.

## Entscheidung

Wir verwenden Docker Engine mit Docker Compose als primäre Containerplattform. Traefik übernimmt Reverse Proxy und TLS-Terminierung.

Dienste werden in getrennten Compose-Projekten mit expliziten Netzwerken, Volumes, Healthchecks, Restart-Policies und gepinnten Image-Versionen betrieben. Persistente Daten werden klar von austauschbaren Containern getrennt.

Kubernetes wird für die erste produktive Plattform nicht eingesetzt.

## Konsequenzen

### Positiv

- Geringere Komplexität als ein Kubernetes-Cluster.
- Gute Reproduzierbarkeit und breite Tool-Unterstützung.
- Bestehende Traefik- und Docker-Erfahrung kann genutzt werden.

### Negativ

- Hochverfügbarkeit und Multi-Node-Orchestrierung sind nicht automatisch enthalten.
- Deployment-Reihenfolge und Rollbacks müssen selbst standardisiert werden.

## Betrachtete Alternativen

### Kubernetes

- Vorteil: umfangreiche Orchestrierung, Scheduling und Self-Healing.
- Nachteil: deutlich höherer Betriebs- und Lernaufwand.
- Grund der Ablehnung: für den initialen Umfang unverhältnismäßig komplex.

### Native Systemdienste ohne Container

- Vorteil: weniger Abstraktion.
- Nachteil: stärkere Hostkopplung und schwierigere Reproduzierbarkeit.
- Grund der Ablehnung: geringere Portabilität und Isolation.

## Referenzen

- Issue #4
- Epic #2
- `docs/01-architecture.md`
