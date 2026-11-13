# Infrastrukturreview – Arbeitsstand 2026-11-01

## Auftrag und Grenzen

Repository-Zusammenspiel prüfen und belegte offene Punkte lokal bearbeiten.
Keine Deployments, Hoständerungen, Migrationen, produktiven Datenzugriffe,
zusätzlichen Kosten, Commits, Pushes oder PR-/Issue-Mutationen beauftragt.
Produktionskonfigurationen, Credentials und Environment-Dateien bleiben ungelesen.

### Erweiterung: lesende Incident-Diagnose

Der Nutzer hat anschließend die Fortsetzung der cAdvisor-/PIM-Runner-Diagnose
über den vorhandenen SSH-Zugang autorisiert. Dies umfasst Status-/Fehlerdiagnose,
keine Deployments, Neustarts, Konfigurationsänderungen, Lasttests oder Bereinigungen.
Restore-Richtung bleibt wie vorgegeben: App-eigene Backups/Restores,
Infrastruktur prüft Evidence vor riskanter Maintenance.

Erste Zugangstests wurden abgelehnt. Anschließend nannte der Nutzer den
funktionierenden administrativen Zugang; SSH mit strikter Hostkey-Prüfung war
erfolgreich. Verbindungseinstellungen bleiben im Chat, keine Schlüsselinhalte
gelesen. Ausschließlich Hoststatus, cgroup-Speicherwerte und gefilterte historische
Kernel-OOM-Einträge gelesen. Keine aktiven SSH-Sitzungen oder Änderungen am VPS.

### Incident-Zwischenstand 2026-11-01, 02:22 UTC

- cAdvisor aktiv; NRestarts=11, MemoryCurrent=950349824 Bytes (ca. 906 MiB),
  MemoryPeak=976580608, MemoryMax=1077936128 (1028 MiB).
- Zweiter Snapshot: anon=16900096, file=355749888, kernel=571203584 Bytes;
  slab_reclaimable=570304720 Bytes. Keine kausale Folgerung allein aus Snapshot.
- memory.events im aktuellen Dienstlebenszyklus: oom=0, oom_kill=0. Das widerlegt
  frühere OOMs nicht; Dienststart laut systemd 01.11.2026 01:48:15 CET.
- Kerneljournal bestätigt cAdvisor-cgroup-OOM-Kills am 27.10. um 12:01, 12:03,
  16:06, 18:29 und 22:45 CET. Gefilterter Tagesauszug enthielt nur cAdvisor als
  OOM-Opfer; kein Nachweis für einen dadurch ausgelösten Runner-Ausfall.
- PIM ist Merchfactory/Produkt-Import-Tool, laut README bestätigt.
- Backendjobs 122245803673 und 122308331620: jeweils 27 failed/995 passed;
  Job 122351745053: 31 failed/998 passed; regulärer pytest-Exitcode 1.
  Assertionfehler insbesondere tests/imports/test_import_plan_builder.py.
- Backendjobs 122428763087 (19:48:56–20:04:58 UTC) und 122434379470
  (19:57:22–20:14:24 UTC) am 27.10.: pytest in_progress, Poststeps pending,
  Gesamtjob failure. Fehlender Abschluss belegt, Ursache ungeklärt.
  Logabfragen: 404 BlobNotFound; Annotationen vom Connector nicht unterstützt;
  gh lokal nicht vorhanden. Keine Abhängigkeit installiert.
- Alle fünf Frontendjobs erfolgreich. Neueste Runs 41199993849 und 41203040285
  vom 31.10. (12:11/12:52 UTC) insgesamt erfolgreich. Keine Runs ausgelöst.
- Korrelation offen: Runner-/DinD-/Controller-Ausgänge und Docker-Ereignisse
  gezielt für 27.10. 19:48–20:15 UTC prüfen; nicht pauschal cAdvisor verantwortlich
  machen. Kein Lasttest/Restart/Deploy ohne gesonderte Freigabe.

Belege: https://github.com/Merchfactory/Produkt-Import-Tool/actions/runs/40572113406
und https://github.com/Merchfactory/Produkt-Import-Tool/actions/runs/40571321868.
GitHub-Diagnose durch technical_project_lead beendet; kein Agent arbeitet weiter.
Wegen zuletzt 6 % Rest im 5h-Fenster kein neues Diagnosepaket begonnen.

## Ausgangsstand

- Projekt durch Nutzer bestätigt: Merchfactory/Infrastructure.
- Ursprünglicher lokaler Branch: development, ce4bfae (sauber).
- Remote-Refs mit git fetch origin aktualisiert; origin/development: 3c13f50.
- Arbeitsbranch: codex/infrastructure-review.
- Basis: vorhandener Draft #342, origin/fix/cadvisor-disk-metrics-pressure,
  Commit 5b6d2876826596a8be0f670943f7aa696ea6e9e5.
- Draft #343 enthält den vorgeschlagenen v0.7-Maintenance-/Backup-Evidence-Vertrag.
  Keine Architekturabnahme oder Implementierung dieses Entwurfs erfolgt.

## Abgeschlossenes lokales Arbeitspaket

- Repository-Karte und offene Integrationspunkte: infrastructure-review-2026-11-01.md.
- cAdvisor: 8 Dateien lokal geändert (Rollendefaults, systemd-Template,
  Unit-/Integrationstest, Fresh-Host-Verifikation, Prometheus-Regeltest,
  docs/64-cadvisor.md und tests/README.md).
