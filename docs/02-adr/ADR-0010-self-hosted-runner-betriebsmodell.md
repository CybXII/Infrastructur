# ADR-0010: Self-hosted Runner Betriebs- und Bootstrap-Modell

- Status: accepted
- Datum: 2026-10-05
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Infrastructure Platform soll GitHub Actions überwiegend über eigene ephemere
Runner ausführen, um GitHub-hosted Laufzeit zu reduzieren und eine kontrollierte
CI/CD-Plattform bereitzustellen.

In der aktuellen Entwicklungsphase steht nur ein privater VPS zur Verfügung.
Dieser Host soll gleichzeitig Development-Workloads wie Odoo, Datenbanken und
Monitoring sowie die GitHub-Runner-Plattform betreiben können.

Die Runner-Plattform selbst läuft auf dem Host-Docker-Daemon. Ein Self-hosted
Job darf deshalb nicht die Host-Runtime, auf der sein eigener Runner läuft,
ungeplant neu starten, entfernen oder grundlegend verändern. Andernfalls kann
sich ein Deployment selbst unterbrechen und im Fehlerfall zusätzlich seinen
eigenen Recovery-Pfad verlieren.

## Entscheidung

1. Ein Runner-Host darf gleichzeitig app_server-, Datenbank-, Monitoring- und
   weitere Development-Rollen besitzen. Ein dedizierter Runner-VPS ist keine
   Voraussetzung.
2. Normale App-Deployments dürfen über ephemeral-linux auf denselben Host
   erfolgen, wenn sie strikt auf ihr eigenes Compose-Projekt beziehungsweise
   ihren eigenen Service-Scope begrenzt sind.
3. Hostweite Operationen bleiben von Self-hosted Runnern getrennt. Dazu gehören
   insbesondere Docker-Daemon-/Paketänderungen, Host-Hardening, SSH-/Firewall-
   Grundlagen, Reboots und die Runner-Plattform selbst.
4. Bootstrap Fresh Host, Bootstrap Managed Host und Bootstrap Idempotency laufen verbindlich auf
   ubuntu-24.04 als GitHub-hosted Runner. Diese Workflows werden nicht über
   einen späteren RUNNER_MODE-Schalter umgebogen.
5. Runner-Aufbau, Runner-Recovery und Host-Maintenance werden bewusst über den
   GitHub-hosted Bootstrap ausgeführt.
6. Vor einer geplanten Host-/Runner-Wartung werden Self-hosted Jobs auf diesem
   Host nicht neu eingeplant. Sobald ein zentraler RUNNER_MODE eingeführt ist,
   wird vor der Wartung auf github-hosted und nach erfolgreichem Smoke-Test
   wieder auf self-hosted geschaltet.
7. DEVELOPMENT_BOOTSTRAP_MANAGED_HOST_ENABLED wird als operatives
   Maintenance-Gate verwendet. Im späteren Normalbetrieb kann es false
   bleiben und nur für bewusste Host-Wartung aktiviert werden.
8. DEVELOPMENT_RUNNER_HOST_ENABLED bestimmt, ob der Development-Host beim
   Bootstrap zusätzlich als Runner-Host behandelt wird.
9. GitHub Environments werden in der aktuellen Plattform nicht eingesetzt.
   Secrets und Variablen werden als Repository Secrets beziehungsweise
   Repository Variables verwaltet.

## Konsequenzen

### Positiv

- Der vorhandene Development-VPS kann sofort als Runner- und App-Host genutzt
  werden.
- Normale Tests, Builds und App-Deployments können später GitHub-hosted Minuten
  einsparen.
- Bootstrap und Recovery bleiben unabhängig von der Self-hosted
  Runner-Plattform.
- Ein späterer Umzug der Runner auf einen dedizierten VPS erfordert keine
  grundlegende Architekturänderung.

### Negativ

- Host-Bootstraps verbrauchen weiterhin GitHub-hosted Laufzeit.
- Bei Co-Location konkurrieren Runner, Datenbanken, Monitoring und Apps um CPU,
  RAM und I/O.
- Host-Maintenance muss bewusst geplant werden, damit keine laufenden
  Self-hosted Jobs unterbrochen werden.

### Risiken und Maßnahmen

- Risiko: Self-hosted Job startet oder stoppt Host-Docker.
  Maßnahme: Bootstrap-Workflows bleiben fest auf ubuntu-24.04.
- Risiko: App-Deployment entfernt fremde Container.
  Maßnahme: eindeutige Compose-Projektnamen und kein globales
  docker system prune, docker rm -f auf alle Container oder vergleichbare
  hostweite Befehle in App-Deployments.
- Risiko: Ressourcenknappheit auf dem gemeinsamen Development-Host.
  Maßnahme: Ressourcenlimits und ausreichende Host-Reserve für Controller,
  Runner und Docker-in-Docker vorsehen.
- Risiko: Runner-Plattform fällt aus.
  Maßnahme: GitHub-hosted Bootstrap bleibt als Break-Glass- und Recovery-Pfad
  verfügbar.

## Betrachtete Alternativen

### Dedizierter Runner-VPS ab sofort

- Beschreibung: Runner-Plattform wird ausschließlich auf einem separaten Host
  betrieben.
- Vorteile: stärkste Isolation und keine Selbstabhängigkeit bei Host-Deployments.
- Nachteile: zusätzlicher Server, Kosten und Betriebsaufwand in der aktuellen
  Testphase.
- Grund der Ablehnung: derzeit steht nur ein Development-Testserver zur
  Verfügung; die Architektur erlaubt den späteren Umzug ohne Neuaufbau.

### Sämtliche Workflows Self-hosted ausführen

- Beschreibung: auch Bootstrap und Runner-Recovery laufen auf
  ephemeral-linux.
- Vorteile: maximale Einsparung GitHub-hosted Laufzeit.
- Nachteile: der Runner kann seine eigene Docker-/Host-Runtime verändern und
  dadurch den laufenden Job sowie den Recovery-Pfad unterbrechen.
- Grund der Ablehnung: zyklische Betriebsabhängigkeit und unnötiges
  Ausfallrisiko.

## Umsetzung und Übergang

- Betroffene Komponenten:
  - .github/workflows/bootstrap-fresh-host.yml
  - .github/workflows/bootstrap-managed-host.yml
  - .github/workflows/bootstrap-idempotency.yml
  - docs/34-github-runner-host.md
  - statische GitHub-Actions-Guardrails
- Migrations- oder Einführungsbedarf:
  - vorhandenen Development-VPS zunächst als gemeinsamen Runner-/App-Host
    verwenden
  - ephemeral-linux per Smoke-Test validieren
  - anschließend geeignete Tests und App-Deployments schrittweise umstellen
- Rollback oder Rückfalloption:
  - Workflows jederzeit wieder auf GitHub-hosted Runner zurückstellen
  - Bootstrap bleibt dauerhaft GitHub-hosted
- Erforderliche Folgetasks:
  - zentralen RUNNER_MODE nur für dafür geeignete Workflows einführen
  - Runner-Ressourcenlimits und Smoke-Test ergänzen
  - später optional dedizierten Runner-Host in der Inventory-Topologie wählen

## Referenzen

- Pull Request: Refs #295
- Pull Request: Refs #296
- Architektur: docs/34-github-runner-host.md
- Verwandte ADRs: ADR-0005, ADR-0006, ADR-0009
- Ersetzt: keine
- Ersetzt durch: keine
