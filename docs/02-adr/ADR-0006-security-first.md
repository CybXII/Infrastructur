# ADR-0006: Security First

- Status: proposed
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Plattform verarbeitet produktionsrelevante Systeme, Zugangsdaten und teilweise kundenbezogene Daten. Sicherheitsmaßnahmen dürfen deshalb nicht erst nachträglich ergänzt werden.

## Entscheidung

Security wird als verbindliche Querschnittsanforderung für Architektur, Code, Deployment und Betrieb behandelt.

Es gelten mindestens: Least Privilege, standardmäßig geschlossene Netzwerkpfade, gehärtete Serverkonfiguration, schlüsselbasierter SSH-Zugriff, Trennung von Secrets und Code, verschlüsselte Übertragung, regelmäßige Updates, nachvollziehbare Änderungen, zentrale Protokollierung und getestete Wiederherstellung.

Ausnahmen müssen dokumentiert, zeitlich begrenzt und mit kompensierenden Maßnahmen versehen werden.

## Konsequenzen

### Positiv

- Risiken werden früh im Design berücksichtigt.
- Sicherheitskontrollen lassen sich automatisieren und reviewen.
- Der spätere Produktionsreview wird planbarer.

### Negativ

- Höherer Aufwand bei Erstimplementierung und Änderungen.
- Manche Komfortfunktionen werden zugunsten geringerer Angriffsfläche eingeschränkt.

## Betrachtete Alternativen

### Security Hardening nach funktionaler Fertigstellung

- Vorteil: kurzfristig schnellere Implementierung.
- Nachteil: teure Nacharbeiten und strukturelle Sicherheitslücken.
- Grund der Ablehnung: nicht akzeptabel für produktive Infrastruktur.

## Referenzen

- Issue #4
- Epic #2
- `docs/01-architecture.md`
