# Entwicklungs- und Qualitätsrichtlinien

## 1. Zweck

Dieses Dokument definiert verbindliche Regeln für Änderungen am Repository `Merchfactory/Infrastructure`. Es gilt für Dokumentation, Infrastrukturcode, Konfiguration, Skripte, Tests, Deployment-Definitionen und betriebliche Werkzeuge.

Ziel ist, dass Änderungen nachvollziehbar, reproduzierbar, sicher, testbar und für andere Personen wartbar bleiben.

## 2. Geltungsbereich

Die Richtlinien gelten für:

- alle dauerhaften und kurzlebigen Branches,
- sämtliche Pull Requests,
- Dokumentation und Architecture Decision Records,
- Bootstrap- und Konfigurationsautomatisierung,
- Deployment-, Monitoring-, Backup- und Restore-Code,
- Shell-, Python- und sonstige Hilfsskripte,
- GitHub Actions und Repository-Governance,
- Beispiele und Templates.

Technische Ausnahmen müssen im Pull Request begründet und, falls dauerhaft relevant, über ein Issue oder ADR dokumentiert werden.

## 3. Grundprinzipien

1. Änderungen beginnen mit einem klar definierten Arbeitsauftrag.
2. Der Repository-Stand ist die führende Quelle für Infrastruktur und Dokumentation.
3. Änderungen müssen reproduzierbar und nach Möglichkeit idempotent sein.
4. Sicherheit, Wiederherstellbarkeit und Monitoring werden bereits beim Entwurf berücksichtigt.
5. Secrets, produktive Zugangsdaten und reale Kundendaten gehören nicht ins Repository.
6. Kleine, klar abgegrenzte Pull Requests werden großen Sammeländerungen vorgezogen.
7. Dokumentation, Tests und Betriebshinweise sind Bestandteil der Änderung und keine nachgelagerte Aufgabe.
8. Technische Komplexität muss durch einen konkreten Nutzen begründet sein.

## 4. Branch-Modell

Dauerhafte Branches:

- `development`: Integration laufender Änderungen,
- `staging`: freigegebener, produktionsnah geprüfter Stand,
- `main`: produktiv freigegebener Stand.

Kurzlebige Branches werden grundsätzlich von `development` erstellt.

Zulässige Präfixe:

- `feature/` für neue Funktionen,
- `fix/` für Fehlerkorrekturen,
- `docs/` für reine Dokumentationsänderungen,
- `chore/` für Wartung und organisatorische Änderungen,
- `refactor/` für interne Umstrukturierung ohne beabsichtigte Funktionsänderung,
- `test/` für Testergänzungen,
- `agent/` für durch einen KI-Agenten bearbeitete Aufgaben.

Beispiele:

```text
feature/server-bootstrap
fix/backup-retention
chore/update-dependencies
docs/restore-runbook
agent/development-guidelines
```

Regeln:

- Branch-Namen verwenden `kebab-case`.
- Ein Branch bearbeitet möglichst genau ein Issue oder ein klar abgegrenztes Teilziel.
- Direkte Änderungen auf `development`, `staging` oder `main` sind nicht vorgesehen.
- Kurzlebige Branches werden nach erfolgreichem Merge manuell gelöscht.
- Dauerhafte Branches dürfen nicht gelöscht oder durch Force Push überschrieben werden.

## 5. Commit-Konventionen

Commit-Nachrichten folgen diesem Muster:

```text
<typ>: <kurze beschreibung>
```

Zulässige Typen:

- `feat`: neue Funktion,
- `fix`: Fehlerkorrektur,
- `docs`: Dokumentation,
- `chore`: Wartung oder Verwaltung,
- `refactor`: interne Umstrukturierung,
- `test`: Tests,
- `ci`: CI/CD-Änderung,
- `build`: Build- oder Paketierungsänderung,
- `security`: gezielte Sicherheitsänderung,
- `revert`: Rücknahme einer Änderung.

Beispiele:

