# ADR-0003: Repository Directory Layout

- Status: proposed
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Das Repository soll Bootstrap, Konfiguration, Deployments, Monitoring, Backups, Restore-Prozesse, Tests und Dokumentation langfristig aufnehmen. Ohne verbindliche Struktur entstehen widersprüchliche Ablagen und versteckte Abhängigkeiten.

## Entscheidung

Wir verwenden eine funktionsorientierte Top-Level-Struktur:

```text
.github/
bootstrap/
configuration/
deployment/
monitoring/
backup/
restore/
scripts/
templates/
tests/
docs/
examples/
```

Jeder Bereich erhält eine README mit Zweck, Verantwortungsgrenzen, Eingaben, Ausgaben und Abhängigkeiten. Umgebungsspezifische Werte werden von wiederverwendbaren Komponenten getrennt.

Die verbindlichen Verantwortungsbereiche, Unterstrukturen, Benennungsregeln, Erweiterungskonventionen und verbotenen Ablagemuster sind in `docs/09-repository-structure.md` definiert.

Neue Top-Level-Verzeichnisse dürfen nur über eine ergänzende Architekturentscheidung eingeführt werden.

## Konsequenzen

### Positiv

- Zuständigkeiten und Auffindbarkeit werden verbessert.
- Komponenten können unabhängig getestet und erweitert werden.
- Dokumentation und Implementierung bleiben klar getrennt, aber verlinkt.
- Mehrere Server, Dienste und Umgebungen können ohne strukturelle Duplikation abgebildet werden.
- Milestone v0.2 besitzt eine konkrete Umsetzungsgrundlage.

### Negativ

- Querschnittsfunktionen benötigen bewusst definierte Schnittstellen.
- Bestehende Dateien müssen später in die Zielstruktur migriert werden.
- Jeder Bereich benötigt eine gepflegte README und klare Ownership.

### Risiken und Maßnahmen

- Risiko unklarer Ablageorte: verbindliche Verantwortungsgrenzen in `docs/09-repository-structure.md`.
- Risiko umgebungsspezifischer Duplikation: Trennung von gemeinsamen Komponenten und Overlays.
- Risiko ungeplanter Top-Level-Strukturen: neue Hauptverzeichnisse nur über ADR.
- Risiko von Secrets im Repository: Laufzeitbereitstellung über das vorgesehene Secret-Management.

## Betrachtete Alternativen

### Struktur ausschließlich nach Servern

- Vorteil: direkte Zuordnung zu einzelnen Hosts.
- Nachteil: hohe Duplikation und schlechte Wiederverwendbarkeit.
- Grund der Ablehnung: Serverrollen sollen deklarativ kombiniert werden können.

### Struktur ausschließlich nach Umgebungen

- Vorteil: alle Dateien einer Umgebung befinden sich an einer Stelle.
- Nachteil: gemeinsame Logik wird zwischen Development, Staging und Production dupliziert.
- Grund der Ablehnung: erhöht Drift und erschwert konsistente Tests.

### Monolithisches Verzeichnis für sämtliche Infrastruktur

- Vorteil: geringer initialer Strukturaufwand.
- Nachteil: unklare Ownership, steigende Kopplung und schlechte Skalierbarkeit.
- Grund der Ablehnung: nicht tragfähig für mehrere Dienste, Serverrollen und Betriebsprozesse.

## Referenzen

- Issue #10
- Issue #4
- Epic #2
- `docs/01-architecture.md`
- `docs/09-repository-structure.md`
