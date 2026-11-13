# Security Baseline

## 1. Zweck und Geltungsbereich

Diese Baseline definiert verbindliche Mindestanforderungen für neue und bestehende Systeme der Merchfactory Infrastructure Platform. Sie gilt für Entwicklungs-, Staging- und Produktionsumgebungen sowie für alle administrativen Zugriffe, Deployments, Container-Workloads, Backups und Recovery-Prozesse.

Abweichungen sind nur mit dokumentierter Begründung, Risikobewertung, Verantwortlichem und Ablaufdatum zulässig.

## 2. Sicherheitsprinzipien

- Least Privilege
- Default Deny
- Defense in Depth
- Trennung von Entwicklungs-, Staging- und Produktionszugriffen
- Keine Secrets im Repository
- Reproduzierbare und überprüfbare Konfigurationen
- Nachvollziehbare administrative Änderungen
- Regelmäßige Updates, Reviews und Restore-Tests

## 3. Betriebssystem-Baseline

### 3.1 Unterstützte Systeme

- Nur aktiv unterstützte LTS- oder Enterprise-Versionen verwenden.
- End-of-Life-Systeme dürfen nicht neu bereitgestellt werden.
- Abweichungen benötigen eine ADR oder ein dokumentiertes Ausnahmeverfahren.

### 3.2 Basispakete und Dienste

- Nur erforderliche Pakete installieren.
- Unnötige Netzwerkdienste deaktivieren.
- Systemzeit über NTP synchronisieren.
- Hostname, Zeitzone und Locale über Infrastructure as Code setzen.
- Sicherheitsrelevante Kernel- und Netzwerkparameter versioniert verwalten.

### 3.3 Dateisystem und Rechte

- Systemkonfigurationen gehören `root` und sind nicht gruppen- oder weltbeschreibbar.
- Serviceverzeichnisse erhalten dedizierte Eigentümer und restriktive Rechte.
- Secret-Dateien höchstens `0600`, Secret-Verzeichnisse höchstens `0700`.
- Schreibrechte für Container und Dienste auf notwendige Pfade begrenzen.

## 4. Identitäten, Benutzer und Berechtigungen

### 4.1 Persönliche Konten

- Administrative Arbeit erfolgt über persönliche Benutzerkonten.
- Gemeinsame interaktive Administratorkonten sind nicht zulässig.
- Jede Person verwendet einen eigenen SSH-Schlüssel.
- Konten ausscheidender Personen werden unverzüglich gesperrt und entfernt.

### 4.2 Root und sudo

- Direkte Root-Anmeldung per SSH ist deaktiviert.
- Privilegierte Befehle erfolgen über `sudo`.
- Sudo-Rechte werden gruppenbasiert und so eng wie möglich vergeben.
- Passwortloses sudo ist nur für klar begrenzte Automatisierungsbefehle zulässig.

### 4.3 Servicekonten

- Jeder Dienst erhält ein eigenes, nicht interaktives Konto, sofern technisch sinnvoll.
- Servicekonten besitzen keine Login-Shell und keine unnötigen Gruppenmitgliedschaften.
- Tokens und Schlüssel sind einem konkreten Dienst und Zweck zugeordnet.

### 4.4 Review-Intervall

- Produktionszugriffe mindestens vierteljährlich prüfen.
- GitHub-, Server-, Registry-, Backup- und Monitoring-Zugriffe gemeinsam betrachten.
- Veraltete, ungenutzte oder nicht zuordenbare Berechtigungen entfernen.

## 5. SSH-Baseline

- Nur schlüsselbasierte Authentifizierung.
- Passwortauthentifizierung deaktivieren.
- Root-Login deaktivieren.
- Moderne Schlüsseltypen verwenden, bevorzugt Ed25519.
- Administrative Zugriffe nach Möglichkeit auf VPN oder definierte Quellnetze begrenzen.
- Fehlversuche über Fail2ban oder eine gleichwertige Kontrolle behandeln.
- SSH-Konfiguration automatisiert prüfen und versioniert bereitstellen.
- Hostschlüssel bei Neuaufbau kontrolliert erzeugen und bekannte Fingerprints dokumentieren.

Empfohlene Mindestwerte:

```text
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
X11Forwarding no
AllowTcpForwarding no
MaxAuthTries 3
LoginGraceTime 30
```

Abweichungen, etwa notwendiges Port-Forwarding, müssen pro Host dokumentiert werden.

## 6. Firewall und Netzwerksegmentierung

### 6.1 Host-Firewall

