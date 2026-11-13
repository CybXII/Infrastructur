# Blackbox #95 – Development-Preflight und Abnahmetracking

Stand: 2026-10-15. **Diese Befunde sind rein lesend ermittelt; keine
Firewall-Regel und kein Blackbox-Container wurde aktiviert.**

## Vorliegende VPS-Fakten (vom Betreiber geprüft)

| Check | Beobachtung | Interpretation |
| --- | --- | --- |
| OS | AlmaLinux 9.8 | Zielplattform EL9 bestätigt |
| Docker Compose | 5.4.0 | CLI vorhanden; Engine-Version noch offen |
| Docker-Dienst | active | Laufzeit läuft |
| firewalld | running / active | Host-Firewall aktiv |
| nftables | 1.0.9 | Binary vorhanden; tatsächliche nft-Syntax noch nicht geprüft |
| SELinux | Enforcing | MAC aktiv |
| firewalld-Default-Zone | public | Basiszone aktiv |
| Docker-Zone | target ACCEPT, forwarding yes | Docker-Bridge-Schutz erfordert explizite egress-Gates |
| Monitoring-Netz | merchfactory-monitoring | Netzwerk existiert |
| Alertmanager-Egress | merchfactory-alerting-egress | Netzwerk existiert |
| Probe-Egress | noch nicht vorhanden | Erwartet: Draft nicht ausgerollt |

Die Docker-Netzwerk-Daten (Subnetz, Gateway, EnableIPv6, Bridge-Optionen)
wurden bislang **nicht zuverlässig abgefragt**, da Template-Braces in
einem Terminal-Paste als HTML-Entities erschienen.

## Nächste ungefährliche Hostprüfung

Keine Netzwerke anlegen, keine Rules laden, keinen Container starten.
Für das Prüfen der tatsächlichen Laufzeitumgebung diese **nur lesenden**
Befehle auf dem Development-VPS ausführen:

```bash
sudo docker version
sudo docker network inspect merchfactory-monitoring
sudo docker network inspect merchfactory-alerting-egress
sudo firewall-cmd --zone=docker --list-all
sudo nft --version
sudo getenforce
```

**Hinweis:** Vor dem Teilen von `docker network inspect` Ausgaben prüfen,
ob unerwünschte vertrauliche Metadaten oder Containeridentifikatoren enthalten
sind. Zum Abgleich werden `Internal`, `EnableIPv6`, `IPAM.Config`,
`Options` und `Labels` benötigt.

## Tatsächliche Blocker und Arbeitsreihenfolge (16.10.2026)

1. Digest-, Trivy- und Container-Healthcheck-Voraussetzungen des Blackbox-Images müssen auf dem **aktuellen** PR-Head erfolgreich sein.
2. Zunächst die intern isolierte Blackbox-Staging-Compose-Datei durch den vorhandenen Development-Monitoring-Release-Controller bereitstellen und im Runner sowie auf dem Development-VPS prüfen. **Keine öffentlichen Probeziele, kein Egress-Interface, keine Firewall-Änderung**. Erst anschließend den getrennten, manuell freizugebenden Probe-Smoke-Test nach [77](77-blackbox-development-smoke-test.md) durchführen; keine fremddefinierten App-Ziele.
3. Die nftables-Egress-Policy ist weiterhin **DRAFT**. Vor Regeländerungen: laufende Regeln und Netze sichern, unabhängigen Adminzugang und zeitgesteuerten automatischen Rollback **real testen**. Danach B01–B14 gemäß [78](78-blackbox-security-lab-acceptance.md) auf diesem Development-VPS; Abbruch beim ersten Bypass.
4. Die automatische Manifest-Übernahme braucht einen nachweislich **berechtigten Infrastruktur-Deploymentpfad** sowie atomisches Target-Publishing. App-CI erhält keine direkten Schreibrechte auf Prometheus.
5. DNS-Modulkonfiguration, Prometheus-/Grafana-Integration und Discord FIRING/RESOLVED bleiben separate Live-Abnahmekriterien. Bis dahin kein produktives Deployment.

Ein zusätzlicher OIDC-/HTTP-Registrierungsservice gehört **nicht** zur Definition of Done von #95. Historische CI-Fails zu Commit-Konventionen und Runner-Downloads sind keine Aussagen über den aktuellen PR-Head; aktuelle Checks separat nachprüfen.

## Externer Watchdog

Der separate Windows-Aufgabenplanungs-Watchdog prüft die öffentliche n8n-URL
in Fünf-Minuten-Abständen; HTTP 200 wurde im Betreiberlog wiederholt
bestätigt. Er wird nun mittels `wscript.exe` fensterlos gestartet;
die interne Prometheus/Blackbox-Prüfung ersetzt ihn nicht.
Ein erfolgreicher HTTP-Check belegt weder Discord-Alarmpfad bei Fehler
noch Verfügbarkeit bei ausgeschaltetem Windows-Rechner.
