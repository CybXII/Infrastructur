# Volume- und Persistenzmodell

## Zweck

Dieses Dokument definiert das verbindliche Persistenzmodell der Merchfactory Container Platform ab v0.5. Es konkretisiert, welche Daten dauerhaft gespeichert werden, welche Speicherform verwendet wird und wie Backup, Migration und Restore berücksichtigt werden.

Das Modell setzt Issue #72 um und baut auf dem Host-Storage aus `docs/42-storage-directory-preparation.md`, der Backup-Strategie aus `docs/07-disaster-recovery.md` und den Compose-Standards aus `docs/48-docker-compose-standards.md` auf.

## Verbindliche Host-Basis

Die implementierte Plattformbasis ist:

```text
/srv/merchfactory
```

Sie ersetzt ältere Planungsstände mit `/opt/merchfactory`.

Verbindliche langlebige Pfade:

```text
/srv/merchfactory/
├── persistent/
│   └── <service>/
│       └── <dataset>/
└── shared/
    └── <purpose>/

/var/lib/merchfactory/
└── <service>/

/var/log/merchfactory/
└── <service>/

/var/tmp/merchfactory/
└── <service>/
```

Container-Layer und `/var/lib/docker/volumes` sind keine administrativ verwalteten Datenpfade.

## Datenklassen

Die bestehenden Disaster-Recovery-Klassen bleiben führend.

### Klasse A – Geschäftskritische Daten

Beispiele:

- PostgreSQL-Datenbanken,
- Odoo-Filestore,
- produktionsrelevante Uploads und Designs,
- persistente Anwendungsdaten ohne alternative Quelle.

Regeln:

- Backup verpflichtend,
- niedriges RPO gemäß Disaster-Recovery-Konzept,
- Migration und Restore müssen servicebezogen dokumentiert sein,
- bevorzugt expliziter Bind Mount unter `/srv/merchfactory/persistent/<service>/...` oder ein klar benanntes Volume mit anwendungsspezifischem Backup-Verfahren.

### Klasse B – Betriebsrelevante Daten

Beispiele:

- interne Automatisierungszustände,
- Monitoring-Zustände,
- nicht geschäftskritische persistente Service-Daten.

Regeln:

- Backup-Relevanz wird explizit festgelegt,
- Restore innerhalb des betrieblichen RTO,
- Speicherort wie Klasse A, wenn der Zustand hostübergreifend erhalten bleiben muss.

### Klasse C – Rekonstruierbare Konfiguration

Beispiele:

- Compose-Dateien,
- Traefik-Konfiguration,
- Skripte,
- deklarative Service-Konfiguration aus Git.

Regeln:

- Quelle der Wahrheit ist Git bzw. das freigegebene Deployment-Artefakt,
- Konfigurations-Bind-Mounts werden read-only eingebunden,
- kein zusätzliches Datenbackup erforderlich, sofern keine externen, nicht reproduzierbaren Werte enthalten sind.

### Klasse D – Secrets und Credential-Material

Beispiele:

- TLS-Private-Keys,
- ACME-Speicher,
- Datenbankpasswörter,
- API-Tokens.

Regeln:

- getrennte Behandlung gemäß `docs/07-disaster-recovery.md` und `docs/51-secret-management.md`,
- keine Ablage des Werts im Repository,
- normale Runtime-Kopien liegen unter `/srv/merchfactory/secrets/<service>/...`,
- Secret-Dateien verwenden restriktive Rechte und werden nicht in normale Volume-Backups aufgenommen,
- Recovery erfolgt aus einer getrennten autorisierten Secret-/Credential-Quelle,
- Services erhalten Secrets kontrolliert über `/run/secrets`.

Der Traefik-ACME-Speicher ist ein technischer Sonderfall innerhalb von Klasse D und behält sein bestehendes geschütztes Backup-Verfahren.

### Klasse T – Temporäre und rekonstruierbare Laufzeitdaten

Beispiele:

- Render-/Transcoding-Zwischendaten,
- entbehrliche Caches,
- temporäre Exporte,
- Prozess-Scratchspace.

Regeln:

