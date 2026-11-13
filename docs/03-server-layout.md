# Server- und Infrastrukturmodell

## 1. Ziel

Dieses Dokument definiert die verbindlichen Serverrollen, Verantwortungsbereiche, Datenablagen und Abhängigkeiten der Merchfactory Infrastructure Platform. Das Modell muss sowohl den Betrieb auf einem einzelnen VPS als auch eine spätere Aufteilung auf mehrere Systeme unterstützen.

Verknüpft mit Issue #5 und Epic #2.

## 2. Grundprinzipien

- Serverrollen werden logisch definiert und können anfangs auf einem Host konsolidiert werden.
- Persistente Daten, Konfigurationen und Secrets werden getrennt behandelt.
- Jeder Dienst muss reproduzierbar aus Repository, Konfiguration und Backup wiederherstellbar sein.
- Öffentliche Dienste werden ausschließlich über den Reverse Proxy veröffentlicht.
- Interne Verwaltungs- und Datenbankdienste sind nicht direkt aus dem Internet erreichbar.
- Produktions-, Staging- und Entwicklungsumgebungen werden logisch und später bei Bedarf physisch getrennt.

## 3. Logische Serverrollen

### 3.1 Edge- und Proxy-Rolle

**Zweck**

- Annahme externer HTTP- und HTTPS-Verbindungen
- TLS-Terminierung
- Routing auf interne Dienste
- Zentrale Zugriffskontrolle für veröffentlichte Webdienste

**Kernkomponenten**

- Traefik
- ACME-Zertifikatsverwaltung
- optionale vorgeschaltete Zugriffsschutz- oder Rate-Limit-Komponenten

**Persistente Daten**

- ACME-Zertifikatsspeicher
- statische und dynamische Proxy-Konfiguration

**Abhängigkeiten**

- DNS
- öffentliche IP-Adresse
- Docker-Netzwerke der veröffentlichten Dienste

### 3.2 Application-Rolle

**Zweck**

- Betrieb geschäftlicher Anwendungen und Automatisierungen
- Ausführung interner APIs, Worker und Integrationsdienste

**Beispiele**

- n8n
- interne Middleware
- Shopify-/DecoNetwork-Integrationen
- Odoo-nahe Hilfsdienste
- PDF- und Produktionsdatei-Verarbeitung

**Persistente Daten**

- anwendungsspezifische Volumes
- Uploads und Arbeitsdateien
- Queue- und Statusdaten, sofern nicht in PostgreSQL gespeichert

**Abhängigkeiten**

- Reverse Proxy
- Datenbank-Rolle
- Secret-Management
- Monitoring und Logging

### 3.3 Database-Rolle

**Zweck**

- Bereitstellung relationaler Datenbanken für Plattformdienste

**Kernkomponenten**

- PostgreSQL
- optional PgBouncer bei späterem Skalierungsbedarf

**Persistente Daten**

- PostgreSQL-Datenverzeichnisse
- WAL-/Backup-relevante Daten

**Abhängigkeiten**

- Backup-Ziel
- internes Netzwerk
- Monitoring

**Sicherheitsanforderungen**

- keine öffentliche Portfreigabe
- Zugriff ausschließlich aus definierten internen Netzwerken
- separate Benutzer und Datenbanken pro Anwendung

### 3.4 Observability-Rolle

**Zweck**

- Sammlung und Auswertung von Metriken, Logs und Alarmen

**Kernkomponenten**

- Prometheus
- Grafana
- Loki
- Alloy
- Alertmanager

**Persistente Daten**

- Metriken
- Logs
- Dashboards und Alert-Regeln

**Abhängigkeiten**

- erreichbare Exporter und Telemetrie-Endpunkte
- Benachrichtigungskanäle
- Backup für Konfigurationen und Dashboards

### 3.5 Backup-Rolle

**Zweck**

- Erstellung, Verschlüsselung, Prüfung und externe Ablage von Backups

**Verantwortungsbereich**

- Datenbank-Dumps
- Volume-Backups
- Konfigurations-Backups
- Integritätsprüfungen
- Restore-Vorbereitung

**Persistente Daten**

- lokaler Staging-Bereich für Backups
- Metadaten und Prüfsummen

**Abhängigkeiten**

- Offsite-Ziel
- Secret-Management für Verschlüsselung und Zugang
- Monitoring

### 3.6 Management- und Bootstrap-Rolle

**Zweck**

- Reproduzierbare Bereitstellung und Verwaltung der Infrastruktur

**Kernkomponenten**

