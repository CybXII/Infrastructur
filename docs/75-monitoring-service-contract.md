# App-eigene Monitoring-Definitionen – Vertrag v1

## Trennung der Verantwortung

Das **App-Repository** verwaltet seine Prüfziele. Das **Infrastructure-Repository** verwaltet generische Prometheus-/Blackbox-/Alertmanager-/Grafana-Konfiguration, Sicherheitsregeln und Deployment. Eine App installiert keinen zweiten Monitoring-Stack und darf zentrale Targets nicht direkt ändern. Eine gemeinsame Multi-Kunden-Überwachungsplattform ist nicht Teil dieses Vertrages.

## Manifest (Beispiel, liegt im App-Repository)

```json
{
  "schema_version": 1,
  "service": "n8n",
  "environment": "development",
  "http": [{"url": "https://n8n.luft-alex.de/", "expected_status": 200}],
  "tls": [{"target": "n8n.luft-alex.de:443"}],
  "dns": [{"name": "n8n.luft-alex.de", "type": "A"}],
  "labels": {"component": "service-probe"}
}
```

V1 akzeptiert nur öffentliche DNS-Hostnamen, HTTPS/443, HTTP 200 und DNS A. Das Manifest ist beispielhaft; die n8n-Datei gehört zu [CybXII/n8n-deployment PR #3](https://github.com/CybXII/n8n-deployment/pull/3). Zusätzliche kundenspezifische IDs, Server und Umgebungen dürfen nicht implizit aus dem Repo-Namen abgeleitet werden; das weitergehende Multi-Server-/Template-Modell wird in [#291](https://github.com/Merchfactory/Infrastructure/issues/291) geklärt.

## Was bereits implementiert ist

`scripts/compile-service-monitoring.py` validiert das Manifest und schreibt **nur in ein isoliertes Staging-Verzeichnis**:

```bash
python3 scripts/compile-service-monitoring.py \
  /pfad/zum/app-repo/monitoring/service.json \
  --output-dir /tmp/monitoring-staging
```

Dabei entstehen `http/development--n8n.json`, `tls/development--n8n.json` für Prometheus `file_sd` sowie `development--n8n.dns.json` **als bloßes DNS-Metadatum**. DNS-Probes erfordern später gültige Blackbox-DNS-Module; sie sind aktuell nicht automatisch aktiv.

Prometheus besitzt generische, gegenwärtig nicht live aktivierte HTTP-/TLS-Discovery-Jobs. Der reservierte plattformeigene Targetpfad lautet `/srv/merchfactory/monitoring/targets/http|tls`, im Prometheus-Container nur lesbar. Die App-Deploy-Credentials bekommen darauf **keine** Schreibrechte.

## Was für die automatische Übernahme fehlt

Nach einem erfolgreichen App-Deployment muss der bereits berechtigte Infrastruktur-Deploymentpfad das Manifest annehmen, App/Umgebung/Zielhost **unabhängig** autorisieren, erlaubte Domains prüfen, sicher veröffentlichen und im Fehlerfall zurückrollen. Fehlgeschlagene App-Updates dürfen bisherige Monitorings nicht entfernen. Weder die CLI-Optionen des Compilers noch die Tatsache eines erfolgreichen App-Deployments sind ein Authentifizierungsnachweis.

Ein neuer dauerhaft laufender HTTP-Registrierungsdienst und eine zusätzliche OIDC-API sind **keine notwendige Bedingung für #95**. Ein späterer gesonderter Authentifizierungsmechanismus bleibt möglich, wenn die bestehende Schnittstelle nicht sicher genug ist.

## Grenzen und Testablauf

DNS-Vorprüfungen sind kein vollständiger SSRF-/Rebinding-Schutz; ausgehende Verbindungen müssen beim tatsächlichen Verbindungsaufbau auf zulässige Adressen beschränkt werden. Die geplante nftables-Policy ist **nicht live** und die zweite Blackbox-Netzwerkschnittstelle erfordert explizite Negativtests.

Der aktuelle VPS ist **Development**. Zum Testplan gehören [74](74-external-probes-design.md), [76](76-blackbox-development-preflight.md), [77](77-blackbox-development-smoke-test.md) und [78](78-blackbox-security-lab-acceptance.md). Das unabhängig laufende Windows-Watchdog-Signal ersetzt nicht Blackbox, aber dient der begrenzten externen VPS-Ausfallperspektive.

**Kein produktiver App-Registrierungscontroller und kein produktiver Blackbox-Egress sind damit freigegeben.**

## Erste Deployment-Phase: interner Blackbox-Exporter

Der neue **Development-Staging-Release** bindet `deployment/monitoring/blackbox/compose.staging.yaml` in den vorhandenen kontrollierten Monitoring-Deployment-Controller ein. Diese Variante hat ausschließlich das `internal: true` Monitoring-Netz, **kein Probe-Egress**, keine Hostports und keine aktiven App-Targets. Prometheus prüft den Exporter selbst per `blackbox-exporter:9115/metrics`; ein defekter Exporter kann so bereits im Staging alarmiert werden. Die Egress-fähige `compose.yaml` ist getrennt und bleibt ein manuelles Developer-Smoke-Testartefakt, nicht Teil des regulären Releases.

**Merge-Reihenfolge:** erfolgreicher CI-Lauf des aktuellen PR-Commits → Merge auf `development` → bestehender Monitoring-Deployworkflow mit diesem freigegebenen Commit → interner Health-/Netzwerktest auf Development. Erst danach kontrollierte, gesondert freizugebende B01–B14-Egress-Tests und die Aktivierung echter Probes. Der erste Merge bedeutet **nicht**, dass #95 vollständig abgenommen oder Produktion betroffen ist.