- Eingehender Verkehr standardmäßig blockiert.
- Nur dokumentierte Ports und Quellbereiche freigeben.
- Ausgehenden Verkehr für besonders sensible Komponenten soweit praktikabel begrenzen.
- Firewallregeln über Infrastructure as Code verwalten.

### 6.2 Externe Dienste

- Öffentlich erreichbar sind grundsätzlich nur Reverse Proxy und explizit freigegebene Endpunkte.
- Datenbanken, Monitoring-Backends, Admin-UIs und interne APIs werden nicht direkt veröffentlicht.
- TLS ist für externe HTTP-Verbindungen verpflichtend.
- Admin-Oberflächen benötigen zusätzliche Zugriffsbeschränkungen wie VPN, IP-Allowlist oder starke Authentifizierung.

### 6.3 Container-Netzwerke

- Edge-, Application-, Data- und Observability-Netze logisch trennen.
- Dienste werden nur mit den Netzwerken verbunden, die sie tatsächlich benötigen.
- Datenbanken dürfen nicht im öffentlichen Proxy-Netz liegen.
- Containerports nur veröffentlichen, wenn Hostzugriff erforderlich ist.

## 7. Secret- und Credential-Management

### 7.1 Grundregeln

- Keine Passwörter, API-Schlüssel, privaten Schlüssel oder produktiven Tokens im Git-Repository.
- `.env.example` enthält nur Namen und ungefährliche Beispielwerte.
- Produktive Secrets werden außerhalb des Repositories gespeichert und beim Deployment dateibasiert injiziert.
- Runtime-Secrets liegen unter `/srv/merchfactory/secrets/<service>/...`.
- Container erhalten nur explizit freigegebene Secrets unter `/run/secrets/<name>`.
- Secret-Werte dürfen nicht in Images, normalen Environment-Variablen, Build-Logs, Shell-History, Monitoring-Labels oder Artefakten erscheinen.

### 7.2 Quellen und Runtime-Speicherung

Zulässige Quellen:

- GitHub Environment Secrets für kontrollierte Deployments,
- ein autorisierter verschlüsselter Recovery-/Credential-Tresor,
- kontrollierte manuelle Eingabe für Bootstrap oder Recovery.

GitHub Environment Secrets sind keine alleinige Recovery-Quelle, weil Werte nach dem Speichern nicht wieder ausgelesen werden können.

Die Runtime-Kopie wird als geschützte Hostdatei unter `/srv/merchfactory/secrets` abgelegt. Standardrechte:

- Secret-Root und Service-Verzeichnis: `0700`,
- Secret-Datei: bevorzugt `0400`,
- `0440` nur bei dokumentiertem Gruppenlesezugriff.

### 7.3 Injection und Zugriff

- Docker Compose Secrets werden dateibasiert verwendet.
- Anwendungen lesen Werte direkt aus `/run/secrets` oder über eine unterstützte `*_FILE`-Konvention.
- File-basierte Compose-Secrets übernehmen die Host-Dateieigenschaften; Ownership und Rechte werden deshalb vor dem Containerstart auf dem Host gesetzt.
- Normale Repository-Leserechte vermitteln keinen Zugriff auf Produktiv-Secrets.
- CI/CD erhält nur die Secrets, die der konkrete Deployment-Job benötigt.
- Unvertrauenswürdiger PR-Code erhält keine produktiven Secrets.

### 7.4 Rotation und Notfallzugriff

- Verantwortlicher, Zweck und Rotationsanforderung werden als Metadaten versioniert; der Wert selbst nie.
- Secrets bei Verdacht auf Offenlegung sofort widerrufen oder rotieren.
- Host-Runtime-Dateien werden atomar ersetzt und betroffene Dienste danach kontrolliert neu geladen oder erstellt.
- Alte Credentials werden erst nach erfolgreicher Validierung des neuen Werts widerrufen, sofern der Anbieter eine Überlappung unterstützt.
- Kritische Secrets benötigen einen getrennten Recovery-Pfad.
- Notfallzugänge werden mindestens halbjährlich getestet und nach Verwendung bewertet bzw. rotiert.

### 7.5 Erkennung und Incident-Verhalten

- `scripts/check-secrets.py` prüft aktuellen Tree und erreichbare Git-Historie.
- Verdächtige Funde blockieren den Merge.
- Scanner-Ausgaben enthalten Fundort und Regelname, niemals den erkannten Wert.
- Bereits veröffentlichte Secrets gelten als kompromittiert und werden zuerst rotiert.
- Das spätere Entfernen aus Git-Historie oder Artefakten ersetzt die Rotation nicht.

