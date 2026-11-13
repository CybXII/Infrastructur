# Plattform-Storage

Dieser Bereich enthält Werkzeuge und Regeln für persistente Hostpfade der Merchfactory Container Platform.

## Persistente Verzeichnisse vorbereiten

`prepare-persistent-directory.sh` legt einen einzelnen persistenten Servicepfad idempotent an und prüft Owner, Group und Mode.

Beispiel:

```bash
sudo bash platform/storage/scripts/prepare-persistent-directory.sh \
  /srv/merchfactory/persistent/odoo/filestore \
  101 \
  101 \
  0750
```

Die tatsächliche UID/GID muss zum eingesetzten Container-Image passen und wird servicebezogen dokumentiert.

Standardmäßig sind nur diese Basispfade zulässig:

- `/srv/merchfactory/persistent`
- `/srv/merchfactory/shared`
- `/var/lib/merchfactory`

Das Skript führt kein rekursives `chown` bestehender Daten durch.

Das vollständige Modell ist in `docs/50-volume-persistence-model.md` dokumentiert.
