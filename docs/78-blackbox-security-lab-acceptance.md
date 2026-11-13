# Issue #95 – Sicherheitsabnahme auf Development-VPS (Phase B)

Status: **Testplan, nicht ausgeführt**. Diese Dokumentation autorisiert
weder die Installation einer Host-Firewall noch ein Development-Deployment.

## Voraussetzung und Trennung

Betreiberentscheidung: **Der bestehende Development-VPS ist die Testumgebung.**
Es wird kein zusätzlicher VPS bereitgestellt. Phase B erfolgt erst **nach einem
kontrollierten, zunächst nicht aktivierten Staging-Deployment** auf diesem
Development-VPS (AlmaLinux 9.8, Docker/Compose, firewalld, nftables und
SELinux Enforcing). Ein Deploy darf nicht automatisch Firewall-Regeln
installieren oder ungeprüfte Ziele mit Internet-Egress aktivieren.

Vor jeder Netzwerkänderung müssen ein unabhängig nutzbarer administrativer
Konsolenzugang, ein zeitgesteuerter automatischer Firewall-Rollback,
exportierte aktive Rulesets, Docker-Netzwerk-Inspects und ein dokumentierter
Wiederherstellungsweg vorhanden und **nachweislich getestet** sein. Bis dahin
bleiben Probe-Egress und die dynamische Target-Übernahme deaktiviert. SSH, Traefik, n8n und der
laufende Monitoring-Core dürfen durch die Tests nicht beeinträchtigt werden.
Keine CI-Pipeline lädt diesen nftables-Entwurf ungeprüft auf einen Host.

## Negativ- und Positivmatrix

| ID | Prüfung | Erwartung |
| --- | --- | --- |
| B01 | Eigene genehmigte HTTPS-URL, A-Record öffentlich | TCP/443 und gültiger Probe-Erfolg |
| B02 | RFC1918, Loopback, Link-Local und CGNAT als Ziel | Verbindungsaufbau blockiert |
| B03 | Host-Gateway, Docker-Bridge-Gateway, Host-Dienste | Verbindungsaufbau blockiert |
| B04 | Andere Container auf Probe- und Monitoring-Bridge | Kein unerlaubter Verbindungsaufbau |
| B05 | Cloud-Metadaten-IP 169.254.169.254 | Verbindung blockiert |
| B06 | IPv6 ULA, Loopback, Link-Local, öffentliches IPv6 | Kein IPv6-Bypass |
| B07 | Redirect von genehmigtem HTTPS zu fremdem/internem Host | Kein Follow-Redirect |
| B08 | DNS-Rebinding öffentlich zu privat nach Registrierung | Verbindung weiterhin blockiert |
| B09 | Aufruf über zweite Blackbox-Netzwerkschnittstelle | Keine Egress-Umgehung |
| B10 | Docker embedded DNS und daemon-seitiger Resolver | Keine interne Namens-/Netzwerkumgehung |
| B11 | Unberechtigter Repository-/Workflow-/Environment-Caller | Registrierung zurückgewiesen |
| B12 | Ungültiges Manifest oder gescheiterte Veröffentlichung | Vorherige Registrierungen unverändert |
| B13 | Neustart, Regel-Reload und explizites Rollback | Isolierung stabil; Rest-Dienste weiter erreichbar |
| B14 | Public HTTPS plus internes Monitoring-Scraping | Beide funktionieren bei wirksamer Egress-Sperre |

## Messverfahren und Nachweise

Für jedes Szenario erfassen: Zeitstempel, OS-/Docker-/Kernel-/firewalld-
Versionen, aktives nftables-Ruleset, Container-IP/MAC/Interfaces, DNS-Antwort,
Versuchsziel, tatsächliches Verbindungsziel, tcpdump/conntrack-Beleg,
Netzwerk-Entscheidung und beobachtete Container-/Host-Folgen.
Ein HTTP-Fehler allein beweist **nicht**, dass die Firewall blockiert hat.
Gegenprüfungen müssen mit einer erreichbaren Gegenstelle erfolgen.

## Harte Stop-Gates

- Keine positive Freigabe bei funktionierendem Bypass, fehlender Regelwirkung,
  nicht nachvollziehbarer DNS-Auflösung oder fehlendem Rollback.
- Keine Live-Target-Übernahme durch vom App-Workflow selbst behauptete
  Identitäten. Nur der authentifizierte vorhandene Infrastruktur-Deploymentpfad
  darf seine vorab festgelegten App-/Environment-/Server-Berechtigungen anwenden.
  Kein direkter Schreibzugriff auf globale Prometheus-Konfiguration.
- Tests finden ausschließlich im Development-Wartungsfenster statt. Bei
  Verlust des Management-Zugangs, unerwartetem Host-Traffic oder fehlender
  Rollback-Wirkung sofort abbrechen und den gesicherten Ausgangszustand
  wiederherstellen.
- Keine Phase-C-Freigabe ohne dokumentierte B01–B14-Ergebnisse und Review.

## Abnahmeprotokoll

| Feld | Wert |
| --- | --- |
| Testhost | Bestehender Development-VPS; Tests noch nicht durchgeführt |
| Testoperator | Offen |
| B01–B14 | Nicht ausgeführt |
| Firewall-Rollback | Nicht nachgewiesen |
| Security-Review | Offen |
| Freigabe für Development | **NEIN** |
