# Backup- und Disaster-Recovery-Konzept

## Zweck

Dieses Dokument definiert die verbindliche Backup-, Restore- und Disaster-Recovery-Strategie für die Merchfactory Infrastructure Platform. Ziel ist es, kritische Daten und Systeme nach Fehlbedienung, technischer Störung, Datenkorruption, Sicherheitsvorfall oder vollständigem Serverausfall reproduzierbar wiederherstellen zu können.

## Geltungsbereich

Die Vorgaben gelten für:

- produktive, interne und optionale Serverrollen,
- Datenbanken,
- persistente Container-Volumes,
- Anwendungsdaten und Uploads,
- Infrastruktur- und Deployment-Konfiguration,
- Secrets und Zugangsdaten,
- Monitoring-, Logging- und Auditdaten,
- Backup-Metadaten und Wiederherstellungsprotokolle.

## Grundprinzipien

1. Ein Backup gilt erst dann als belastbar, wenn seine Wiederherstellung erfolgreich getestet wurde.
2. Produktive Daten werden nicht ausschließlich auf demselben Host oder im selben Fehlerbereich gesichert.
3. Backups werden verschlüsselt, versioniert und gegen unbeabsichtigte Löschung geschützt.
4. Restore-Verfahren müssen dokumentiert, reproduzierbar und rollenbasiert ausführbar sein.
5. Konfiguration und Infrastrukturcode werden aus Git rekonstruiert; persistente Nutz- und Betriebsdaten werden aus Backups wiederhergestellt.
6. Secrets werden nicht im Repository gespeichert und benötigen einen getrennten Sicherungs- und Recovery-Prozess.
7. Backup- und Restore-Jobs sind Teil des Monitorings und erzeugen verwertbare Auditdaten.

## Datenklassen

### Klasse A – Geschäftskritische Daten

Beispiele:

- produktive Datenbanken,
- Auftrags-, Kunden-, Produktions- und Versanddaten,
- produktionsrelevante Designs und Uploads,
- persistente Anwendungsdaten ohne alternative Quelle.

Anforderungen:

- niedrigstes RPO,
- priorisierte Wiederherstellung,
- verschlüsselte Offsite-Sicherung,
- regelmäßige Restore-Tests,
- dokumentierte Eigentümerschaft.

### Klasse B – Betriebsrelevante Daten

Beispiele:

- Monitoring-Konfiguration,
- Dashboard-Definitionen,
- Alerting-Regeln,
- Betriebsprotokolle,
- interne Automatisierungsdaten.

Anforderungen:

- definierte Sicherungsintervalle,
- Restore innerhalb des betrieblichen RTO,
- Rekonstruktion aus Git und Backup kombinierbar.

### Klasse C – Rekonstruierbare Konfiguration

Beispiele:

- Docker-Compose-Dateien,
- Ansible-Rollen,
- CI/CD-Workflows,
- Reverse-Proxy-Konfiguration,
- Runbooks und Architektur-Dokumentation.

Anforderungen:

- führende Quelle ist Git,
- keine zusätzliche Vollsicherung zwingend erforderlich,
- notwendige externe Parameter und Artefaktversionen müssen dokumentiert sein.

### Klasse D – Secrets und Credentials

Beispiele:

- SSH-Schlüssel,
- API-Tokens,
- Datenbankpasswörter,
- TLS-Private-Keys,
- Recovery-Codes,
- Backup-Zugangsdaten.

Anforderungen:

- getrennte, verschlüsselte Sicherung,
- restriktiver Zugriff,
- dokumentierter Rotations- und Wiederherstellungsprozess,
- keine Ablage im Git-Repository oder unverschlüsselten Backup.

## RPO- und RTO-Ziele

| Daten-/Systemklasse | Ziel-RPO | Ziel-RTO | Priorität |
|---|---:|---:|---|
| Produktive Datenbanken | 15 Minuten | 4 Stunden | Kritisch |
| Produktions-Uploads und persistente Volumes | 1 Stunde | 8 Stunden | Kritisch |
| Reverse Proxy und zentrale Plattformdienste | 24 Stunden bzw. Git-Stand | 4 Stunden | Hoch |
| Monitoring und Alerting | 24 Stunden | 8 Stunden | Hoch |
| Interne Entwicklungs- und Stagingdaten | 24 Stunden | 24 Stunden | Mittel |
| Logs und Auditdaten | 24 Stunden | 24 Stunden | Mittel |
| Secrets und Credentials | nach Änderung | 4 Stunden | Kritisch |