Das vollständige Betriebsmodell steht in `docs/51-secret-management.md`.

## 8. Container- und Image-Sicherheit

- Eigene Images werden ausschließlich unter `ghcr.io/merchfactory/...` veröffentlicht.
- Drittanbieter-Images sind Default-Deny und benötigen einen Eintrag in `configuration/container-image-policy.json`.
- Registry und Repository werden in Compose-Dateien vollständig ausgeschrieben.
- Alle Images werden mit SHA-256-Digest gepinnt; rein tagbasierte Deployments und `:latest` sind verboten.
- First-Party-Images benötigen eine verifizierbare GitHub Artifact Attestation für die Build-Provenance.
- Drittanbieter-Provenance oder Signaturen werden verifiziert, wenn der Upstream belastbare Nachweise veröffentlicht; andernfalls gelten Digest, Allowlist, Scan und Review als kompensierende Kontrollen.
- Trivy berichtet HIGH- und CRITICAL-Funde.
- Fixbare CRITICAL-Schwachstellen blockieren den normalen Releasepfad.
- Security-Ausnahmen benötigen Issue, Risikobewertung, Owner und Ablaufdatum.
- Container möglichst ohne Root-Rechte ausführen.
- Linux Capabilities reduzieren und `no-new-privileges` setzen.
- Schreibgeschützte Root-Dateisysteme verwenden, sofern der Dienst dies unterstützt.
- Ressourcenlimits und Healthchecks definieren.
- Keine Docker-Socket-Mounts ohne explizite Sicherheitsentscheidung.
- Nicht mehr benötigte Images werden nur nach Referenz- und Rollback-Prüfung entfernt.

Das vollständige Registry-, Provenance-, Scan- und Retention-Modell steht in `docs/52-container-registry-security.md`.

## 9. Patch-, Update- und Vulnerability-Prozess

### 9.1 Klassifizierung

- Kritisch: aktive Ausnutzung oder hohes Risiko für öffentlich erreichbare Systeme.
- Hoch: relevante Schwachstelle mit realistischer Angriffsfläche.
- Regulär: sonstige Sicherheits- und Wartungsupdates.

### 9.2 Zielzeiten

- Kritisch: Bewertung sofort, Umsetzung möglichst innerhalb 24 Stunden.
- Hoch: Bewertung innerhalb 3 Arbeitstagen, Umsetzung möglichst innerhalb 7 Tagen.
- Regulär: im geplanten Wartungsfenster.

### 9.3 Vorgehen

1. Betroffene Hosts, Images und Dienste bestimmen.
2. Risiko und Betriebswirkung bewerten.
3. Änderung in Entwicklung oder Staging testen.
4. Backup- und Rollbackfähigkeit prüfen.
5. Deployment durchführen.
6. Funktion und Monitoring validieren.
7. Ergebnis dokumentieren.

Automatisierte Abhängigkeitsupdates dürfen ohne Review nicht produktiv ausgerollt werden.

## 10. Logging, Audit und Nachvollziehbarkeit

Mindestens erfassen:

- SSH-Anmeldungen und Fehlversuche
- sudo-Nutzung
- Firewall- und Fail2ban-Ereignisse
- Deployment- und Konfigurationsänderungen
- Containerstarts, Neustarts und Healthcheck-Fehler
- Backup- und Restore-Ergebnisse
- Authentifizierungsfehler geschäftskritischer Dienste

Anforderungen:

- Systemzeiten synchronisieren.
- Logs vor unberechtigter Änderung schützen.
- Secrets und unnötige personenbezogene Daten nicht protokollieren.
- Aufbewahrungsfristen pro Logklasse definieren.
- Kritische Ereignisse an zentrale Überwachung und Alarmierung weiterleiten.

## 11. GitHub- und Deployment-Sicherheit

- `development`, `staging` und `main` werden durch Branch Protection geschützt.
- Änderungen erfolgen über Pull Requests.
- `main` erhält nur Änderungen über den vereinbarten Promotion-Flow.
- Staging- und Produktionsdeployments verwenden getrennte GitHub Environments.
- Produktionsdeployments benötigen manuelle Freigabe.
- Workflows erhalten minimale Token-Berechtigungen.
- Drittanbieter-Actions werden auf Commit-SHAs oder kontrollierte Versionen gepinnt.
- Unvertrauenswürdiger PR-Code erhält keinen Zugriff auf produktive Secrets.

## 12. Backups und Recovery