```text
docs: define restore testing process
fix: prevent empty backup target
ci: validate compose configuration
security: restrict ssh forwarding
```

Anforderungen:

- Beschreibung im Imperativ oder als klare Tätigkeit.
- Keine nichtssagenden Nachrichten wie `update`, `changes` oder `fix stuff`.
- Ein Commit soll einen logisch zusammengehörigen Schritt enthalten.
- Temporäre Debug-Ausgaben und nicht benötigte Dateien werden vor dem Merge entfernt.
- Bei Breaking Changes muss die Auswirkung in Commit und Pull Request klar benannt werden.

## 6. Pull-Request-Konventionen

Jeder Pull Request enthält mindestens:

- verständlichen Titel,
- Zusammenfassung,
- Ziel und Umfang,
- Referenz auf Issue oder Arbeitsauftrag,
- betroffene Komponenten,
- Test- oder Prüfnachweis,
- Risiken und Auswirkungen,
- Rollback- oder Wiederherstellungshinweis, sofern relevant.

Ein Pull Request soll beantworten:

1. Was wurde geändert?
2. Warum wurde es geändert?
3. Wie wurde es geprüft?
4. Welche Auswirkungen oder Risiken bestehen?
5. Wie kann die Änderung zurückgenommen oder korrigiert werden?

Der Zielbranch ist im Regelfall `development`.

Promotion erfolgt über separate Pull Requests:

```text
development -> staging -> main
```

Direkte Promotion von `development` nach `main` ist nur für ausdrücklich dokumentierte Übergangs- oder Notfallsituationen zulässig.

## 7. Review-Anforderungen

Ein Review prüft mindestens:

- fachliche Vollständigkeit,
- Übereinstimmung mit Architektur und ADRs,
- Sicherheit und Berechtigungen,
- Daten- und Secret-Risiken,
- Wiederherstellbarkeit,
- Testabdeckung,
- Fehlerbehandlung,
- Wartbarkeit und Verständlichkeit,
- Auswirkungen auf andere Dienste und Umgebungen.

Bei sicherheitskritischen, datenverändernden oder produktionsrelevanten Änderungen soll nach Möglichkeit eine zweite Person prüfen.

Offene Review-Kommentare müssen vor dem Merge beantwortet oder nachvollziehbar aufgelöst werden.

## 8. Dokumentationsstandard

Die Projektdokumentation wird grundsätzlich auf Deutsch verfasst.

Unverändert bleiben technische Eigennamen und Fachbegriffe, bei denen eine Übersetzung unüblich oder missverständlich wäre, beispielsweise:

- Docker Compose,
- GitHub Actions,
- Pull Request,
- Commit-SHA,
- Healthcheck,
- Rollback,
- RPO und RTO,
- Dateipfade, Befehle und Konfigurationsschlüssel.

Neue oder geänderte Dokumentation muss:

- zum tatsächlichen technischen Stand passen,
- klare Verantwortlichkeiten enthalten,
- Voraussetzungen und Abhängigkeiten benennen,
- offene Entscheidungen kenntlich machen,
- betroffene Runbooks und ADRs verlinken,
- keine sensiblen Informationen enthalten.

Akzeptierte ADRs werden nicht rückwirkend inhaltlich umgeschrieben. Eine abweichende neue Entscheidung wird durch eine neue ADR dokumentiert.

## 9. Idempotenz und Reproduzierbarkeit

Automatisierung muss mehrfach ausführbar sein, ohne einen korrekten bestehenden Zustand zu beschädigen.

Anforderungen:

- Vorhandene Ressourcen werden erkannt.
- Änderungen werden nur bei Bedarf durchgeführt.
- Zielzustände sind deklarativ oder eindeutig beschrieben.
- Ergebnisse hängen nicht von undokumentierten manuellen Vorarbeiten ab.
- Versionen, Images und Abhängigkeiten werden nachvollziehbar festgelegt.
- Zufällige oder zeitabhängige Werte werden kontrolliert erzeugt und gespeichert.