Abweichungen benötigen eine dokumentierte Architektur- oder Risikoentscheidung.

## Backup-Matrix

| Objekt | Verfahren | Frequenz | Aufbewahrung | Offsite | Verschlüsselung | Restore-Test |
|---|---|---|---|---|---|---|
| PostgreSQL-Datenbanken | konsistenter Dump plus WAL/PITR, sofern verfügbar | Dump täglich, kontinuierliche Logs | 14 täglich, 8 wöchentlich, 12 monatlich | Ja | Ja | monatlich |
| Persistente Container-Volumes | Snapshot oder dateibasierte Sicherung im konsistenten Zustand | stündlich oder täglich je Klasse | 14 täglich, 8 wöchentlich, 12 monatlich | Ja | Ja | quartalsweise |
| Uploads/Produktionsdateien | inkrementelle dateibasierte Sicherung | stündlich | 30 Tage plus Monatsstände | Ja | Ja | monatlich stichprobenartig |
| Infrastrukturcode und Dokumentation | GitHub-Repository | bei jeder Änderung | Git-Historie | Plattformseitig | Transport/Plattform | halbjährlicher Exporttest |
| Deployment-Artefakte | Registry/Artefaktspeicher | je Release | mindestens aktuelle und vorherige freigegebene Versionen | Ja | Plattformabhängig | bei Release-Rollback |
| Monitoring-Konfiguration | Git plus Konfigurationsbackup | täglich | 30 Tage | Ja | Ja | quartalsweise |
| Secrets/Credentials | verschlüsselter Secret-Speicher/Offline-Tresor | nach Änderung | aktuelle und vorherige gültige Version nach Policy | Ja | Ja, getrennte Schlüssel | halbjährlich |
| Logs/Auditdaten | Export oder Remote-Log-Speicher | kontinuierlich/täglich | nach Security- und Datenschutzvorgabe | optional | Ja | jährlich |

## 3-2-1-Regel

Für kritische Daten gilt mindestens:

- drei Datenkopien,
- auf mindestens zwei unterschiedlichen Speichertechnologien oder Fehlerdomänen,
- davon mindestens eine Kopie offsite.

Die produktive Kopie zählt als eine der drei Kopien, jedoch nicht als Backup.

## Speicherorte und Fehlerdomänen

Backups müssen so verteilt werden, dass ein einzelnes Ereignis nicht alle Kopien zerstören kann.

Mindestens vorgesehen:

1. primärer Produktionshost,
2. separater Backup-Speicher oder Backup-Host,
3. externer Offsite-Speicher in einer anderen Verfügbarkeits- oder Anbieter-Domäne.

Für besonders kritische Monatsstände ist ein gegen Veränderung geschützter Speicher vorzusehen, beispielsweise Object Lock, WORM oder organisatorisch getrennte Offline-Sicherung.

## Verschlüsselung und Schlüsselmanagement

- Backups werden vor oder während der Übertragung verschlüsselt.
- Übertragungen erfolgen ausschließlich über gesicherte Protokolle.
- Verschlüsselungsschlüssel werden getrennt von den Backups aufbewahrt.
- Mindestens zwei berechtigte Personen oder dokumentierte Notfallverfahren müssen den Zugriff wiederherstellen können.
- Schlüsselrotation darf bestehende Backups nicht unbrauchbar machen.
- Der Verlust eines Backup-Zielsystems darf keinen Zugriff auf produktive Systeme ermöglichen.

## Backup-Konsistenz

### Datenbanken

Datenbank-Backups müssen transaktionskonsistent sein. Reine Dateisystemkopien laufender Datenbankverzeichnisse sind ohne dafür vorgesehenes Snapshot- oder Datenbankverfahren unzulässig.

### Container-Volumes

Vor der Sicherung zustandsbehafteter Volumes ist je Dienst festzulegen:

- ob ein Online-Backup unterstützt wird,
- ob Schreibzugriffe pausiert werden müssen,
- ob ein Anwendungsexport erforderlich ist,
- wie Konsistenz nach dem Backup geprüft wird.

### Abhängige Systeme

Bei logisch zusammengehörigen Datenbeständen muss die Wiederherstellungsreihenfolge dokumentiert werden, beispielsweise:

1. Datenbank,
2. persistente Dateien,
3. Anwendungskonfiguration,
4. Anwendungscontainer,
5. Reverse Proxy,
6. Monitoring und Alerting.

## Monitoring und Alarmierung

