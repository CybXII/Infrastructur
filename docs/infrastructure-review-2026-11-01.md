# Repository- und Integrationsreview 2026-11-01

## Prüfgrundlage

Nutzerbestätigtes Projekt: Merchfactory/Infrastructure. Repository-Metadaten,
offene PRs und 40 zuletzt aktualisierte offene Issues wurden auf GitHub gelesen.
Die technische Projektleitung prüfte aktuelle Dokumentation und App-READMEs,
anschließend App-Workflows, Runner-Registrierung und generische Plattformverträge.
Produktionskonfigurationen, Environment-Dateien und Zugangsdaten wurden nicht
gelesen; es erfolgte kein Zugriff auf laufende Server.

Der alte lokale development-Stand ce4bfae war veraltet. Nach Fetch wurde der
lokale Arbeitsbranch codex/infrastructure-review von Draft #342 (5b6d287)
erstellt. Vorhandene Änderungen dieses Drafts sind nicht Ergebnisse dieses Reviews.

## Belegtes Zusammenspiel

| Repository | Verantwortung laut Dokumentation |
|---|---|
| [Infrastructure](https://github.com/Merchfactory/Infrastructure) | Host-Baseline, Docker, Traefik/TLS/ACME, Edge-Netz, generische Service-Verzeichnisse, Monitoring, Installation der Runner-Plattform |
| [GitHub-Runners](https://github.com/CybXII/GitHub-Runners) | Ephemere Runner und DinD auf einem ausgewählten Runner-Host; dokumentierte Scopes: Merchfactory und n8n-deployment |
| [n8n-deployment](https://github.com/CybXII/n8n-deployment/blob/main/README.md) | n8n, PostgreSQL, Task-Runner, eigener Deployment- und Backup-Pfad |
| [odoo-deployment](https://github.com/CybXII/odoo-deployment/blob/main/README.md) | Odoo/PostgreSQL, Filestore, Backups, App-Route; laut README vorbereitet, nicht deployed |
| [openwebui](https://github.com/CybXII/openwebui/blob/main/README.md) | WebUI/PostgreSQL/Redis, App-Route und Deployment; laut README noch nicht auf VPS validiert |

Plattformverträge: [Runner-Host](34-github-runner-host.md),
[App-eigenes Routing](68-application-owned-edge-routing.md),
[Monitoring-Vertrag](75-monitoring-service-contract.md).
Apps besitzen ihre Compose-Stacks und atomar geschriebenen app-*.yaml-Routen.
Infrastructure besitzt die gemeinsame Edge-Plattform und ACME-Zustände.
Datenbanken und interne Worker gehören nicht ins öffentliche Edge-Netz.

Merchfactory/Odoo-Platform und VPS-Traefik-Server sind nicht als aktive
Abhängigkeiten belegt. Das Odoo-Deployment erklärt ausdrücklich seine
Unabhängigkeit von Odoo-Platform. Für CybXII/postgres lieferte README.md 404;
daraus folgt weder eine Integrationszuordnung noch die Abwesenheit anderer Dateien.

## Offene Punkte und zulässiger nächster Schritt

| Punkt | Nachweis / Stand | Nächster Schritt |
|---|---|---|
| cAdvisor-Metrikprofil | Issue #341, Draft #342; Integration und Bootstrap verlangten im Ausgangsstand weiterhin deaktivierte FS-Metriken | Lokal korrigiert, 11 Unit-Tests und unabhängiges Review erfolgreich; promtool und Host-/Lasttest offen |
| Runner-Zugang OpenWebUI | App-Workflow erwartet ephemeral-linux; generische Plattformdefaults konfigurieren nur Merchfactory und n8n; Controller registriert ausschließlich explizite Scopes | Scope/Tokenrechte und Job-Routing nach expliziter Zugriffsfreigabe prüfen; keine Freischaltung behaupten |
| Odoo-Runner-Dokumentation | Aktueller App-Workflow verwendet ubuntu-24.04; README war veraltet | README lokal korrigiert und unabhängig gegen Workflow geprüft; kein belegter Scope-Blocker für Odoo |
| OpenWebUI-Verzeichnisprovisionierung | Workflow erwartete schreibbare Plattform-Elternverzeichnisse statt Provisionierer-Aufruf | Lokal vor Upload korrigiert; drei synthetische Workflowtests und unabhängiges Review erfolgreich |
| OpenWebUI-Deploymenttrigger | Workflow enthielt push-main, README versprach ausschließlich manuell | Push-Trigger lokal entfernt; manueller Trigger durch Test abgesichert, kein Workflow ausgelöst |
| n8n-Proxyvertrag | README beschrieb Loopback als Proxy-Upstream; tatsächlicher Installer nutzt korrekt File Provider plus Edge-Alias | README lokal an Code angepasst und unabhängig geprüft; Loopback bleibt lokale Diagnose, kein Routing-Codefehler |
| OpenWebUI-Betriebsreife | README nennt Secret-Standard-Abweichung und fehlende Retention-/Restore-Abnahme | App-eigene Umsetzung/Tests getrennt prüfen; produktive Abnahme offen |
| Backup-/Maintenance-Vertrag | Draft #343, ADR-0011 proposed; Issues #100/#101/#102/#106/#111/#112/#116/#117 | Architekturentscheidung abnehmen, anschließend isolierte Vertragsimplementierung planen |
| Multi-Server/Recovery/v1.0 | Epics #291/#135 und offene Recovery-Aufgaben | Abhängigkeiten und Freigaben separat planen; keine Gesamtfertigstellung behaupten |
| Firewall-Port-Drift | Exklusives Pruning vorhanden; Rollenports akkumulierten, erforderlicher SSH-Port wurde erst nach Service-Pruning geöffnet | Lokal korrigiert; neun Tests, davon drei neue synthetische Regressionstests, und unabhängiges Review erfolgreich; tatsächliche firewalld-/SSH-Prüfung offen |

Issue #325 ist ausdrücklich Zukunfts-Backlog und kein aktueller Implementierungsauftrag.
Das Backlog wurde nicht vollständig abgearbeitet. Ein offenes Issue allein ist
kein Nachweis, dass die dort beschriebene Implementierung im aktuellen Branch fehlt.

## Verifikation und Grenzen

- Statisch geprüft: Git-Zustände, ausgewählte Dokumentation, Repository-Beziehungen,
  offene PR-Beschreibungen und Issue-Abgrenzungen; App-Routen/Workflow-Verträge,
  generische Runner-Scope-Logik sowie Firewall-Taskreihenfolge.
- Ausgeführte Tests und cAdvisor-Review: siehe [Arbeitsstand](work-status.md).
- Ungeprüft: tatsächliches Server-Placement, Runner-Freischaltung, Live-Metriken,
  OOM-/Slab-Entwicklung, Runner-Ausfallursachen, Restore und Produktionsbereitschaft.
- Keine Deployments, Migrationen, Host-Neustarts, Bereinigungen, externen
  Veröffentlichungen, Commits oder Pushes ausgeführt.

Vor Merge/Rollout von #342 bleiben Scrape-, cgroup-/Slab- und Runner-Churn-Messungen
sowie der dokumentierte Rollback auf einem ausdrücklich freigegebenen Testhost nötig.

## Review von Draft #343

Read-only gegen origin/development geprüft; ADR-0011 bleibt proposed.
Keine Vertragsimplementierung oder Architekturabnahme erfolgt.

- docs/07-disaster-recovery.md überträgt App-Backups neu an Applications,
  verlangt unter Infrastructure Owner aber weiterhin Betrieb der Backup-Jobs,
  Speicherziele und technische Wiederherstellungen. Vor Abnahme vereinheitlichen.
- deployment/service-release.py akzeptiert bei relevanten Datenänderungen eine
  nicht leere backup-reference. Dies ist noch kein überprüfter Evidence-Vertrag
  mit autorisiertem Service-/Environment-/Host-Placement.
- Frische, Restore-Test-Abstand, Vertrauensquelle/Manipulationsschutz,
  Bindung an Wartungsvorgang und Behandlung unbekannter Versionen konkretisieren.
- Post-Hook, Timeout-/Fehlerverhalten und Freigabe pausierter Schreibzugriffe
  fehlen in der minimalen Schnittstelle trotz Nennung im Architekturtext.
- ADR-Verweis auf superseded PR #339 vor Abnahme mit Draft #343 abgleichen.

Nach Architekturabnahme: Schema/Registrierung, isolierte Referenz- und
Negativtests, anschließend gesondert freizugebende Betriebsintegration.
Ein echter App-Restore ist durch diese Vertragsprüfungen nicht nachgewiesen.

## Lokale Arbeitsbranches

| Checkout | Branch | Änderungen |
|---|---|---|
| F:/Projects/Infrastructure | codex/infrastructure-review | cAdvisor, Firewall, Review-/Statusdokumentation |
| F:/Projects/openwebui | codex/infrastructure-integration-review | manueller Workflow, Provisionierer, synthetische Tests, README |
| F:/Projects/n8n-deployment | codex/infrastructure-docs-review | README-Routingvertrag |
| F:/Projects/odoo-deployment | codex/infrastructure-docs-review | README-Runnerangabe |

Alle Änderungen sind uncommitted und ungepusht. Die drei App-Repositories wurden
für diese lokale Prüfung geklont; existierende Arbeitskopien wurden nicht ersetzt.
Keine Produktions-/Environment-Dateien gelesen, keine Abhängigkeiten installiert.
