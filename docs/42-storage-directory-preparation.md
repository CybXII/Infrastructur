# Storage- und Verzeichnisvorbereitung

## Zweck

Die Rolle `storage_preparation` stellt ein reproduzierbares Verzeichnis- und Mountpoint-Layout für die Merchfactory-Plattform bereit. Sie trennt langlebige Plattformdaten bewusst von temporären Arbeitsdaten und schafft damit die Grundlage für spätere Docker-, Applikations-, Backup- und Multi-Server-Rollen.

Die Rolle formatiert **keine Datenträger**. Destruktive Storage-Operationen wie Partitionierung, Dateisystemerstellung oder LVM-Provisionierung bleiben außerhalb von v0.4 und müssen separat geplant werden.

## Standardlayout

| Pfad | Klasse | Standardrechte | Zweck |
|---|---|---:|---|
| `/srv/merchfactory` | Plattform | `0755` | gemeinsamer Plattformstamm |
| `/srv/merchfactory/persistent` | persistent | `0750` | langlebige Applikations-/Servicedaten |
| `/srv/merchfactory/shared` | persistent | `0750` | später gemeinsam nutzbare Plattformdaten |
| `/srv/merchfactory/secrets` | secret | `0700` | geschützte Runtime-Kopien von Service-Secrets |
| `/var/lib/merchfactory` | persistent | `0750` | lokaler persistenter Laufzeitzustand; Gruppe `merchfactory-runtime` |
| `/var/log/merchfactory` | persistent | `0750` | plattformspezifische Logs |
| `/var/tmp/merchfactory` | temporär | `1770` | temporäre Arbeitsdaten |

`/var/tmp/merchfactory` ist bewusst vom persistenten Datenbaum getrennt. Das Sticky-Bit verhindert, dass Benutzer in einem gemeinsam nutzbaren temporären Verzeichnis fremde Dateien löschen können, sofern später mehrere berechtigte Benutzer/Gruppen verwendet werden.

## Besitzer und Gruppen

Die Standardverzeichnisse gehören grundsätzlich `root:root`. Eine bewusste Ausnahme ist `/var/lib/merchfactory`: Der Runtime-Root bleibt `root`-owned und `0750`, verwendet aber die dedizierte Systemgruppe `merchfactory-runtime`. Nur explizit berechtigte Host-Agenten werden Mitglied dieser Gruppe und können dadurch bekannte Unterpfade traversieren; der Runtime-Root wird nicht global geöffnet.

Alle Definitionen sind deklarativ in `storage_directories` hinterlegt und können über Inventory-/Gruppenvariablen angepasst werden, sobald konkrete Service-Accounts für Docker oder einzelne Plattformdienste festgelegt sind.

Beispiel:

```yaml
storage_directories:
  - path: /srv/merchfactory/persistent/app
    owner: merchapp
    group: merchapp
    mode: '0750'
    class: persistent
```

Die Rolle läuft nach `user_management`, damit deklarierte Benutzer und Gruppen bereits existieren können, bevor ihnen Storage-Pfade zugewiesen werden.

## Optionale Mountpoints

Zusätzliche bereits vorhandene Dateisysteme können über `storage_mounts` in `/etc/fstab` und im laufenden System verwaltet werden:

```yaml
storage_mounts:
  - path: /srv/merchfactory/persistent
    src: /dev/disk/by-id/scsi-example
    fstype: xfs
    opts: defaults,noatime
    state: mounted
```

Ohne Einträge in `storage_mounts` wird kein bestehender Mount verändert.

Für persistente Datenträger sollen nach Möglichkeit stabile Bezeichner wie `/dev/disk/by-id/...`, UUIDs oder providerseitig garantierte Devices verwendet werden. Flüchtige Gerätenamen wie `/dev/sdb` können sich zwischen Bootvorgängen ändern und sollten nicht ohne Bewertung als langfristige Identität verwendet werden.

## Sicherheitsgrenzen

Die Rolle führt absichtlich keine dieser Aktionen automatisch aus:

- Partitionstabellen ändern,
- Dateisysteme formatieren,
- bestehende Dateisysteme verkleinern oder migrieren,
- LVM-/RAID-Strukturen erzeugen,
- Daten zwischen Mountpoints verschieben,
- bestehende Daten löschen.

Dadurch kann ein Inventory-Fehler nicht unmittelbar einen Datenträger neu formatieren. Storage-Provisionierung ist später als eigener Infrastruktur-Schritt zu behandeln.

## Persistente und temporäre Daten

Die Klassifikation `platform`, `persistent`, `secret` und `temporary` ist Bestandteil jeder Standard-Verzeichnisdefinition. Secret-Pfade werden zusätzlich von persistenten und temporären Datenbäumen getrennt gehalten. Der Bootstrap prüft zusätzlich, dass `storage_persistent_root` und `storage_temporary_root` nicht identisch sind und nicht ineinander verschachtelt werden.

Spätere Rollen sollen diese Trennung beibehalten:

- Datenbanken, Uploads, Anwendungszustände und notwendige Backups → persistente Pfade,
- Runtime-Secrets → `/srv/merchfactory/secrets`, getrennte Klasse D und kein normales Volume-Backup,
- Build-Artefakte, Transcoding-/Render-Zwischendaten, entbehrliche Caches → temporäre Pfade,
- Container selbst → nicht als Persistenzmechanismus verwenden.

## Validierung

Vor Änderungen werden Verzeichnis- und Mountdefinitionen geprüft. Nach der Anlage kontrolliert die Rolle für jedes Plattformverzeichnis:

- Existenz,
- Verzeichnistyp,
- Besitzer,
- Gruppe,
- Dateimodus.

Abweichungen führen zu einem fehlgeschlagenen Bootstrap, anstatt mit einem inkonsistenten Rechte- oder Storage-Zustand weiterzulaufen.

## Idempotenz

Verzeichnisse und Mounts werden über deklarative Ansible-Module verwaltet. Ein erneuter Lauf mit identischen Variablen soll keine fachlich unnötigen Änderungen erzeugen.

## Multi-Server-Ausblick

Das Layout ist absichtlich rollenunabhängig. Ein späterer `app_server`, `database_server` oder `backup_server` kann zusätzliche Einträge über Gruppenvariablen erhalten, ohne das gemeinsame Bootstrap-Prinzip zu ändern.

Beispiele:

- App-Server: `/srv/merchfactory/persistent/app`
- Datenbankserver: dedizierter DB-Mountpoint
- Backupserver: separates Backup-Dateisystem
- Shared Storage: später NFS/Object-Storage-spezifische Rollen

Die konkrete Multi-Server- und HA-Architektur bleibt außerhalb von v0.4.

Das auf dieser Verzeichnisbasis aufbauende Container-Persistenzmodell ist in `docs/50-volume-persistence-model.md` verbindlich definiert. Das getrennte Secret-Modell ist in `docs/51-secret-management.md` beschrieben.

## Rollback

Verzeichnisrechte können durch Revert der Inventory-/Rollenwerte und erneute Ausführung zurückgesetzt werden. Bei Mounts muss vor einem Unmount geprüft werden, ob Prozesse oder Container den Pfad verwenden.

Bereits auf einem Dateisystem vorhandene Daten werden durch einen Repository-Revert nicht automatisch verschoben oder gelöscht.
