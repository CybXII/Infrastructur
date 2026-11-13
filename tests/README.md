# Tests

## Zweck

Dieses Verzeichnis enthält automatisierte Qualitäts-, Sicherheits-, Struktur- und Wiederherstellungsprüfungen für das Infrastruktur-Repository.

## Struktur

```text
tests/
  static/
  unit/
  integration/
  smoke/
  security/
  backup/
  restore/
  fixtures/
```

### `static/`

Prüft Dateistruktur, Syntax, Benennung, Formatierung und statisch erkennbare Regelverstöße, ohne Dienste zu starten.

`test-github-actions-contexts.sh` verhindert nicht unterstützte GitHub-
Runner-Kontexte wie `runner.home`, die andernfalls erst beim echten Lauf
zu einem falschen Dateipfad führen.

### `unit/`

Testet kleine, isolierte Funktionen oder Skriptbestandteile ohne externe Systeme.

`test_create_bootstrap_test_inventories.py` prüft die Trennung zwischen
initialem und verwaltetem SSH-Benutzer sowie die Ablehnung ungültiger
Public-Key-Eingaben.

`test_validate_image_policy.py` prüft die Kanonisierung von Registry-Namen, die First-Party-/Drittanbieter-Klassifikation sowie die Ablehnung ungepinnter oder nicht allowgelisteter Images.

`test_render_service_template.py` prüft Eingabevalidierung und Platzhalterersetzung des Standard-Service-Renderers.

`test_healthcheck_policy.py` stellt sicher, dass die plattformweite Healthcheck-Policy und die Defaults im Service-Template nicht auseinanderlaufen.

`test_resource_policy.py` prüft Ressourcen-Defaults, Prioritätsklassen, Validator-Negativfälle und den Abgleich mit Template/Traefik.

`test_logging_policy.py` hält Docker-, journald-, Template- und Retention-Werte synchron und prüft, dass servicebezogene Logging-Overrides abgelehnt werden.

`test_deployment_policy.py` prüft Digestpflicht, Registry-Allowlist, Freigaben, Backup-Pflichten, destruktive Datenänderungen und Rollback-Historie.

`test_platform_validation.py` schützt die v0.5-Evidence-Matrix vor Drift: Pflichtfähigkeiten, Workflow-Jobs, Fehlerfälle sowie die Trennung zwischen Monitoring-Freigabe und Epic-Abschluss.

`test_docker_cleanup_policy.py` prüft Retention-Defaults, Rollback-Historie, Volume-/Force-Safety, Timer-Abgleich und stabile/instabile Deployment-States.

`test_monitoring_stack.py` schützt die v0.6-Architektur gegen Drift: Pflichtkomponenten und Versionen, Public-Ingress-Grenzen, Prometheus-Pullmodell, Alloy-Host-Agent, Docker-Socket-Grenze, External-Probe-Unabhängigkeit und Issue-Zuordnung.

`test_node_exporter_policy.py` schützt Node-Exporter-Release/SHA, systemd-Hardening, Monitoring-Gateway, fehlenden öffentlichen Firewall-Port, Prometheus-`file_sd`-Target und die zentralen Host-Alerts gegen Drift.

`test_cadvisor_policy.py` schützt cAdvisor-Release/SHA, Host-Agent-/Docker-Socket-Grenzen, Label-Allowlist, Monitoring-Gateway, fehlende öffentliche Portfreigabe und die Container-Recording-Rules gegen Drift.

### `integration/`

Prüft das Zusammenspiel mehrerer Komponenten in einer kontrollierten Testumgebung.

Der Fresh-Host-Test verwendet:

- `test-ansible-runtime.yaml` für einen lokalen, zustandslosen Tasklauf,
  der die konfigurierte Ansible-Callback-Laufzeit tatsächlich lädt.
- `test-bootstrap-fresh-host-preflight.yaml` für unverändernde
  Vorabprüfungen eines leeren EL9-Zielsystems.
- `test-bootstrap-fresh-host-verify.yaml` für Sicherheits- und
  Funktionsprüfungen nach dem Bootstrap.

Diese Playbooks laufen nur gegen einen ausdrücklich freigegebenen
Development-Testhost. Pull-Request-Prüfungen führen für die Fresh-Host-
Playbooks ausschließlich deren Syntaxprüfung mit einem synthetischen
Inventar aus; der lokale Runtime-Test wird vollständig ausgeführt.

`test-service-template-deployment.sh` rendert das Container-Service-Template mit künstlichen Testwerten, validiert Compose- und Image-Policy, startet einen isolierten Whoami-Container und prüft dessen Health-Endpunkt.

`test-resource-limits.sh` baut lokal ein minimales Scratch-Testimage und prüft cgroup-Limits, PID-Druck sowie containerlokales OOM-Verhalten. Der Test verwendet keine externe Image-Basis und bleibt durch harte Testlimits begrenzt.

`test-log-rotation.sh` baut ein lokales Scratch-Testimage mit hoher Lograte und prüft, dass der Docker-`local`-Driver ältere Segmente tatsächlich entfernt und den neuesten Logbestand weiterhin über `docker logs` bereitstellt.

`test-update-rollback.sh` deployt einen bekannten guten Digest, provoziert ein fehlgeschlagenes Update mit einem anderen gepinnten Image und bestätigt anschließend Release-State, `release.env`, Container-Image und HTTP-Health nach dem automatischen Rollback.