Jeder Backup-Job muss mindestens folgende Signale liefern:

- Start- und Endzeit,
- Erfolgs- oder Fehlerstatus,
- gesicherte Datenmenge,
- Ziel und Backup-ID,
- Alter des letzten erfolgreichen Backups,
- Prüfsummen- oder Integritätsstatus,
- Abweichung von erwarteter Laufzeit oder Datenmenge.

Alarmierung:

- Kritisch: kein erfolgreiches Backup innerhalb des RPO-Fensters.
- Hoch: Integritätsprüfung fehlgeschlagen oder Offsite-Kopie nicht verfügbar.
- Mittel: ungewöhnliche Laufzeit, Datenmenge oder Kapazitätsentwicklung.
- Niedrig: Aufbewahrungs- oder Bereinigungswarnung ohne unmittelbares Risiko.

## Restore-Runbook: Einzelne Datei oder Volume

1. Incident oder Restore-Anforderung erfassen.
2. Zielobjekt, Zeitpunkt und fachlichen Eigentümer bestätigen.
3. Geeigneten Wiederherstellungspunkt anhand Backup-Metadaten auswählen.
4. Wiederherstellung zunächst in isoliertes Ziel durchführen.
5. Integrität und Inhalt fachlich sowie technisch prüfen.
6. Produktiven Austausch oder Rückimport freigeben.
7. Anwendung und abhängige Dienste validieren.
8. Ergebnis, Dauer, Backup-ID und Abweichungen dokumentieren.

## Restore-Runbook: Datenbank

1. Schreibzugriffe auf das Zielsystem stoppen oder isolierte Restore-Umgebung bereitstellen.
2. Aktuellen Zustand zur Beweissicherung erfassen, sofern technisch vertretbar.
3. Backup und gegebenenfalls WAL-/PITR-Zielzeit auswählen.
4. Datenbankinstanz mit kompatibler Version bereitstellen.
5. Backup einspielen.
6. Datenbankintegrität und Migrationsstand prüfen.
7. Anwendung mit der wiederhergestellten Datenbank verbinden.
8. Smoke Tests und fachliche Stichproben durchführen.
9. Freigabe dokumentieren und Monitoring aktivieren.
10. Ursache und Verbesserungsmaßnahmen im Incident festhalten.

## Disaster Recovery: vollständiger Serverausfall

### Phase 1 – Lagebewertung

- Ausfall bestätigen und Fehlerdomäne bestimmen.
- Sicherheitsvorfall ausschließen oder Incident Response aktivieren.
- Wiederherstellungsleitung und Kommunikationskanal festlegen.
- RPO-/RTO-Ziele und letzte erfolgreiche Backups prüfen.

### Phase 2 – Ersatzinfrastruktur

- neuen Host oder Ersatzumgebung bereitstellen,
- Baseline-Hardening anwenden,
- Netzwerk, DNS und Firewall vorbereiten,
- Zugänge und Recovery-Credentials kontrolliert bereitstellen,
- Container-Runtime und benötigte Systempakete installieren.

### Phase 3 – Plattformrekonstruktion

- freigegebenen Stand aus dem Repository auschecken,
- Infrastruktur- und Deployment-Konfiguration anwenden,
- Netzwerke, Volumes und Service-Verzeichnisse erstellen,
- Monitoring-Agenten und Backup-Zugänge konfigurieren.

### Phase 4 – Datenwiederherstellung

- Datenbanken wiederherstellen,
- persistente Volumes und Uploads einspielen,
- Secrets aus dem sicheren Recovery-Speicher bereitstellen,
- Anwendungen in definierter Reihenfolge starten.

### Phase 5 – Validierung

- technische Healthchecks,
- Datenbank- und Dateiintegrität,
- Authentifizierung und Berechtigungen,
- Testauftrag oder repräsentativer Geschäftsprozess,
- Reverse Proxy, TLS und externe Erreichbarkeit,
- Monitoring, Logging und Backup-Jobs.

### Phase 6 – Umschaltung

- DNS, Load Balancer oder Routing kontrolliert umschalten,
- erhöhte Beobachtung aktivieren,
- Stakeholder informieren,
- alten Host isoliert lassen, bis Ursache und Datenlage geklärt sind.

### Phase 7 – Nachbereitung

- tatsächliches RPO und RTO dokumentieren,
- Lücken und manuelle Schritte erfassen,
- Runbooks und Automatisierung verbessern,
- notwendige Schlüssel- und Credential-Rotation durchführen,
- Post-Incident-Review abschließen.

