# ADR-0004: Infrastructure as Code

- Status: proposed
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Plattform soll auf einem leeren Ersatzserver reproduzierbar aufgebaut werden können. Manuelle, nicht dokumentierte Serveränderungen verhindern Wiederholbarkeit, Review und Disaster Recovery.

## Entscheidung

Alle technisch reproduzierbaren Infrastrukturzustände werden als versionierter Code oder deklarative Konfiguration im Repository gepflegt.

Server-Bootstrap, Systemkonfiguration, Containerbereitstellung, Monitoring, Backup und Restore werden automatisiert. Manuelle Eingriffe sind nur für initiale Vertrauensanker, Secrets, externe Providerfreigaben oder dokumentierte Notfallmaßnahmen zulässig.

Jede Automatisierung muss idempotent oder ausdrücklich als einmaliger Migrationsschritt gekennzeichnet sein.

## Konsequenzen

### Positiv

- Reproduzierbarer Neuaufbau und nachvollziehbare Änderungen.
- Reviews, Tests und Rollbacks werden möglich.
- Abhängigkeit von individuellem Betriebswissen sinkt.

### Negativ

- Initial höherer Dokumentations- und Automatisierungsaufwand.
- Externe Systeme lassen sich eventuell nur teilweise deklarativ verwalten.

### Risiken und Maßnahmen

- Configuration Drift wird durch regelmäßige Prüfungen und erneute Automationsläufe erkannt.
- Manuelle Notfalländerungen müssen nachträglich als Code übernommen werden.

## Betrachtete Alternativen

### Manuelle Runbooks als primäre Betriebsform

- Vorteil: schneller Start.
- Nachteil: fehleranfällig, schwer testbar und nicht zuverlässig reproduzierbar.
- Grund der Ablehnung: widerspricht dem Disaster-Recovery-Ziel.

## Referenzen

- Issue #4
- Epic #2
- `docs/01-architecture.md`
