# Dokumentationsstandard

## Sprache

Die verbindliche Projektdokumentation der Merchfactory Infrastructure Platform wird grundsätzlich in deutscher Sprache verfasst.

Dies gilt insbesondere für:

- Architektur- und Konzeptdokumente
- Architecture Decision Records (ADRs)
- Betriebsanweisungen und Runbooks
- Sicherheits-, Backup- und Recovery-Dokumentation
- Verzeichnis-READMEs
- Issue- und Pull-Request-Beschreibungen, sofern sie Teil der dauerhaften Projektdokumentation werden

## Zulässige englische Fachbegriffe

Etablierte technische Begriffe dürfen verwendet werden, wenn eine Übersetzung unüblich oder missverständlich wäre. Dazu gehören beispielsweise:

- Branch
- Pull Request
- Merge
- Deployment
- Infrastructure as Code
- Monitoring
- Logging
- Backup
- Restore
- Disaster Recovery
- Healthcheck
- Secret
- Container

Die umgebende Erklärung und die inhaltliche Dokumentation bleiben deutsch.

## Code, Konfiguration und Bezeichner

Technische Bezeichner werden nicht übersetzt, wenn sie Bestandteil einer Schnittstelle, eines Dateipfads, eines Programms oder einer Konfiguration sind.

Beispiele:

- Branches: `development`, `staging`, `main`
- Verzeichnisse: `deployment/`, `monitoring/`, `backup/`
- GitHub Environments: `development`, `staging`, `production`
- Konfigurationsschlüssel und Umgebungsvariablen
- Befehle, Code, Logausgaben und Fehlermeldungen

## Neue Dokumente

Vor dem Merge ist zu prüfen:

1. Überschriften und Fließtext sind deutsch.
2. Englische Fachbegriffe werden konsistent verwendet.
3. Codeblöcke und technische Bezeichner wurden nicht unnötig übersetzt.
4. Referenzen auf andere Dokumente und ADRs sind korrekt.
5. Das Dokument ist ohne zusätzlichen Chatkontext verständlich.

## Bestehende Abweichungen

Bereits vorhandene englische Dokumentation wird bei der nächsten fachlichen Bearbeitung übersetzt oder über einen eigenen Korrektur-Pull-Request bereinigt.

## Referenzen

- `docs/00-vision.md`
- `docs/01-architecture.md`
- `docs/02-adr/README.md`
