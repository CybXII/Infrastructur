# Plattform-Secrets

Dieser Bereich enthält die hostseitigen Werkzeuge für das Secret-Management der Merchfactory Container Platform.

## Runtime-Pfad

Standard:

```text
/srv/merchfactory/secrets/<service>/<secret-name>
```

Der Secret-Wert wird nicht im Repository abgelegt.

## Secret installieren oder rotieren

Das Installationswerkzeug liest den Wert ausschließlich von stdin:

```bash
printf '%s' "$SECRET_FROM_APPROVED_SOURCE" \
  | sudo bash platform/secrets/scripts/install-secret-file.sh \
      example-service api-token 1000 1000
```

Standardmodus ist `0400`.

Optional kann als fünftes Argument `0440` gesetzt werden, wenn ein dokumentierter Gruppenlesezugriff erforderlich ist.

Das Werkzeug gibt ausschließlich den Zielpfad zurück und niemals den Secret-Wert.

Details zu Quellen, Zugriff, Rotation und Recovery stehen in `docs/51-secret-management.md`.