`test-reference-service-deployment.sh` startet Traefik und den ausführbaren Reference HTTP Service in getrennten Compose-Projekten auf demselben Edge-Netz. Geprüft werden HTTP→HTTPS, TLS, Readiness, Docker-Liveness, fehlende direkte Hostports, Logs sowie Persistenz über einen erzwungenen Container-Recreate.

`test-docker-retention-cleanup.sh` prüft Dry-Run, Safety-Gate, managed Stopped-Container, ungenutzte und Dangling Images, Build-Cache-Cleanup, Rollback-Digest-Schutz, laufende Container sowie den vollständigen Ausschluss persistenter Volumes.

`test-prometheus-deployment.sh` startet das gepinnte Prometheus-Image auf einem isolierten internen Monitoring-Netz und prüft Runtime-UID/GID, promtool, fehlende Hostports, Self-Scrape, Node-Exporter-`file_sd`-Target, Self-Monitoring-Rules, Retention-Flags, deaktivierte Admin-/Remote-Write-Funktionen sowie TSDB-Persistenz über einen Container-Recreate.

`test-node-exporter.sh` lädt das offizielle Node-Exporter-Release 1.12.1, verifiziert den SHA256 aus dem Upstream-Release, startet die Binary ausschließlich am internen Test-Gateway, weist die Nichterreichbarkeit auf `127.0.0.1:9100` nach, prüft den Scrape aus einem Container im internen Netz sowie CPU-, Memory-, Filesystem-, Netzwerk-, Boot- und Zeitmetriken. Anschließend validiert `promtool` Syntax und Auslöseverhalten der Host-Alerts.

`test-cadvisor.sh` lädt die offizielle cAdvisor-0.60.5-Binary, verifiziert den Upstream-SHA256, startet einen markierten Testcontainer und cAdvisor am isolierten Monitoring-Gateway. Geprüft werden CPU, RAM, Netzwerk, Startzeit/Neustart, Label-Allowlisting, fehlende globale Listener sowie der Scrape aus dem internen Monitoring-Netz. Das Standardprofil `lean` deaktiviert Filesystem- und Disk-I/O-Metriken und prueft deren Abwesenheit. Mit `CADVISOR_METRICS_PROFILE=filesystem` wird separat das Upstream-Profil mit Filesystem-Metriken geprueft. Die cAdvisor-Rules werden mit `promtool` geprüft.

### `smoke/`

Enthält kurze Funktionsprüfungen nach Bereitstellung oder Konfigurationsänderung.

### `security/`

Prüft unter anderem auf Secrets, unsichere Standardwerte, riskante Berechtigungen und bekannte Fehlkonfigurationen.

### `backup/` und `restore/`

Validieren Sicherungsdefinitionen, Integrität, Wiederherstellbarkeit und erwartete Wiederanlaufabläufe. Tests dürfen niemals produktive Daten verändern.

### `fixtures/`

Enthält ausschließlich künstliche, anonymisierte und nicht produktive Testdaten.

## Namenskonventionen

- Shell-Tests: `test-<beschreibung>.sh`
- Python-Tests: `test_<beschreibung>.py`
- Testdaten: `<beschreibung>.fixture.*`
- Dateien und Verzeichnisse verwenden `kebab-case`, sofern das jeweilige Testframework nichts anderes verlangt.
- Jeder Test liefert bei Erfolg Exit-Code `0` und bei Fehler einen von `0` verschiedenen Exit-Code.

## Mindestanforderungen

Jeder Test muss:

1. reproduzierbar und ohne produktive Zugangsdaten ausführbar sein,
2. Eingaben und Voraussetzungen validieren,
3. verständliche Fehlermeldungen ausgeben,
4. Seiteneffekte vermeiden oder vollständig aufräumen,
5. lokal und in CI mit demselben Aufruf funktionieren.

## Lokale Ausführung

Die vorbereiteten Strukturtests werden über folgenden Befehl ausgeführt:

```bash
bash tests/static/test-repository-structure.sh
bash tests/static/test-github-actions-contexts.sh
```

Weitere Testkategorien erhalten einen dokumentierten Einstieg, sobald das jeweilige Framework eingeführt wird.

Die lokalen Fresh-Host-Prüfungen ohne Serverzugriff werden ausgeführt mit:

```bash
python3 -m unittest discover -s tests/unit -p 'test_*.py'
bash -n scripts/test-bootstrap-fresh-host.sh
```

## CI-Integration

`.github/workflows/tests.yml` führt die statischen Strukturprüfungen bei Pull Requests und Pushes auf die dauerhaften Branches aus. Neue Tests werden nach Testkategorie ergänzt und müssen ohne Secrets ausführbar sein.

`.github/workflows/image-security.yml` prüft die Registry-Policy und scannt tatsächlich verwendete Plattformimages mit einer fest gepinnten Trivy-Version. HIGH/CRITICAL werden berichtet; fixbare CRITICAL-Funde blockieren den normalen Merge-/Releasepfad.

Tests für Deployments, Backup oder Restore dürfen in CI zunächst nur gegen isolierte Testartefakte beziehungsweise ausdrücklich freigegebene Testumgebungen laufen.

## Abgrenzung

- Wiederverwendbare Prüf- und Hilfslogik gehört nach `scripts/`.
- Produktive Healthchecks werden unter `monitoring/` oder `deployment/` definiert und können von Tests aufgerufen werden.
- Testdaten dürfen keine realen Secrets, Kundendaten, produktiven Domains oder privaten IP-Zuordnungen enthalten.

## Referenzen

- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`
- `.github/workflows/tests.yml`