- lean-Profil und optionales Upstream-Filesystemprofil konsistent dokumentiert
  und synthetisch geprüft. Keine behauptete OOM-Behebung auf einem echten Host.
- Unabhängiges Review durch technical_project_lead abgeschlossen: keine
  verbleibenden blockierenden Befunde; frühere UTF-8-Probleme behoben.
- Keine externen Prozesse oder Hosttests gestartet. WSL-Tests abgeschlossen.

## Weitere abgeschlossene lokale Arbeitspakete

- Firewall #276: Rollenport-Akkumulation und Reihenfolge der SSH-Freigabe
  korrigiert. Geändert: tasks/main.yml der Rolle, tests/unit/test_firewall_policy.py.
  Drei neue Regressionstests vor Fix fehlgeschlagen, nach Fix grün;
  unabhängiges Review ohne blockierende Befunde.
- OpenWebUI: F:/Projects/openwebui, codex/infrastructure-integration-review,
  Basis main e818211. Workflow nur manuell, Provisionierer vor Upload,
  README korrigiert, tests/test_deployment_contract.py ergänzt.
  Unabhängiges Review ohne Befunde. Runner-Freischaltung offen.
- n8n: F:/Projects/n8n-deployment, codex/infrastructure-docs-review,
  Basis main 1137323. README an vorhandenes App-owned Edge-Routing angepasst.
- Odoo: F:/Projects/odoo-deployment, codex/infrastructure-docs-review,
  Basis main 10c0f6c. README nennt tatsächlichen ubuntu-24.04-Runner.
- Beide README-Korrekturen unabhängig gegen Code abgenommen.
- Draft #343 read-only geprüft; Widersprüche und fehlende Vertragsdetails im
  Reviewbericht dokumentiert. ADR weiterhin proposed, keine Implementierung.
- Keine Agents oder externen Prozesse arbeiten weiter an diesen Paketen.

Die lokalen Korrekturpakete sind beendet; die separate lesende PIM-Incident-
Diagnose ist mit obigem Zwischenstand gesichert und noch nicht abgeschlossen.

## Verifikation bisher

Read-only: lokale Git-Zustände, GitHub-Repositoryliste, offene Issues (erste
40 nach Aktualisierung), offene PRs und ausgewählte Dokumentation abgeglichen.
Dies ist keine vollständige Backlog-Abnahme und kein Laufzeitnachweis.

Erfolgreich ausgeführt (nach Wiederaufnahme vom Hauptagent wiederholt):

```text
wsl -d Ubuntu-20.04 -- bash -lc 'cd /mnt/f/Projects/Infrastructure && python3 -m unittest discover -s tests/unit -p test_cadvisor_policy.py && bash -n tests/integration/test-cadvisor.sh'
git diff --check
```

Ergebnis: 11 Unit-Tests einschließlich Jinja-Rendering beider Profile erfolgreich;
Shell-Syntax und Diff-Whitespace erfolgreich. Implementierer zusätzlich:
vier YAML-Dateien geparst, sechs synthetische Bootstrap-Profilfälle erfolgreich.
Windows-Python: 11 Tests, davon Jinja-Test mangels Jinja2 übersprungen; WSL-Test
schließt diese Lücke. Keine Abhängigkeiten installiert.

Offen: promtool nicht im vorhandenen PATH; Prometheus-Regeltest nicht ausgeführt.
Linux-/Docker-Integration beider Profile und Host-/Lastnachweis nicht ausgeführt.

Weitere Verifikation:

- WSL: python3 -m unittest discover -s tests/unit -p test_firewall_policy.py
  im Infrastructure-Checkout: 9/9 erfolgreich, auch durch Reviewer ausgeführt.
- WSL: python3 -m unittest discover -s tests -p 'test_*.py' im OpenWebUI-Checkout:
  3/3 erfolgreich, unabhängig wiederholt. SSH/SCP nur Stubs, kein Remote-Shelllauf.
- Sämtliche OpenWebUI-Workflow-Shellblöcke mit bash -n geprüft.
- git diff --check in allen vier Checkouts erfolgreich.
- README-Korrekturen statisch gegen Routing-Skripte/Compose bzw. Workflow geprüft.

Tests bedeuten keine Freigabe für echte Firewall-/SSH-Änderungen, Deployments,
Runner-Registrierung oder produktive Backup-/Restore-Abläufe.

## Nächste Schritte

1. Lokale Änderungen zur Übernahme prüfen; Commit/Push nicht beauftragt.
2. promtool und isolierte Docker-Tests bei vorhandener/freigegebener Laufzeit nachholen.
3. Zielhost, Umfang und Freigabe für cAdvisor-/Firewall-Tests und Runner-Scope klären.
4. Vorgeschlagenen Backup-Vertrag vor Implementierung fachlich konsistent abnehmen.
5. Vor weiteren Arbeitspaketen Kontolimits neu prüfen.

Nach ausdrücklicher Wiederaufnahme und Limitreset frisch gemessen:
6 % Rest im 5-Stundenfenster, 85 % im Wochenfenster (2026-11-01 ca. 02:21 UTC).
5h-Reset laut Tool: Unix 1793516382. Vor Fortsetzung erneut messen.
Bei höchstens 10 % keine neuen größeren Pakete/Agents; bei höchstens 5 % stoppen.
