# Deployment-Konzept

## Zweck

Dieses Dokument definiert den technischen und organisatorischen Ablauf für Deployments in Development, Staging und Produktion. Es ergänzt `docs/05-cicd.md` um konkrete Freigabe-, Rollback- und Fehlerverfahren.

## Grundprinzipien

- Deployments sind reproduzierbar und auf einen Commit-SHA oder ein unveränderliches Artefakt zurückführbar.
- Staging und Produktion verwenden dasselbe Artefakt.
- Konfigurationen und Secrets sind je Umgebung getrennt.
- Änderungen an persistenten Daten benötigen vorab eine Wiederherstellungsstrategie.
- Produktive Änderungen erfolgen nur über freigegebene Pull Requests und GitHub Environments.
- Git-Environment, Host-Rolle und physisches Placement sind getrennte Konzepte; ein Environment setzt keinen dedizierten Server voraus.

## Deployment-Stufen

### Development

Zweck:

- Integration laufender Änderungen
- frühe Validierung von Konfiguration und Automatisierung
- nichtproduktive Tests

Quelle:

- Branch `development`

Freigabe:

- erfolgreiche CI
- kein manueller Production-Approval erforderlich

### Staging

Zweck:

- produktionsnahe Verifikation
- Prüfung von Netzwerk, Secrets, Persistenz und Monitoring
- Abnahme des Release Candidates

Quelle:

- Branch `staging`

Freigabe:

- Release-PR von `development` nach `staging`
- erfolgreiche CI
- manueller Approval für das Environment `staging`

### Produktion

Zweck:

- stabiler und freigegebener Plattformbetrieb

Quelle:

- Branch `main`

Freigabe:

- Release-PR von `staging` nach `main`
- erfolgreiche Staging-Verifikation
- manueller Approval für das Environment `production`
- dokumentierter Rollback-Plan

## Zielauflösung und Deployment-Topologie

Ein Deployment wird in dieser Reihenfolge aufgelöst:

```text
Git-Branch / Release
        ↓
Environment
        ↓
benötigte Rollen
        ↓
Topology Placement
        ↓
physischer Host
```

Die verbindlichen Placement-Profile sind in `configuration/deployment-topologies.json` definiert:

- `development-only`: aktueller Zustand, ein Development-Host
- `compact`: ein Host für Production, Staging und Development
- `standard`: Production App + DB gemeinsam, Development + Staging auf einem zweiten Host
- `split-production`: Production App und DB getrennt, Development + Staging auf einem dritten Host

Ein Merge nach `development` darf deshalb aktuell ausschließlich das aktive Development-Placement adressieren. Die bloße Existenz von `staging` und `production` im Repository erzeugt keine laufenden Zielsysteme.

Bei Shared Hosts bleiben Compose-Projekte, Netzwerke, Persistenz, Secrets und Datenbank-Credentials je Environment getrennt. Die Application-/Database-Verbindung wird über einen environment-spezifischen Endpoint aufgelöst, damit ein späterer Wechsel von Co-Location zu getrennten Hosts ohne strukturellen Umbau möglich bleibt.

Referenz: ADR-0009.

## Standardablauf

1. Release Scope und betroffene Komponenten bestimmen.
2. CI-Prüfungen und Security Scans ausführen.
3. Artefakt bauen und eindeutig mit Commit-SHA kennzeichnen.
4. Konfigurationsänderungen als Diff oder Plan prüfen.
5. Backup-Anforderung für persistente Daten bewerten.
6. Deployment in Zielumgebung freigeben.
7. Vorabprüfungen ausführen.
8. Änderung ausrollen.
9. Health Checks und Smoke Tests durchführen.
10. Monitoring und Logs während der Stabilisierungsphase beobachten.
11. Deployment-Ergebnis dokumentieren.

## Vorabprüfungen

Vor jedem Deployment sind mindestens zu prüfen:

- Zielhost und Zielumgebung korrekt
- verfügbare Kapazität für CPU, RAM und Speicher
- erwartete Container-Images mit vollständigem Registry-Namen und SHA-256-Digest
- Imagequelle entspricht `configuration/container-image-policy.json`
- Vulnerability-Gate für den zu deployenden Digest ist erfolgreich
- First-Party-Provenance ist gegen das erwartete Quellrepository verifiziert
- benötigte Secrets vorhanden, aber nicht ausgegeben
- Netzwerkabhängigkeiten erreichbar
- Backup aktuell, wenn Daten oder Volumes betroffen sind
- Rollback-Version verfügbar
- Wartungsfenster und Kommunikationsweg geklärt

Fehlt eine kritische Voraussetzung, wird das Deployment nicht gestartet.

## Deployment-Verfahren

Bevorzugt werden deklarative und idempotente Verfahren:

- Infrastructure as Code für Infrastrukturzustand,
- Konfigurationsmanagement für Hosts,
- versionierte Compose-, Stack- oder Orchestrierungsdefinitionen,
- unveränderliche Container-Images.

Für containerisierte Standardservices ist `deployment/service-release.py` die Referenzimplementierung für kontrollierte Digest-Updates und Rollbacks. Das verbindliche Verfahren steht in `docs/57-update-rollback.md`.

Der Controller trennt Compose-Konfiguration vom freigegebenen Laufzeit-Digest über `SERVICE_IMAGE_REFERENCE`, verwaltet den letzten bekannten guten Zustand und verifiziert Update sowie Rollback.

Manuelle Änderungen auf Produktivsystemen sind nur zur Incident-Begrenzung zulässig und müssen anschließend in Repository und Dokumentation nachgezogen werden.

## Datenbank- und Persistenzänderungen

Änderungen an persistenten Daten werden gesondert behandelt:

- Vorwärts- und Rückwärtskompatibilität bewerten
- Migration separat testen
- Backup oder Snapshot unmittelbar vor kritischer Migration
- Dauer und Sperrverhalten dokumentieren
- Wiederherstellungszeit abschätzen

Destruktive Migrationen benötigen eine explizite Freigabe. Ein reiner Code-Rollback reicht nicht aus, wenn das Datenschema inkompatibel verändert wurde.

## Verifikation

Nach dem Deployment werden mindestens geprüft:

- alle erwarteten Dienste laufen
- Health Checks sind erfolgreich
- externe Endpunkte antworten erwartungsgemäß
- keine neuen kritischen Fehler in Logs
- Metriken und Ressourcennutzung liegen im erwarteten Bereich
- persistente Daten sind erreichbar und konsistent
- Backup-, Monitoring- und Alerting-Komponenten funktionieren

Für geschäftskritische Dienste werden zusätzlich fachliche Smoke Tests ausgeführt.

## Rollback-Strategien

### Artefakt-Rollback

Rückkehr zu einem bereits freigegebenen, weiterhin vorhandenen und per Digest referenzierten Container-Image oder Commit-SHA. Rollback-Digests sind von automatischer Registry-Bereinigung geschützt.

Der Service-Release-Controller schützt den aktuellen und bis zu zwei vorherige bekannte gute Releasezustände. Ein automatischer Artefakt-Rollback ist nur für datenkompatible Änderungen zulässig; destruktive Migrationen benötigen eine manuelle Restore-/Roll-forward-Entscheidung.

Geeignet für:

- fehlerhafte Anwendungsversionen
- fehlerhafte Konfiguration ohne irreversible Datenänderung

### Konfigurations-Rollback

Wiederherstellung der vorherigen versionierten Konfiguration.

Geeignet für:

- Proxy-, Firewall-, Service- oder Routingfehler

### Daten-Restore

Wiederherstellung aus Backup oder Snapshot.

Geeignet für:

- beschädigte Daten
- irreversible oder fehlerhafte Migrationen

Ein Daten-Restore ist ein schwerwiegender Eingriff und benötigt eine Entscheidung zum akzeptierten Datenverlust innerhalb des festgelegten RPO.

### Roll-forward

