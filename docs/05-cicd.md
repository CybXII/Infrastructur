# CI/CD-Konzept

## Zweck

Dieses Dokument definiert den verbindlichen Weg von einer geplanten Änderung bis zur Freigabe für eine Zielumgebung. Ziel sind reproduzierbare Änderungen, nachvollziehbare Reviews, automatisierte Qualitätsprüfungen und klar getrennte Verantwortlichkeiten.

## Branch-Modell

Dauerhafte Branches:

- `development`: Integrationsstand für laufende Entwicklung
- `staging`: freigegebener Release Candidate
- `main`: produktiv freigegebener Stand

Kurzlebige Arbeitsbranches werden von `development` abgezweigt:

- `feature/*`
- `fix/*`
- `docs/*`
- `chore/*`
- `agent/*`

Freigabefluss:

```text
Issue
  -> Arbeitsbranch
  -> Pull Request nach development
  -> automatische und manuelle Prüfungen
  -> Merge nach development
  -> Release-PR development nach staging
  -> Staging-Verifikation
  -> Release-PR staging nach main
  -> produktives Deployment
```

Direkte Änderungen auf `development`, `staging` und `main` sind nicht vorgesehen.

## Pull-Request-Anforderungen

Jeder Pull Request muss:

- ein Issue oder einen dokumentierten Arbeitsauftrag referenzieren,
- Ziel, Umfang und Risiken beschreiben,
- klein genug für ein belastbares Review sein,
- keine Secrets, Zugangsdaten oder produktiven Daten enthalten,
- die für den Änderungstyp relevanten Prüfungen erfolgreich durchlaufen.

Arbeitsbranches werden nach erfolgreichem Merge automatisch gelöscht.

## Prüfklassen

### Dokumentation

Automatisch:

- Markdown-Syntax und Links prüfen
- Dateinamen und Verzeichnisstruktur validieren
- verbotene Secret-Muster erkennen

Manuell:

- fachliche Konsistenz
- Übereinstimmung mit ADRs und Architektur
- Verständlichkeit für Betrieb und Wiederherstellung

### Konfiguration und Infrastructure as Code

Automatisch:

- Syntax- und Schema-Validierung
- Linting
- Formatprüfung
- Secret-Scanning
- statische Sicherheitsanalyse
- Plan-, Diff- oder Dry-Run-Ausgabe

Manuell:

- Bewertung destruktiver Änderungen
- Prüfung von Netzwerk-, Daten- und Berechtigungsauswirkungen
- Prüfung der Rollback-Fähigkeit

### Skripte und Anwendungscode

Automatisch:

- Linting
- Unit- und Integrationstests
- Dependency- und Vulnerability-Scan
- Build- oder Container-Image-Erstellung
- Image-Scan

Manuell:

- fachliche Abnahme
- Prüfung privilegierter Funktionen
- Bewertung externer Abhängigkeiten

## Qualitäts-Gates

### Arbeitsbranch nach development

Erforderlich:

- erfolgreiche CI
- mindestens ein Review, sobald mehrere berechtigte Reviewer verfügbar sind
- keine offenen Blocker
- dokumentierte Auswirkungen

### development nach staging

Erforderlich:

- vollständige CI
- reproduzierbares Build-Artefakt oder unveränderlicher Commit-SHA
- Release Notes
- bekannte Risiken und Rollback-Verfahren
- Freigabe für das GitHub Environment `staging`

### staging nach main

Erforderlich:

- erfolgreiche Staging-Verifikation
- Backup- oder Wiederherstellungsprüfung bei datenrelevanten Änderungen
- manueller Approval für das GitHub Environment `production`
- dokumentierter Wartungs- und Rollback-Plan

## GitHub Environments

Vorgesehene Environments:

- `development`
- `staging`
- `production`

Secrets und Variablen werden pro Environment getrennt verwaltet. Produktions-Secrets dürfen ausschließlich Jobs zur Verfügung stehen, die an das Environment `production` gebunden und freigegeben sind.

Empfohlene Schutzregeln:

- `development`: automatisierte Prüfungen, eingeschränkte Deployment-Berechtigung
- `staging`: erforderliche Reviewer und optionaler Wartezeitraum
- `production`: erforderliche Reviewer, streng begrenzte Deployment-Branches, keine Self-Approval-Ausnahme

## Artefakte und Nachvollziehbarkeit

Deployments referenzieren unveränderliche Artefakte:

- Commit-SHA,
- vollständig per SHA-256-Digest referenziertes Container-Image,
- First-Party-Build-Provenance über GitHub Artifact Attestations,
- Prüfsummen für Archive und Konfigurationspakete.

Eigene Container-Images werden unter `ghcr.io/merchfactory/...` veröffentlicht. Vor Promotion müssen Registry-Policy, Vulnerability-Gates und bei First-Party-Images die Provenance-Verifikation erfolgreich sein.

Ein in Staging geprüftes Artefakt wird unverändert nach Produktion promoted. Es wird nicht für Produktion neu gebaut. Der identische Image-Digest durchläuft Development, Staging und Production.

Der Deployment-Controller erhält zusätzlich Source-Revision, Release- und Approval-Referenz zur Auditierbarkeit. Ein erfolgreich ausgeführter automatischer Rollback macht den fehlgeschlagenen Deploymentversuch ausdrücklich nicht zu einem erfolgreichen CI/CD-Release.

## Fehlerbehandlung

Bei fehlgeschlagener CI:

- kein Merge
- Ursache im Pull Request dokumentieren
- Korrektur auf demselben Arbeitsbranch

Bei fehlgeschlagenem Deployment:

- Deployment stoppen
- Zustand und Logs sichern
- Rollback oder Roll-forward gemäß `docs/06-deployment.md` und `docs/57-update-rollback.md`
- Incident eröffnen, wenn Verfügbarkeit, Datenintegrität oder Sicherheit betroffen sind

## Verantwortlichkeiten

- Autor: vollständiger Scope, Tests, Dokumentation und Rollback-Information
- Reviewer: technische und sicherheitsrelevante Prüfung
- Release-Verantwortlicher: Promotion nach Staging und Produktion
- Betriebsverantwortlicher: Verifikation, Monitoring und Incident-Entscheidung

Eine Person kann in einem kleinen Team mehrere Rollen ausüben; kritische produktive Änderungen sollen dennoch durch ein separates Review abgesichert werden.

## Abhängigkeiten

Dieses Konzept ist mit folgenden Dokumenten abzustimmen:

- `docs/01-architecture.md`
- `docs/03-server-layout.md`
- `docs/04-security.md`
- `docs/06-deployment.md`
- `docs/02-adr/ADR-0001-branching-strategy.md`
- `docs/02-adr/ADR-0002-github-environments.md`
- `docs/02-adr/ADR-0004-infrastructure-as-code.md`
- `docs/02-adr/ADR-0006-security-first.md`
- `docs/02-adr/ADR-0007-backup-strategy.md`

## Offene Entscheidungen

Folgende Punkte werden in späteren Issues oder ADRs konkretisiert:

- konkrete CI-Tools und Workflow-Dateien
- verpflichtende Reviewer-Anzahl je Branch
- verpflichtende Commit-Signierung zusätzlich zur bereits definierten Image-Provenance
- konkrete Deployment-Runner und deren Netzwerkzugriff
- Freigaberegeln für Notfalländerungen

Referenz: Issue #7, Epic #2.