Nicht idempotente Schritte müssen:

- ausdrücklich als einmalig gekennzeichnet sein,
- einen sicheren Wiederholungs- oder Abbruchmechanismus besitzen,
- im Migrations- oder Deployment-Ablauf dokumentiert werden.

## 10. Konfigurationsstandards

Konfigurationen müssen:

- gemeinsame und umgebungsspezifische Werte trennen,
- nachvollziehbare Standardwerte besitzen,
- Eingaben validieren,
- keine produktiven Secrets enthalten,
- klare Dateinamen und Strukturen verwenden,
- mit Kommentaren nur tatsächliche Besonderheiten erklären.

Umgebungen heißen verbindlich:

- `development`,
- `staging`,
- `production`.

Konfigurationen dürfen nicht vollständig pro Umgebung kopiert werden, wenn nur einzelne Werte abweichen.

## 11. Secret- und Datenschutzregeln

Nicht zulässig im Repository sind:

- Passwörter,
- API-Tokens,
- private Schlüssel,
- produktive `.env`-Dateien,
- Recovery-Codes,
- echte Kundendaten,
- produktive Datenbank-Dumps,
- vollständige Produktions- oder Designdateien,
- sensible interne URLs oder Zugangsinformationen, sofern sie nicht ohnehin öffentlich und unkritisch sind.

Beispieldateien verwenden erkennbare Platzhalter:

```text
CHANGE_ME
example.invalid
user@example.invalid
00000000000000000000000000000000
```

Ein versehentlich veröffentlichtes Secret gilt als kompromittiert und muss ersetzt werden. Das reine Entfernen aus einem späteren Commit ist nicht ausreichend.

## 12. Fehlerbehandlung

Skripte und Automatisierung müssen Fehler eindeutig erkennen und melden.

Mindestanforderungen:

- Eingaben vor Verarbeitung validieren,
- sinnvolle Exit-Codes verwenden,
- bei kritischen Fehlern sicher abbrechen,
- keine Teilzustände als Erfolg melden,
- Fehlermeldungen mit Ursache und betroffener Komponente ausgeben,
- keine Secrets in Fehlermeldungen oder Logs ausgeben,
- bei destruktiven Aktionen explizite Freigaben verlangen.

Shell-Skripte sollen abhängig vom Anwendungsfall unter anderem verwenden:

```bash
set -Eeuo pipefail
```

Dabei ist sicherzustellen, dass erwartete nicht-null Rückgabewerte bewusst behandelt werden.

## 13. Logging-Standards

Logs müssen für Betrieb und Fehlersuche nützlich sein, ohne unnötige sensible Daten offenzulegen.

Mindestens sinnvoll sind:

- Zeitstempel,
- Komponente oder Skript,
- Umgebung,
- Aktion,
- Status,
- technische Fehlerursache,
- Korrelations- oder Vorgangs-ID, sofern vorhanden.

Log-Level:

- `DEBUG`: detaillierte Diagnose, standardmäßig nicht in Produktion,
- `INFO`: normaler Ablauf,
- `WARN`: erkennbare Abweichung ohne unmittelbaren Abbruch,
- `ERROR`: fehlgeschlagener Vorgang,
- `CRITICAL`: akuter Ausfall, Datenverlust oder Sicherheitsvorfall.

Nicht protokolliert werden dürfen Passwörter, Tokens, Cookies, private Schlüssel oder unnötige personenbezogene Inhalte.

## 14. Tests und Validierung

Der erforderliche Testumfang richtet sich nach dem Änderungstyp.

### Dokumentation

- Markdown-Syntax,
- interne Links,
- Dateipfade,
- Konsistenz mit bestehenden ADRs und Konzepten,
- deutsche Dokumentationssprache.

### Konfiguration

- Syntax- und Schema-Prüfung,
- Linting,
- sichere Standardwerte,
- Dry Run oder Plan, sofern möglich,
- Prüfung für alle betroffenen Umgebungen.

### Skripte