## Restore-Tests

| Testart | Intervall | Umfang |
|---|---|---|
| automatisierte Backup-Integritätsprüfung | je Backup | Prüfsumme, Lesbarkeit, Metadaten |
| Datenbank-Testrestore | monatlich | vollständiger Restore in isolierte Umgebung |
| Datei-/Volume-Stichprobe | monatlich | zufällige oder risikobasierte Auswahl |
| vollständiger Service-Restore | quartalsweise | Anwendung plus Datenbank plus Volumes |
| vollständige Disaster-Recovery-Übung | mindestens jährlich | Neuaufbau auf Ersatzinfrastruktur |
| Secret-Recovery-Test | halbjährlich | Zugriff, Entschlüsselung und dokumentierter Ablauf |

Tests dürfen keine produktiven Daten unkontrolliert in unsichere Umgebungen übertragen. Testdaten sind zu anonymisieren oder die Testumgebung ist entsprechend der produktiven Schutzklasse abzusichern.

## Verantwortlichkeiten

### Platform Owner

- genehmigt RPO/RTO und Aufbewahrung,
- priorisiert Investitionen und Risikobehandlung,
- entscheidet über akzeptierte Abweichungen.

### Infrastructure Owner

- betreibt Backup-Jobs und Speicherziele,
- überwacht Kapazität und Fehler,
- pflegt Restore-Runbooks,
- führt technische Wiederherstellungen durch.

### Application Owner

- definiert kritische Daten und Konsistenzanforderungen,
- validiert fachliche Wiederherstellungen,
- dokumentiert anwendungsspezifische Export- und Restore-Verfahren.

### Security Owner

- verantwortet Verschlüsselungs- und Zugriffsvorgaben,
- begleitet Recovery nach Sicherheitsvorfällen,
- prüft Schlüssel- und Credential-Verfahren.

## Kapazitätsmanagement

Mindestens monatlich zu prüfen:

- Wachstum der Backup-Daten,
- freie Kapazität je Ziel,
- Dauer der Backup- und Restore-Prozesse,
- Kostenentwicklung,
- Einhaltung der Aufbewahrung,
- Lösch- und Bereinigungsfehler.

Ein Kapazitätsalarm muss ausgelöst werden, bevor das erwartete Wachstum die verfügbare Kapazität innerhalb von 30 Tagen überschreitet.

## Datenschutz und Löschung

Backups unterliegen denselben Schutzanforderungen wie die produktiven Daten.

- Zugriffe werden protokolliert.
- Aufbewahrungsfristen werden dokumentiert und technisch umgesetzt.
- Löschanforderungen werden mit gesetzlichen Aufbewahrungs- und Backupzyklen abgestimmt.
- Aus Restore-Backups zurückgeführte Daten müssen erneut den geltenden Lösch- und Sperrprozessen unterzogen werden.

## Abhängigkeiten

Dieses Konzept ist abgestimmt mit:

- `docs/03-server-layout.md`,
- `docs/04-security.md`,
- `docs/05-cicd.md`,
- `docs/06-deployment.md`,
- `docs/08-monitoring.md`,
- `docs/02-adr/ADR-0006-security-first.md`,
- `docs/02-adr/ADR-0007-backup-strategy.md`.

## Offene Entscheidungen

Folgende Punkte benötigen vor der produktiven Umsetzung eine konkrete technische Festlegung oder ein ergänzendes ADR:

- verwendetes Backup-Werkzeug,
- Offsite-Speicheranbieter,
- Object-Lock- oder WORM-Verfahren,
- Datenbank-PITR-Implementierung,
- Secret-Backup- und Recovery-Technologie,
- konkrete Aufbewahrungsfristen je Fachsystem,
- Verantwortliche und Eskalationskontakte.

## Definition of Done für die Umsetzung

Die operative Backup-Lösung ist erst produktionsreif, wenn:

- alle kritischen Datenklassen einer Backup-Policy zugeordnet sind,
- Monitoring und Alarmierung aktiv sind,
- Offsite-Kopien erfolgreich erzeugt werden,
- Verschlüsselungs- und Recovery-Schlüssel geprüft wurden,
- mindestens ein vollständiger Restore erfolgreich durchgeführt wurde,
- RPO und RTO im Test eingehalten oder Abweichungen dokumentiert wurden,
- Runbooks und Verantwortlichkeiten freigegeben sind.

## Referenzen

- Issue #9
- Epic #2
- ADR-0007 Backup Strategy