- kein Backup,
- bevorzugt Compose-`tmpfs`,
- alternativ `/var/tmp/merchfactory/<service>`,
- darf bei Neustart, Cleanup oder Hostmigration verloren gehen.

## Speicherformen

### Bind Mount

Bind Mounts sind der Standard für dateibasierte, backup- oder migrationsrelevante Daten.

Beispiel:

```yaml
volumes:
  - type: bind
    source: ${SERVICE_DATA_DIR:-/srv/merchfactory/persistent/example-service/data}
    target: /var/lib/example-service
```

Vorteile:

- eindeutiger Hostpfad,
- unabhängig von Docker-internen Volume-Pfaden,
- einfach in hostbasierte Backup- und Migrationswerkzeuge integrierbar,
- Besitzrechte und Kapazität sind nachvollziehbar.

Beschreibbare Bind Mounts dürfen im Standardmodell nur aus explizit verwalteten Plattformpfaden stammen.

### Named Volume

Named Volumes sind zulässig, wenn der Dienst seinen Zustand bewusst Docker-gekapselt verwaltet und ein dokumentiertes Backup-/Restore-Verfahren existiert.

Beispiel:

```yaml
volumes:
  example-database-data:
    labels:
      com.merchfactory.persistence.class: A
      com.merchfactory.backup.required: "true"
      com.merchfactory.backup.method: application-native
```

Regeln:

- keine anonymen Volumes,
- sprechender Compose-Name,
- Datenklasse und Backup-Relevanz dokumentieren,
- niemals produktive Daten durch direkten Zugriff auf `/var/lib/docker/volumes` sichern oder migrieren,
- Datenbanken werden mit dem dafür vorgesehenen Datenbankverfahren gesichert; eine Live-Dateikopie des Datenverzeichnisses ist kein gültiges Datenbankbackup.

### Read-only Konfigurations-Mount

Rekonstruierbare Konfiguration wird read-only eingebunden:

```yaml
volumes:
  - ./configuration/service.yaml:/etc/example/service.yaml:ro
```

Der Repository- oder Release-Stand bleibt die Quelle der Wahrheit.

### tmpfs

Temporäre Schreibpfade sollen nach Möglichkeit als `tmpfs` bereitgestellt werden:

```yaml
tmpfs:
  - /tmp
```

## Besitzrechte

Für jeden persistenten Datensatz müssen effektiver Besitzer und Gruppe bekannt sein.

### Bind Mounts

- Host-UID/GID müssen zum effektiven Container-Benutzer passen.
- Service-README oder Deployment-Dokumentation nennt die erwartete UID/GID.
- Verzeichnisse werden vor dem Containerstart angelegt.
- Weltweit beschreibbare Rechte sind nicht zulässig.
- Als Ausgangspunkt gilt maximal `0750` für Verzeichnisse; strengere Rechte sind zu bevorzugen, wenn der Dienst sie unterstützt.
- Rekursives `chown` auf bestehende Produktivdaten ist keine generische Deployment-Aktion und benötigt eine bewusste Migration.

Das Werkzeug `platform/storage/scripts/prepare-persistent-directory.sh` legt einen freigegebenen persistenten Pfad idempotent mit explizitem Owner, Group und Mode an.

### Named Volumes

Bei Named Volumes wird der Besitz innerhalb des Volumes durch Image bzw. Service-Initialisierung festgelegt. Die erwartete effektive UID/GID muss trotzdem dokumentiert werden, damit ein Restore nicht mit inkompatiblen Besitzrechten endet.

## Backup-Relevanz

Jeder persistente Datensatz benötigt eine Zuordnung in der servicebezogenen Backup-Policy.

Mindestens zu dokumentieren sind:

- eindeutige ID,
- Datenklasse,
- Speicherart,
- Quelle und Container-Ziel,
- Backup erforderlich: ja/nein,
- Backup-Verfahren,
- Konsistenzanforderung,
- Restore-Verfahren,
- Restore-Test-Frequenz.

Die Beispielstruktur unter `examples/services/example-service/backup/policy.yaml.example` zeigt das Format.

## Datenbank-Sonderfall