- Syntaxprüfung,
- Linting,
- Positiv- und Fehlerfälle,
- sichere Wiederholung,
- korrekte Exit-Codes,
- Verhalten bei fehlenden Abhängigkeiten.

### Deployment

- Preflight-Prüfung,
- Healthchecks,
- Smoke Tests,
- Rollback-Fähigkeit,
- Daten- und Persistenzprüfung.

### Backup und Restore

- Backup-Erstellung,
- Integritätsprüfung,
- Testrestore,
- Validierung des wiederhergestellten Dienstes,
- Messung gegen RPO und RTO.

Ein Testnachweis kann automatisiert oder manuell erfolgen, muss aber im Pull Request nachvollziehbar beschrieben werden.

## 15. Abhängigkeiten

Neue Abhängigkeiten müssen begründet werden.

Zu prüfen sind:

- Wartungsstatus,
- Lizenz,
- Sicherheitsrisiken,
- Update- und Supportmodell,
- Anbieterbindung,
- zusätzlicher Betriebsaufwand,
- Restore- und Migrationsfähigkeit.

Versionen sollen gepinnt oder innerhalb eines kontrollierten Bereichs festgelegt werden. Floating Tags wie `latest` sind für produktive Deployments nicht zulässig.

Automatische Abhängigkeitsupdates benötigen weiterhin Review und Tests.

## 16. Breaking Changes

Ein Breaking Change liegt vor, wenn bestehende Konfigurationen, Abläufe, Schnittstellen, Daten oder Deployments ohne Anpassung nicht mehr funktionieren.

Der Pull Request muss enthalten:

- klare Kennzeichnung als Breaking Change,
- betroffene Komponenten und Umgebungen,
- Migrationsschritte,
- Kompatibilitätsgrenzen,
- Rollback- oder Restore-Verfahren,
- notwendige Kommunikationsmaßnahmen.

Destruktive Datenänderungen benötigen eine explizite Freigabe und ein aktuelles, geprüftes Backup.

## 17. Releases und Versionierung

Freigegebene Stände werden nachvollziehbar über Commit-SHA, Tag oder Release identifiziert.

Ein Release enthält mindestens:

- Umfang der Änderungen,
- bekannte Risiken,
- Breaking Changes,
- Migrationshinweise,
- Rollback-Verfahren,
- Test- und Freigabestatus.

Ein in `staging` geprüftes Artefakt wird unverändert nach `production` übernommen.

## 18. Notfalländerungen

Notfalländerungen sind nur zulässig, wenn ein unmittelbares Sicherheits-, Daten- oder Verfügbarkeitsrisiko besteht.

Mindestanforderungen:

- Incident-Referenz,
- kleinstmöglicher Umfang,
- dokumentierte Auswirkung,
- nachträgliche Übernahme in das Repository,
- nachträglicher Pull Request und Review,
- Ursachenanalyse nach Stabilisierung.

Manuelle Änderungen dürfen nicht dauerhaft zu Configuration Drift führen.

## 19. Definition of Done für Änderungen

Eine Änderung gilt als abgeschlossen, wenn:

- Ziel und Umfang erfüllt sind,
- relevante Tests erfolgreich waren,
- Dokumentation aktualisiert wurde,
- Sicherheits- und Secret-Prüfung erfolgt ist,
- Fehler- und Rollback-Verhalten geklärt ist,
- Review-Kommentare bearbeitet wurden,
- keine temporären Dateien oder Debug-Ausgaben verbleiben,
- der Pull Request auf den richtigen Zielbranch zeigt,
- Folgeaufgaben und offene Risiken dokumentiert sind.

## 20. Referenzen

- Issue #11
- Epic #2
- `docs/README.md`
- `docs/04-security.md`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/09-repository-structure.md`
- `docs/02-adr/ADR-0001-branching-strategy.md`
- `docs/02-adr/ADR-0004-infrastructure-as-code.md`
- `docs/02-adr/ADR-0006-security-first.md`