- Ansible
- Shell- und Python-Hilfswerkzeuge
- GitHub Actions für validierte Automatisierung

**Verantwortungsbereich**

- Benutzer und Gruppen
- SSH-Hardening
- Firewall
- Fail2ban
- Docker-Installation
- Host- und Service-Konfiguration

Diese Rolle kann lokal auf einer Administrator-Workstation, einem dedizierten Management-Host oder über kontrollierte GitHub Actions ausgeführt werden.

## 4. Physische Ausbaustufen

### 4.1 Startmodell: Einzelner Produktions-VPS

Zum Projektstart können folgende Rollen auf einem VPS konsolidiert werden:

- Edge/Proxy
- Applications
- Database
- Observability
- Backup-Staging

Die logische Trennung erfolgt über:

- separate Docker-Netzwerke
- getrennte Compose-Projekte
- eigenständige Volumes
- separate Benutzer und Secrets
- Ressourcenlimits

Das Offsite-Backup darf nicht ausschließlich auf demselben VPS liegen.

### 4.2 Erweiterungsmodell: Getrennte Produktionsrollen

Bei steigender Last oder höheren Verfügbarkeitsanforderungen erfolgt die Trennung mindestens in:

1. Edge/Application Host
2. Database Host
3. Observability/Backup Host

Die Aufteilung darf keine Änderung der fachlichen Service-Struktur erfordern.

### 4.3 Interne Hardware

Interne Server oder Workstations können künftig folgende Rollen übernehmen:

- Entwicklungs- und Testumgebung
- Backup-Repository
- Build- und Runner-System
- lokale KI- oder rechenintensive Verarbeitungsdienste

Produktionsabhängigkeiten zu interner Hardware müssen explizit dokumentiert werden, insbesondere bei eingeschränkter Internetanbindung oder Stromversorgung.

## 5. Umgebungsmodell

| Umgebung | Git-Quelle | Zweck | Daten |
|---|---|---|---|
| Development | `development` | Integration und technische Tests | synthetisch oder anonymisiert |
| Staging | `staging` | Release Candidate und produktionsnahe Prüfung | keine unkontrollierte Produktivkopie |
| Production | `main` | freigegebener Betriebsstand | produktiv |

Umgebungen müssen mindestens durch eigene Konfigurationen, Secrets, Netzwerke und Datenbestände getrennt sein.

Ein Environment beschreibt den Release- und Datenkontext, nicht die physische Serveranzahl. Mehrere Environments dürfen einen Host teilen; ein Environment darf zugleich Application- und Database-Rollen auf mehreren Hosts verwenden.

Aktuell ist ausschließlich `development` aktiv. `staging` und `production` bleiben vorbereitete Promotion-Ziele, bis reale Zielsysteme bereitgestellt werden.

## 6. Verzeichnislayout auf Hosts

Die implementierte Storage-Basis verwendet `/srv/merchfactory` für langlebige Plattformdaten:

```text
/srv/merchfactory/
├── persistent/
│   └── <service-name>/
│       └── <dataset>/
├── shared/
│   └── backups/
└── secrets/
    └── <service-name>/

/var/lib/merchfactory/
└── <service-name>/

/var/log/merchfactory/
└── <service-name>/

/var/tmp/merchfactory/
└── <service-name>/
```

Repository-/Release-Inhalte werden von diesen Laufzeitdaten getrennt bereitgestellt und sind nicht Teil des Persistenzpfads.

### Regeln

- Repository-Inhalte und Laufzeitdaten werden nicht vermischt.
- Backup- und migrationsrelevante Dateidaten liegen standardmäßig unter `/srv/merchfactory/persistent/<service-name>/...`.
- Gemeinsam genutzte langlebige Plattformdaten und lokales Backup-Staging liegen unter `/srv/merchfactory/shared`.
- Docker-interne Pfade unter `/var/lib/docker` werden nicht als administrativer Persistenz- oder Backupvertrag verwendet.
- Named Volumes sind nur mit dokumentierter Datenklasse und Restore-Strategie zulässig.
- Runtime-Secrets liegen getrennt unter `/srv/merchfactory/secrets/<service-name>/...` und werden gemäß `docs/51-secret-management.md` kontrolliert in Container injiziert.
- Temporäre Arbeitsdaten liegen unter `/var/tmp/merchfactory` oder in `tmpfs`.
- Das vollständige Volume- und Persistenzmodell ist in `docs/50-volume-persistence-model.md` definiert.

## 7. Datenklassifikation und Zuordnung

### 7.1 Konfiguration