Datenbanken sind Klasse A.

Für PostgreSQL und vergleichbare Systeme gilt:

- das Datenverzeichnis ist persistent,
- Backups erfolgen transaktionskonsistent über Datenbankmechanismen,
- reine Live-Dateikopien des Datenverzeichnisses sind unzulässig,
- Version und Erweiterungen müssen beim Restore kompatibel sein,
- für das spätere Odoo-Setup gehören Datenbank und Filestore gemeinsam in denselben fachlichen Restore-Punkt.

PITR/WAL und konkrete PostgreSQL-Backup-Automatisierung bleiben Bestandteil der operativen Backup-Umsetzung.

## Odoo-Ausblick

Für Odoo ist damit bereits die Zieltrennung definiert:

- PostgreSQL: Klasse A, persistenter Datenbankzustand, anwendungsspezifisches/logisches Backup,
- Odoo-Filestore: Klasse A, expliziter Bind Mount unter `/srv/merchfactory/persistent/odoo/...`,
- Odoo-Konfiguration: Klasse C, versioniert/read-only soweit möglich,
- Secrets: Klasse D, Runtime-Injection gemäß `docs/51-secret-management.md`,
- temporäre Sessions/Caches nur dann persistent, wenn Odoo bzw. das Betriebsmodell dies fachlich benötigt.

Ein gültiger Odoo-Restore muss Datenbank und zugehörigen Filestore konsistent zusammenführen.

## Migration eines Bind Mounts

Empfohlener Ablauf:

1. Zielhost und kompatible Service-Version bereitstellen.
2. Zielpfad mit korrekten UID/GID und Rechten vorbereiten.
3. Dienst abhängig von seiner Konsistenzanforderung quiescen oder stoppen.
4. Daten mit einem Verfahren übertragen, das Besitzrechte und Metadaten erhält.
5. Integrität bzw. Prüfsummen validieren.
6. Zielpfad in der neuen Compose-Konfiguration einbinden.
7. Dienst starten.
8. technischen und fachlichen Smoke Test durchführen.
9. Quellsystem erst nach erfolgreicher Abnahme außer Betrieb nehmen.

## Migration eines Named Volumes

Named Volumes werden nicht durch Kopieren des Docker-internen Hostpfads migriert.

Zulässig sind:

- anwendungsspezifischer Export/Import,
- kontrollierter Volume-Export bei gestopptem bzw. konsistentem Service,
- Storage-Snapshot, wenn die eingesetzte Storage-Technologie Konsistenz garantiert.

Das Restore-Verfahren muss vor produktiver Nutzung dokumentiert und getestet werden.

## Restore-Reihenfolge

Als allgemeine Reihenfolge gilt:

1. Host und Containerplattform wiederherstellen,
2. Netzwerke und persistente Zielpfade erzeugen,
3. Secrets kontrolliert bereitstellen,
4. Datenbank wiederherstellen,
5. dateibasierte persistente Daten wiederherstellen,
6. Konfiguration aus Git/Release bereitstellen,
7. Anwendung starten,
8. Reverse Proxy aktivieren,
9. Smoke Tests, Monitoring und Backup prüfen.

Serviceabhängige Abweichungen werden im jeweiligen Runbook dokumentiert.

## Validierung

Die Referenzimplementierung prüft automatisiert:

- keine anonymen Volumes,
- keine direkten Bind Mounts in Docker-interne Volume-Pfade,
- beschreibbare Bind Mounts nur aus freigegebenen Plattformpfaden,
- Named Volumes besitzen eine explizite Persistenzklasse,
- backup-pflichtige Named Volumes besitzen ein dokumentiertes Backup-Verfahren,
- die servicebezogene Backup-Policy ist vorhanden.

## Abgrenzung

Nicht Bestandteil dieses Tasks sind:

- konkreter Offsite-Backup-Anbieter,
- vollständige Backup-Orchestrierung,
- PostgreSQL-WAL/PITR-Implementierung,
- Registry-Strategie (#74),
- vollständiges Service-Template (#75),
- Logging-Retention (#78),
- Update/Rollback (#79).