Gezielte Korrektur mit einer neuen Version, wenn ein Rollback technisch riskanter oder wegen Datenmigrationen nicht möglich ist.

## Rollback-Entscheidung

Ein Rollback wird ausgelöst, wenn mindestens eines der folgenden Kriterien zutrifft:

- kritischer Dienst nicht verfügbar
- Datenintegrität gefährdet
- Sicherheitsrisiko entstanden
- zentrale Health Checks dauerhaft fehlschlagen
- Fehler nicht innerhalb des definierten Stabilisierungsfensters behebbar

Die Entscheidung trifft der Release- oder Betriebsverantwortliche. Bei Sicherheitsvorfällen gelten zusätzlich die Incident-Regeln aus `docs/04-security.md`.

## Fehlgeschlagene Deployments

Bei Fehlern:

1. weitere Ausrollung stoppen
2. Zustand, Logs und Zeitpunkte sichern
3. Auswirkungen bewerten
4. Rollback oder Roll-forward entscheiden
5. Stakeholder informieren, wenn Verfügbarkeit oder Daten betroffen sind
6. Ursache und Maßnahmen dokumentieren
7. erneutes Deployment erst nach neuer Freigabe

## Notfalländerungen

Emergency Changes sind nur zulässig, wenn ein unmittelbares Sicherheits- oder Verfügbarkeitsrisiko besteht.

Mindestanforderungen:

- Incident-Referenz
- kleinstmöglicher Scope
- dokumentierte Änderung
- nachträglicher Pull Request
- nachträgliches Review
- Ursachenanalyse nach Stabilisierung

Notfalländerungen dürfen den Repository-Stand nicht dauerhaft vom produktiven Zustand abweichen lassen.

## Secrets und Berechtigungen

- Secrets liegen ausschließlich in dafür vorgesehenen Secret Stores oder GitHub Environments.
- Deployment-Jobs erhalten nur die für die Zielumgebung notwendigen Berechtigungen.
- Produktionszugriff ist getrennt von Development und Staging.
- Logs dürfen keine Secret-Werte enthalten.
- Temporäre Credentials werden nach Verwendung widerrufen oder laufen automatisch ab.

## Wartung und Kommunikation

Produktive Deployments enthalten:

- geplanten Zeitpunkt
- erwartete Auswirkungen
- verantwortliche Person
- Verifikationskriterien
- Rollback-Kriterien
- Kommunikationsweg für Störungen

Für Änderungen mit erwarteter Unterbrechung wird ein Wartungsfenster verwendet.

## Deployment-Protokoll

Für Standardservices wird der lokale Releasezustand zusätzlich in `state.json` dokumentiert. Dieser enthält keine Secrets und dient als operative Referenz für den aktuellen und vorherige bekannte gute Digests.

Pro Deployment werden mindestens festgehalten:

- Datum und Uhrzeit
- Zielumgebung
- Commit-SHA oder Artefaktversion
- ausführende und freigebende Person
- betroffene Komponenten
- Backup-Referenz, falls relevant
- Ergebnis der Verifikation
- Rollback oder Abweichungen

## Abhängigkeiten

Dieses Konzept ist mit folgenden Dokumenten abzustimmen:

- `docs/03-server-layout.md`
- `docs/04-security.md`
- `docs/05-cicd.md`
- `docs/02-adr/ADR-0002-github-environments.md`
- `docs/02-adr/ADR-0004-infrastructure-as-code.md`
- `docs/02-adr/ADR-0005-container-strategy.md`
- `docs/02-adr/ADR-0006-security-first.md`
- `docs/02-adr/ADR-0007-backup-strategy.md`
- `docs/57-update-rollback.md`

## Offene Entscheidungen

- konkrete Deployment-Werkzeuge
- konkrete Health- und Smoke-Tests je Dienst
- Wartungsfenster und Stabilisierungsdauer
- RPO und RTO je Plattformkomponente
- Break-glass-Verfahren für produktive Notfälle

Referenz: Issue #7, Epic #2.