- Compose-Dateien
- Traefik-Konfiguration
- Monitoring-Regeln
- Ansible-Rollen
- Skripte

**Quelle der Wahrheit:** Git-Repository

### 7.2 Persistente Betriebsdaten

- PostgreSQL-Daten
- Anwendungsuploads
- Produktionsdateien
- Queue- und Statusdaten

**Quelle der Wahrheit:** produktive Volumes und Datenbanken, abgesichert durch Backups

### 7.3 Secrets

- API-Keys
- Datenbankpasswörter
- SSH-Schlüssel
- Backup-Verschlüsselungsschlüssel
- OAuth- und Webhook-Secrets

**Quelle der Wahrheit:** autorisierte Deployment-/Recovery-Quelle gemäß `docs/51-secret-management.md`; die Hostdatei unter `/srv/merchfactory/secrets` ist nur die Runtime-Kopie und niemals Git.

### 7.4 Logs und Metriken

- Anwendungslogs
- Systemlogs
- Audit-Informationen
- Metriken und Alarmhistorie

**Quelle der Wahrheit:** Observability-Plattform mit definierter Aufbewahrung

## 8. Netzwerk- und Abhängigkeitsmodell

```text
Internet
   |
   v
Edge / Traefik
   |
   +--> Public Application Network
             |
             +--> Application Services
                       |
                       +--> Internal Data Network --> PostgreSQL
                       |
                       +--> Observability Network --> Metrics / Logs

Management Network --> Hosts / Docker / Internal Admin Endpoints
Backup Network ------> Databases / Volumes / Offsite Target
```

### Netzwerkregeln

- Nur der Edge-Dienst veröffentlicht Ports 80 und 443.
- Datenbanken befinden sich ausschließlich in internen Netzen.
- Management-Endpunkte werden nicht über öffentliche Standardrouten veröffentlicht.
- Monitoring erhält nur die für Telemetrie erforderlichen Zugriffe.
- Backups verwenden dedizierte Zugangsdaten und möglichst getrennte Ziele.

## 9. Skalierung

Skalierung erfolgt in dieser Reihenfolge:

1. Ressourcenlimits und Engpässe messen.
2. Einzelne Dienste vertikal skalieren.
3. Datenbank und Observability auf separate Hosts verschieben.
4. zustandslose Application Services horizontal skalieren.
5. externe oder hochverfügbare Datenbank-/Storage-Lösungen nur nach ADR einführen.

## 10. Wartung

Jede Serverrolle benötigt:

- dokumentierte Verantwortlichkeit
- unterstützte Betriebssystemversion
- Update- und Wartungsfenster
- Monitoring und Alarmierung
- Backup-Zuordnung
- Wiederherstellungsanweisung
- dokumentierte Abhängigkeiten

Änderungen an produktiven Rollen werden über Pull Requests, Staging-Prüfung und kontrollierte Releases durchgeführt.

## 11. Wiederherstellung

Der Wiederaufbau eines Hosts folgt grundsätzlich diesem Ablauf:

1. unterstütztes Betriebssystem installieren
2. Bootstrap ausführen
3. Repository und freigegebenen Release-Stand bereitstellen
4. Netzwerke, Verzeichnisse und Containerplattform erzeugen
5. Secrets kontrolliert wiederherstellen
6. Datenbanken und Volumes aus Backup restaurieren
7. Dienste starten
8. technische und fachliche Smoke Tests durchführen
9. Monitoring und Backup-Funktion validieren

Das Ziel ist, dass keine nicht dokumentierte manuelle Serverkonfiguration für einen Wiederaufbau erforderlich ist.

## 12. Offene Architekturentscheidungen

Folgende Themen werden in separaten ADRs oder späteren Arbeitspaketen konkretisiert:

- Auswahl eines optionalen dedizierten externen Vault-Produkts
- Offsite-Backup-Technologie
- Host-Betriebssysteme
- Trennung der Serverrollen nach Last und Risiko
- private Netzwerkverbindung zwischen VPS und interner Hardware
- Hochverfügbarkeit und Failover

## 13. Definition of Done

Das Servermodell ist vollständig, wenn:

- jede Rolle einen klaren Zweck und Verantwortungsbereich besitzt
- Persistenz, Konfiguration und Secrets eindeutig zugeordnet sind
- Netzwerkgrenzen und Abhängigkeiten nachvollziehbar sind
- Einzelhost- und Mehrhost-Betrieb unterstützt werden
- Migration und Disaster Recovery ohne grundlegende Architekturänderung möglich sind
