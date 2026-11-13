# Zukünftige Plattform-Erweiterungen

## Zweck

Dieses Dokument hält mögliche spätere Ausbaustufen der Infrastruktur fest. Es ist **keine aktuelle Umsetzungsverpflichtung** und erweitert den Scope von v0.4 nicht. Ziel ist, die heutige Bootstrap- und Containerbasis so zu gestalten, dass spätere Skalierung, Rollenverteilung und Hochverfügbarkeit ohne vollständigen Neuaufbau möglich bleiben.

## Aktueller Ausgangspunkt

Die derzeitige Roadmap konzentriert sich zunächst auf:

- reproduzierbaren Bootstrap eines bereits bereitgestellten Servers,
- einheitliche Betriebssystem- und Sicherheitsbasis,
- idempotente Serverkonfiguration mit Ansible,
- standardisierte Containerplattform,
- nachvollziehbare Deployments und Rollbacks,
- dokumentierte Backups und Wiederherstellungsprozesse.

Das Betriebssystem selbst wird aktuell nicht durch die CI/CD-Pipeline installiert. Der Zielserver muss mit einem unterstützten Betriebssystem bereitgestellt werden. Der Bootstrap prüft das System und konfiguriert anschließend den gewünschten Zustand.

## Mögliche spätere Ausbaustufen

### 1. Rollenbasierte Mehrserver-Architektur

Mehrere Server können über Inventargruppen unterschiedliche Aufgaben erhalten.

Beispiel:

```yaml
load_balancers:
  hosts:
    lb-01:

app_servers:
  hosts:
    app-01:
    app-02:

database_servers:
  hosts:
    db-01:

monitoring_servers:
  hosts:
    mon-01:

backup_servers:
  hosts:
    backup-01:
```

Gemeinsame Rollen wie Basisinstallation, Benutzerverwaltung, Hardening, Logging und Monitoring werden auf alle Server angewendet. Spezifische Rollen werden nur den jeweiligen Hostgruppen zugeordnet.

### 2. Getrennte Anwendungs-, Datenbank- und Infrastrukturrollen

Dienste können später gezielt verteilt werden:

- Load Balancer beziehungsweise Reverse Proxy,
- mehrere Anwendungsinstanzen,
- separate Datenbankserver,
- zentrale oder replizierte Dateiablage,
- Monitoring und Alarmierung,
- Backup- und Restore-Infrastruktur,
- interne Registry und Secret-Verwaltung.

Dadurch sinkt die Kopplung zwischen Anwendung, Daten und Hostsystem.

### 3. Horizontale Skalierung von Anwendungen

Anwendungen können mehrfach bereitgestellt werden:

```text
Load Balancer
├── App 1
└── App 2
```

Healthchecks entfernen fehlerhafte Instanzen aus dem Routing. Neue Instanzen können aus einem freigegebenen Container-Image gestartet werden.

Voraussetzungen dafür sind unter anderem:

- zustandslose oder kontrolliert zustandsbehaftete Anwendung,
- ausgelagerte Sessions,
- gemeinsame Datenbank,
- gemeinsamer oder replizierter Object Storage,
- reproduzierbare Secrets und Konfigurationen,
- automatisierte Healthchecks.

### 4. Hochverfügbarkeit und automatisches Failover

Eine spätere Hochverfügbarkeitsstufe kann umfassen:

- redundante Load Balancer,
- mindestens zwei Anwendungsinstanzen,
- Datenbankreplikation und kontrolliertes Failover,
- replizierten oder hochverfügbaren Storage,
- Ausfallüberwachung,
- automatische Umschaltung,
- dokumentierte RTO- und RPO-Ziele.

Der Bootstrap allein stellt keine Wiedererreichbarkeit innerhalb weniger Sekunden sicher. Dafür müssen Dienste bereits redundant betrieben werden.

### 5. Vollautomatisches Provisioning

Der heutige Bootstrap setzt einen bereits installierten Server voraus. Eine spätere vorgelagerte Provisioning-Schicht könnte zusätzlich Server und Betriebssystembereitstellung automatisieren, zum Beispiel mit:

- Terraform,
- Cloud-Provider-APIs,
- Cloud-Init,
- Kickstart,
- PXE beziehungsweise Netzwerk-Boot.

Diese Schicht würde Serverressourcen erstellen und anschließend den bestehenden Ansible-Bootstrap starten.

### 6. Multi-Provider- oder Standortbetrieb

Für höhere Ausfallsicherheit kann die Plattform später auf mehrere Provider oder Standorte verteilt werden.

Zu klären wären dann insbesondere:

- DNS- oder Anycast-Failover,
- Datenreplikation zwischen Standorten,
- Latenz und Konsistenz,
- Secret-Verteilung,
- Backup-Isolation,
- Kosten und Betriebsaufwand,
- rechtliche und datenschutzrechtliche Anforderungen.

### 7. Optionale kundenübergreifende Betreiberübersicht – erst nach v1.0

Spätere Idee für den persönlichen Managed-Infrastructure-Betrieb:
eine **zentrale Statusübersicht** für betreute Kunden-/Serverumgebungen,
offene Alarme, Updates, Datenbankzustände und Backup-/Restore-Ergebnisse.
Von dort kann das jeweilige **separat funktionierende** Kunden-Grafana
oder Runbook geöffnet werden.

Jede Infrastruktur-Instanz behält eigenständiges Monitoring, Alertmanager,
Discord-Routing, Secrets, Daten und Wiederherstellung. Die persönliche
Übersicht darf **keine Laufzeitabhängigkeit** der einzelnen Kunden schaffen.
Zugriffsschutz, Mandantentrennung, DSGVO und Datensparsamkeit müssten vor
Umsetzung neu geprüft werden.

**Geparkt unter [Issue #325](https://github.com/Merchfactory/Infrastructure/issues/325).**
Keine Umsetzung in v0.6, #95, der ersten Template-Ausbaustufe oder vor v1.0.

## Architekturprinzipien für heutige Entscheidungen

Neue Bootstrap- und Plattformfunktionen sollen folgende Erweiterbarkeit berücksichtigen:

1. Rollen dürfen nicht unnötig an einen einzelnen Hostnamen gekoppelt sein.
2. Hostgruppen und hostspezifische Variablen müssen sauber getrennt werden.
3. Anwendungen sollen aus versionierten, getesteten Images deploybar sein.
4. Persistente Daten dürfen nicht unkontrolliert an kurzlebige Container gebunden sein.
5. Secrets dürfen nicht im Repository oder in Logs gespeichert werden.
6. Healthchecks, Logging und Monitoring sollen bei neuen Diensten vorgesehen werden.
7. Backups und Restore müssen unabhängig vom ursprünglichen Server möglich sein.
8. Einzelserverbetrieb bleibt zulässig, darf spätere Mehrserver-Nutzung aber nicht unnötig blockieren.

## Abgrenzung zur aktuellen Roadmap

Folgende Punkte sind derzeit nur Zukunftsoptionen und nicht Bestandteil von v0.4:

- automatische Installation des Betriebssystems,
- automatische Bereitstellung neuer VPS oder Cloud-Instanzen,
- Multi-Server-Orchestrierung,
- Datenbankcluster,
- Load-Balancer-Redundanz,
- automatisches standortübergreifendes Failover,
- Kubernetes oder eine vergleichbare Clusterplattform.

Konkrete Umsetzung erfolgt erst über eigene Epics, Architekturentscheidungen und Tests.

## Mögliche spätere Epics

Bei Bedarf können aus diesem Dokument eigenständige Arbeitspakete entstehen:

- Infrastructure Provisioning,
- Multi-Server Inventory & Roles,
- Application High Availability,
- Database High Availability,
- Central Object Storage,
- Multi-Site Disaster Recovery,
- Automated Failover & Recovery Tests.

## Leitgedanke

Die aktuelle Infrastruktur soll zunächst einen Server schnell, sicher und reproduzierbar betriebsbereit machen. Spätere Erweiterungen können darauf aufbauen, mehrere Server mit unterschiedlichen Rollen vorzubereiten und Anwendungen redundant zu betreiben, ohne die heutige Grundlage neu entwerfen zu müssen.
