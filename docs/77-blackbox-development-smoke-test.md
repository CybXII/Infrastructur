# Issue #95 – Blackbox Development Smoke Test

**Geltung:** ausschließlich Development-VPS `luft-alex.de`. Dies ist
eine **manuelle**, explizit gesteuerte technische Probe. Kein automatisches
CI-Deployment, keine Änderung von Host-Firewall, firewalld, nftables,
Traefik oder Monitoring-Core. Keine Freigabe für beliebige App-Targets.

## Was der Test nachweist

Der Blackbox Exporter kann im vorgesehenen Container mit einem internen
Monitoring-Interface (`172.30.250.40`) und eigenem Egress-Interface
(`172.30.252.2`) laufen, ohne einen Host-Port zu publizieren. Der
Test prüft einen explizit übergebenen, vertrauenswürdigen öffentlichen HTTPS-Endpunkt sowie dessen TLS-Handshake und erwartet
jeweils `probe_success=1`.

**Was dieser Test nicht nachweist:** SSRF-Schutz, sichere Durchsetzung
einer Ziel-Allowlist, Schutz vor DNS-Rebinding, automatische
Service-Registrierung, Prometheus-Target-Auslieferung, Alarmzustellung,
echte Docker-/firewalld-Isolation und vollständigen Produktionsbetrieb.

## Vorbedingungen

- Image-Digest: Docker Hub führt den hinterlegten Multi-Arch-Indexdigest
  `sha256:9613f2884689b6fad9f1939f6a3b0388c93a022cfaededb19545b329b5c83dea`
  als `prom/blackbox-exporter:v0.29.0` (linux/amd64 unterstützt).
  Referenz: https://hub.docker.com/layers/prom/blackbox-exporter/v0.29.0
- **Upgrade-Kandidat v0.29.0:** Das Image-Security-Workflow-Job `Verify Blackbox v0.29.0 candidate` löst den tatsächlichen Registry-Digest im CI-Runner auf und prüft das unveränderliche Image mit Trivy. Der Kandidaten-Job hat bestanden (4 HIGH, 0 CRITICAL; Stand 16.10.2026); die Compose-Referenz wurde auf diesen konkreten Digest umgestellt. Weitere Image-Security-Gates laufen erneut nach der Änderung.
- Der verpflichtende Trivy-Sicherheitslauf ist im Image-Security-Workflow
  unter `Scan Blackbox image` ergänzt. Vor `start` muss dessen
  erfolgreicher CI-Abschluss geprüft werden; der Digest allein ist kein
  Schwachstellen-/Provenienz-Nachweis.
- Nur autorisierte Administratoren auf dem eigenen Development-VPS.
  Der Bediener gibt die freigegebene öffentliche Testdomain beim Verify-Schritt an.
- `docker`, Docker Compose, Python 3 und `curl` sind auf dem Host
  installiert; vorhandenes internes Monitoring-Netz ist korrekt.
- Container `172.30.250.40` darf nicht bereits vergeben sein.
- Der Test-Container kann nach dem Start über seine getrennte Bridge
  öffentliches HTTPS erreichen. **Bis eine Egress-Policy geprüft und
  aktiviert wurde, ist Netzwerk-Egress nicht zuverlässig auf die
  festgelegte Domain begrenzt.**
- Kein anderer Prozess legt gleichzeitig das Probe-Egress-Netz an.

Die Beispiel-Domain `example.org` ist nur ein Platzhalter: Beim echten Test eine ausdrücklich freigegebene öffentliche HTTPS-Origin eintragen. Das Testskript nimmt nur `https://hostname.tld` ohne Pfad, Port, Parameter oder Credentials entgegen; diese Eingabeprüfung ersetzt **keine DNS-/Egress-Sicherheitsgrenze**. Die Anwendung wird durch den Parameter bestimmt, nicht durch den Infrastructure-Code.

## Manuell durchzuführende Schritte

Auf dem Development-VPS im Checkout des PR-Branches:

```bash
sudo bash scripts/smoke-blackbox-development.sh check
sudo bash scripts/smoke-blackbox-development.sh start
sudo bash scripts/smoke-blackbox-development.sh verify https://example.org
sudo bash scripts/smoke-blackbox-development.sh stop
```

`check` führt keine Änderung durch. `start` legt gegebenenfalls
das zusätzliche, allein für Blackbox vorgesehene Docker-Bridge-Netz an
und startet ausschließlich den Blackbox-Container. `verify` erwartet
für die angegebene HTTP- und TLS-Probe den Wert `probe_success 1`. `stop`
entfernt den Smoke-Test-Container, **nicht** die gemeinsam genutzten
Docker-Netzwerke.

Fehler bei `start` oder `verify` erfordern Untersuchung der Logs:

```bash
sudo docker compose -p merchfactory-development-blackbox \
  -f deployment/monitoring/blackbox/compose.yaml logs --tail 100
sudo bash scripts/smoke-blackbox-development.sh stop
```

### Abnahme

- Kein Public-Ingress und keine öffentlich gebundenen Docker-Ports.
- Zwei `probe_success 1`-Werte (HTTP + TLS), dokumentierte Zeit.
- Container nach `stop` nicht mehr vorhanden; Monitoring-Core bleibt
  erreichbar.
- Blackbox-Image-Digest und CVE-Scan sind dokumentiert.
- Keine Änderung an System-Firewall und keine Änderung am regulären
  Deployment des Monitoring-Core.

**Hinweis:** Ein VM-/Host-unabhängiger Netzwerk-Schutz wird in diesem
Smoke-Test ausdrücklich **nicht behauptet**. Der Schritt ist
grundsätzlich nur für kontrollierte Developer-Tests mit nicht frei
konfigurierbaren, vertrauenswürdigen Zielen geeignet.

## Danach

Bei erfolgreichem Test den regulären Deployment-Controller und dessen
Rollback um Blackbox erweitern, die statischen Prometheus-Zielmanifest-
Daten einer beispielhaften Anwendung kontrolliert veröffentlichen, Alertmanager-Test prüfen,
dann App-Ziele ausschließlich über den bestehenden berechtigten
Infrastruktur-Deploymentpfad übernehmen. Ein neuer OIDC-/HTTP-Registrar
ist nicht Teil des #95-Mindestumfangs. Solange diese Punkte offen sind, bleiben PR #324 und
n8n PR #3 Draft.

## Separate reguläre Staging-Bereitstellung (ohne Egress)

Der reguläre Infrastructure-Release verwendet **nur** `deployment/monitoring/blackbox/compose.staging.yaml`. Diese Staging-Variante ist ausschließlich im Docker-Netz `merchfactory-monitoring` und hat **keine** Internet-Egress-Netzwerkschnittstelle. Der Core-Deployment-Controller prüft den internen Health-Endpunkt und führt den Blackbox-Zustand in seinem bestehenden Release-/Rollback-Verfahren. Das Deployment muss abbrechen, wenn bereits aktive app-eigene `file_sd`-Targets vorhanden sind; es lädt keine nftables-Regeln und aktiviert **keine** Public-Probes.

Der oben dokumentierte `smoke-blackbox-development.sh` verwendet dagegen absichtlich die **separate**, manuelle Compose-Datei `compose.yaml` mit Probe-Egress. Der Smoke-Versuch darf nicht gleichzeitig mit dem regulär gestarteten Staging-Container laufen: Beide besitzen denselben Docker-Compose-Projektnamen. Vor einem Egress-Smoke ist der Staging-Container kontrolliert aus dem Release-Prozess heraus anzuhalten, ohne bestehendes Monitoring zu unterbrechen. Vor produktionsähnlicher Aktivierung müssen die Firewall-Tests B01–B14 durchgeführt werden.

Der Staging-Merge ist **keine Abschluss-Abnahme von #95**; er ermöglicht erstmals einen tatsächlichen, kontrollierten Container-Lauf auf dem Development-VPS. Es gibt dadurch weiterhin keine automatische Freigabe für beliebige app-eigene Probeziele.