- Backups verschlüsseln, wenn sie Secrets, Kundendaten oder produktive Daten enthalten.
- Backup-Zugänge von normalen Servicezugängen trennen.
- Lösch- oder Ransomware-Szenarien durch Offsite- oder immutable Kopien berücksichtigen.
- Restore-Tests sind verpflichtend; ein erfolgreicher Backup-Job allein gilt nicht als Nachweis.
- Wiederhergestellte Systeme durchlaufen vor Freigabe Sicherheits- und Funktionschecks.
- Recovery-Zugänge und Schlüssel müssen auch bei vollständigem Serververlust verfügbar sein.

## 13. Daten und Datenschutz

- Nur erforderliche Daten verarbeiten und speichern.
- Produktionsdaten nicht ohne dokumentierten Zweck in Entwicklungsumgebungen kopieren.
- Für Tests anonymisierte oder synthetische Daten bevorzugen.
- Datenübertragung verschlüsseln.
- Aufbewahrung und Löschung pro Datenklasse festlegen.
- Zugriff auf Kundendaten protokollieren, soweit technisch und rechtlich erforderlich.

## 14. Sicherheitsprüfungen

### Kontinuierlich

- Monitoring und Alarmierung
- Fail2ban- und Firewall-Status
- Backup-Ergebnisse
- Zertifikatslaufzeiten

### Monatlich

- ausstehende Sicherheitsupdates
- Image- und Abhängigkeitsscans
- fehlgeschlagene Backup- oder Monitoring-Jobs
- öffentlich erreichbare Ports und Dienste

### Vierteljährlich

- Benutzer- und Berechtigungsreview
- SSH-Schlüssel und Service-Tokens
- Firewallregeln und Netzwerkfreigaben
- Secret-Inventar und Rotationsstatus
- Restore-Test eines repräsentativen Dienstes

### Jährlich

- vollständiger Security Review
- Disaster-Recovery-Übung
- Überprüfung dieser Baseline und der zugehörigen ADRs

## 15. Ausnahmeverfahren

Eine Sicherheitsabweichung enthält mindestens:

- betroffene Systeme und Umgebung
- verletzte Anforderung
- technische oder betriebliche Begründung
- Risikobewertung
- kompensierende Maßnahmen
- verantwortliche Person
- Ablauf- oder Review-Datum
- Referenz auf Issue oder ADR

Unbefristete, nicht verantwortete Ausnahmen sind nicht zulässig.

## 16. Incident-Grundprozess

1. Ereignis erkennen und Schweregrad bestimmen.
2. Betroffene Zugänge, Hosts oder Dienste begrenzen.
3. Beweise und relevante Logs sichern.
4. Kompromittierte Secrets rotieren.
5. Ursache beheben und Systeme validieren.
6. Dienste kontrolliert wieder freigeben.
7. Auswirkungen und Maßnahmen dokumentieren.
8. Folgeaufgaben und Präventionsmaßnahmen anlegen.

Bei möglicher Offenlegung von Kunden- oder personenbezogenen Daten sind zusätzlich die internen Datenschutz- und Meldeprozesse anzuwenden.

## 17. Verantwortlichkeiten

- Platform Owner: Freigabe der Baseline und Priorisierung kritischer Maßnahmen.
- Infrastructure Maintainer: technische Umsetzung, Updates und Nachweise.
- Service Owner: sichere Konfiguration und Datenklassifikation des Dienstes.
- Reviewer: Prüfung sicherheitsrelevanter Pull Requests und Ausnahmen.

In der aktuellen kleinen Teamstruktur können Rollen durch dieselbe Person wahrgenommen werden; die Rollen und Entscheidungen bleiben trotzdem nachvollziehbar zu dokumentieren.

## 18. Definition of Done für neue Server

Ein Server gilt erst als freigabefähig, wenn:

- unterstütztes Betriebssystem und Updates installiert sind,
- persönliche SSH-Zugänge und restriktive sudo-Rechte bestehen,
- Root- und Passwort-Login deaktiviert sind,
- Firewall und Fail2ban aktiv und geprüft sind,
- nur erforderliche Ports erreichbar sind,
- Monitoring, Logging und Zeitsynchronisation funktionieren,
- Backup und Restore-Pfad dokumentiert sind,
- Secrets außerhalb des Repositories liegen,
- Inventar und Verantwortlichkeit dokumentiert sind,
- offene Abweichungen genehmigt und befristet sind.

## 19. Referenzen

- `docs/01-architecture.md`
- `docs/03-server-layout.md`
- `docs/02-adr/ADR-0006-security-first.md`
- `docs/02-adr/ADR-0007-backup-strategy.md`
- Issue #6
- Epic #2
