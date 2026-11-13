# Issue #95 – Development-VPS-Netzwerk-Inventar (2026-10-15)

## Herkunft und Umfang

Read-only-Ausgaben des Betreibers vom Development-VPS `luft-alex.de`.
Es wurden **keine** Änderungen am Host vorgenommen. Dies ist ein
**Bestandsnachweis**, kein Live-Blackbox- oder Firewall-Abnahmenachweis.

## Host

| Element | Beobachteter Wert |
| --- | --- |
| Betriebssystem | AlmaLinux 9.8 |
| Architektur | linux/amd64 |
| Docker Engine (Client + Server) | 29.7.2, API 1.55 |
| containerd | 2.3.3 |
| runc | 1.4.3 |
| Docker Compose | v5.4.0 |
| nftables | 1.0.9 |
| SELinux | Enforcing |
| Docker-Dienst | active |
| firewalld | active |
| Standard-Zone | public |
| Docker-Zone | docker, Target ACCEPT, forward yes |

Der Benutzer `bootstrap` darf den Docker-Socket nicht direkt nutzen.
Die Docker-Abfragen wurden erfolgreich mit `sudo docker` ausgeführt.
Die Docker-Zone mit ACCEPT-Target ist **keine Bestätigung**, dass
Blackbox-Traffic schon ausreichend gefiltert wäre.

## Beobachtete Docker-Netze

| Eigenschaft | `merchfactory-monitoring` | `merchfactory-alerting-egress` |
| --- | --- | --- |
| Driver | bridge | bridge |
| Internal | true | false |
| EnableIPv4 | true | true |
| EnableIPv6 | false | false |
| Subnet | 172.30.250.0/24 | 172.30.251.0/29 |
| Gateway | 172.30.250.1 | 172.30.251.1 |
| Bridge | mf-monitoring0 | mf-alert-egress |
| Label class | monitoring | alerting-egress |
| managed | true | true |
| Attachable | false | false |

### Beobachtete Belegung

- Prometheus: `172.30.250.2`
- Loki: `172.30.250.10`
- Grafana: `172.30.250.20`
- Alertmanager: `172.30.250.30`
- Alertmanager Egress: `172.30.251.2`

## Abgleich mit Issue #95

- Die vorgesehene Blackbox-Monitoring-IP `172.30.250.40` war in der
  gelieferten Momentaufnahme **nicht belegt**. Das garantiert keine
  künftige Verfügbarkeit; der Deploy muss sie bei Start erneut prüfen.
- Das separate `merchfactory-probe-egress` (`172.30.252.0/29`,
  `mf-probe-egress`) war im gelieferten `docker network ls` **nicht
  vorhanden**. Es darf nicht unkontrolliert im Live-Betrieb angelegt werden.
- Das Alertmanager-Egress-Netz darf nicht als Blackbox-Probe-Netz
  wiederverwendet werden.
- Die vorherigen `nftables`-Entwürfe sind **nicht installiert und nicht
  verifiziert**. Die tatsächliche Docker-Firewall mit `ACCEPT` verlangt
  ausdrücklich Negativtests für FORWARD, INPUT und Verkehr innerhalb
  derselben Bridge beziehungsweise Container-Netz-Namespace.
- Ein Host-Firewall-`nft -c`-Syntaxcheck reicht nicht aus, um Routing-,
  Docker-DNS-, IPv6- oder DNS-Rebinding-Schutz zu beweisen.

## Noch offene Prüfschritte

1. In einer isolierten Umgebung mit AlmaLinux 9.8, Docker 29.7.2,
   firewalld und nftables 1.0.9 die Regeln syntaktisch und funktional testen.
2. Blackbox-Probe-Netz gegen bereits vergebene Docker-Subnetze und
   IP-Reservierungen auf dem Host prüfen.
3. Öffentliche HTTPS-Ziele erlauben; private RFC1918-, Link-Local-,
   Host-/Docker-Gateway- und Metadata-Ziele sowohl über TCP-Verbindung
   als auch per DNS-Rebinding verhindern.
4. Container-zu-Container-Kommunikation und die zweite Netzwerkschnittstelle
   mitprüfen; kritische Regeln nicht nur im `forward`-Hook erwarten.
5. SELinux, Docker-Zone, Traefik, Prometheus, Alertmanager und Discord nach
   der Aktivierung **und nach Rollback** prüfen.
6. Image-Digest und Scannergebnis nachweisen; separaten, authentifizierten
   App-Target-Übernahme über den berechtigten Infrastruktur-Deploymentpfad vorsehen.

**Betriebsentscheidung:** Bis diese Nachweise dokumentiert sind, bleiben
Infrastructure PR #324 und n8n PR #3 Draft. Kein Firewall-Apply, kein
Blackbox-Deployment und kein Merge auf Grundlage dieses Inventars.
