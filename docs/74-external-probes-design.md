# #95 – Erreichbarkeit, DNS und TLS-Zertifikate

## Maßgeblicher Umfang

Die ursprüngliche [Definition of Done von #95](https://github.com/Merchfactory/Infrastructure/issues/95) umfasst öffentliche Erreichbarkeit, HTTP-Status und -Antwortzeit, TLS-Zertifikatslaufzeiten sowie unterscheidbare DNS-/TLS-/HTTP-Fehler. Kein neues universelles Registrierungsprodukt, keine kundenübergreifende Monitoring-Plattform.

- **Infrastruktur:** Ein vorhandener Prometheus-/Grafana-/Alertmanager-Stack pro Infrastrukturinstanz, ergänzt durch Blackbox Exporter. Nicht ein Monitoring-Stack pro App.
- **App:** Das App-Repository besitzt seine eigene Endpoint-Definition `monitoring/service.json`; keine feste App-Domain in zentralen generischen Konfigurationen.
- **Handoff:** Nur ein autorisierter Infrastruktur-Deploymentprozess darf diese Definition gegen die freigegebenen App-/Environment-/Host-Zuordnungen prüfen und daraus Targets veröffentlichen. App-Workflows erhalten **keine** direkten Schreibrechte auf zentrale Monitoring-Verzeichnisse.
- **Kein verpflichtender OIDC-Registrierungsdienst:** Der Handoff soll die vorhandenen Deployment-Identitäten wiederverwenden. Wenn diese Berechtigungsgrenze noch nicht nachgewiesen ist, bleibt der automatische Handoff deaktiviert, ohne dafür vorzeitig eine neue HTTP-API zu bauen.

## Vorgehen auf Development (keine Produktion)

1. Image-/Compose-Security-Prüfungen und vorhandene Unit-/Integrationstests.
2. Zunächst isolierte, egress-freie Blackbox-Staging-Bereitstellung über den bestehenden Release-Controller auf dem Development-VPS; danach ein separat genehmigter manueller Probe-Smoke mit freigegebener Testdomain.
3. Vor Firewall-Änderungen unabhängigen administrativen Zugang und automatischen Firewall-Rollback **nachweislich** testen.
4. Nach Staging-Deployment auf dem Development-VPS die negative Egress-/SSRF-/DNS-Rebinding-/Bridge-Testmatrix [#78](78-blackbox-security-lab-acceptance.md) durchführen.
5. Danach erst HTTP-/TLS-/DNS-`file_sd`-Integration, Zertifikatsalarme, Grafana und echte Discord-FIRING/RESOLVED-Meldungen abnehmen.

Ein interner Exporter bemerkt nicht zuverlässig den vollständigen Ausfall seines VPS. Der schon vorhandene Windows-Watchdog bietet eine **begrenzte** unabhängige externe Prüfstelle, solange der PC läuft; er ist keine 24/7-Verfügbarkeitsgarantie.

## Status / Abnahmecheckliste

- [ ] Blackbox-Exporter ohne Host-Port, digest-gepinnt und sicher geprüft auf Development ausgerollt.
- [ ] HTTP-/TLS-/DNS-Probes funktionieren, Fehlerklassen sind unterscheidbar.
- [ ] Zertifikatswarnung vor Ablauf und Alertmanager/Discord-FIRING+RESOLVED nachgewiesen.
- [ ] Egress- und Rollback-Tests B01–B14 auf Development dokumentiert.
- [ ] App-eigene Ziele nur über den berechtigten Infrastruktur-Deploymentpfad übernommen.
- [ ] Grafana-Darstellung und Runbook geprüft.

PR #324 ist bis zur kontrollierten Integration ein Draft. Die App-Seite wird separat in [n8n PR #3](https://github.com/CybXII/n8n-deployment/pull/3) entwickelt. Template-/Serverstrategie: [#291](https://github.com/Merchfactory/Infrastructure/issues/291). Eine optionale spätere persönliche Betreiberübersicht ist unter [#325](https://github.com/Merchfactory/Infrastructure/issues/325) geparkt.
