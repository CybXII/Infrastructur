# Update- und Rollback-Verfahren

## Zweck

Dieses Dokument definiert das verbindliche Verfahren für kontrollierte Service-Updates und Rollbacks der Merchfactory Container Platform. Es setzt Issue #79 um.

Das Verfahren baut auf unveränderlichen Image-Digests, getesteten Backups, Health-/Smoke-Verifikation und den Freigabestufen aus CI/CD auf.

## Grundsatz

Ein Deployment ist erst erfolgreich, wenn die neue Version nach dem Start technisch und fachlich verifiziert wurde.

Der Ablauf ist:

```text
Freigabe
  -> Preflight
  -> Backup / Restore-Plan falls erforderlich
  -> Ziel-Digest pullen
  -> Compose-Konfiguration validieren
  -> Service aktualisieren
  -> Health-/Smoke-Test
  -> Freigabestatus speichern

bei Fehler:
  -> weitere Ausrollung stoppen
  -> Rollback, wenn datenkompatibel
  -> Rollback verifizieren
  -> Deployment trotzdem als fehlgeschlagen markieren
```

## Unveränderliche Versionen

Updates referenzieren ausschließlich vollständige OCI-Image-Digests:

```text
registry/repository@sha256:<64-hex>
```

Tags wie `latest`, `19` oder `stable` sind keine Deployment-Version.

Development, Staging und Production promoten denselben Digest; für Production wird nicht neu gebaut.

## Laufzeitzustand

Der Standard-Service verwendet:

```text
SERVICE_IMAGE_REFERENCE
```

als Runtime-Imagevariable.

Plattformdienste dürfen bei eindeutigem Servicevertrag eigene Image-Variablen verwenden, zum Beispiel:

```text
PROMETHEUS_IMAGE_REFERENCE
LOKI_IMAGE_REFERENCE
```

Der Deployment-Controller erhält diese über `--image-env-key`. Der Default bleibt `SERVICE_IMAGE_REFERENCE`, sodass bestehende Standardservices unverändert kompatibel bleiben. Zulässig sind ausschließlich Variablennamen nach `[A-Z][A-Z0-9_]*`.

Empfohlene Hoststruktur:

```text
/srv/merchfactory/deployments/<service>/
├── release.env
├── state.json
└── .deployment.lock
```

`release.env` enthält ausschließlich die nicht geheime Image-Referenz.

`state.json` dokumentiert:

- aktuellen bekannten guten Digest,
- bis zu zwei vorherige bekannte gute Digests,
- Source Revision,
- Release-/Approval-Referenz,
- Backup-Referenz,
- Zeitpunkt und Ergebnis des letzten Deploymentversuchs.

Diese Datei enthält keine Secrets.

## Geschützte Rollback-Versionen

Der aktuelle Produktions-Digest und die zwei vorherigen bekannten guten Digests werden weder durch Registry-Cleanup noch durch das lokale Docker-Retention-Cleanup entfernt.

Das Host-Cleanup aus `docs/59-docker-retention-cleanup.md` liest dafür `state.json` direkt aus `/srv/merchfactory/deployments/*/`.

Deshalb gilt:

- `state.json` ist betrieblicher Schutzstate und darf nicht manuell verkürzt werden,
- `current.image` und die ersten zwei `previous[].image` bleiben lokal geschützt,
- ein aktiver `.deployment.lock` blockiert Cleanup,
- instabile Deploymentzustände blockieren Apply,
- persistente Volumes werden unabhängig davon nie automatisch gepruned.

Dies entspricht der Registry-Retention aus `configuration/container-image-policy.json`.

## Preflight

Vor jeder Änderung sind mindestens erforderlich:

1. Compose-Datei vorhanden und renderbar.
2. Zielservice existiert im Manifest.
3. Zielimage ist vollständig per SHA-256-Digest gepinnt.
4. Registry/Repository ist durch die Image-Policy erlaubt.
5. Zielimage kann erfolgreich gepullt werden.
6. benötigte Secrets und persistente Pfade sind außerhalb des Controllers vorbereitet.
7. eine Verifikationsprobe ist definiert.
8. erforderliche Freigabe liegt vor.
9. bei Datenänderungen liegt ein geeignetes Backup vor.
10. bei destruktiven Datenänderungen liegt zusätzlich ein Restore-Plan vor.

Fehlt eine Bedingung, startet das Update nicht.

## Freigaben

### Development

CI und normale Entwicklungsfreigabe reichen aus.

### Staging

Eine Approval-Referenz ist erforderlich, beispielsweise die freigegebene GitHub-Environment-/Release-Referenz.

### Production

Eine Production-Approval-Referenz ist verpflichtend. Self-Approval-Regeln werden durch das GitHub Environment und nicht durch lokale Hostparameter ersetzt.

Der Deployment-Controller speichert die Referenz nur für Nachvollziehbarkeit.

## Datenänderungsklassen

### none

Keine persistente Datenänderung.

- Backup durch dieses Update nicht zwingend.
- automatischer Artefakt-Rollback erlaubt.

### compatible

Persistente Änderung ist rückwärtskompatibel, beispielsweise additive Migration.

- Backup-Referenz verpflichtend.
- automatischer Artefakt-Rollback zulässig.
- fachliche Migrationsprüfung bleibt erforderlich.

### destructive

Schema-/Datenänderung ist potenziell nicht rückwärtskompatibel.

- Backup-Referenz verpflichtend.
- Restore-Plan verpflichtend.
- automatischer Artefakt-Rollback verboten.
- bei Fehler stoppt das Verfahren und fordert manuelle Restore-/Roll-forward-Entscheidung.

Ein älterer Container gegen ein inkompatibel migriertes Schema ist kein sicherer Rollback.

## Backups

Der Deployment-Controller erzeugt bewusst keine fachlich falschen Universalbackups.

Die jeweilige `backup/policy.yaml` bestimmt das korrekte Verfahren, z. B.:

- PostgreSQL Dump/PITR,
- Volume-Snapshot,
- anwendungsspezifischer Export.

Vor einem Update mit `compatible` oder `destructive` muss ein erfolgreiches Backup bereits existieren. Seine ID/Referenz wird dem Deployment übergeben und im State dokumentiert.

## Deployment-Controller

Referenzimplementierung:

```text
deployment/service-release.py
```

Beispiel:

```bash
python3 deployment/service-release.py deploy \
  --compose-file deployment/compose.yaml \
  --project-name my-service \
  --service my-service \
  --state-file /srv/merchfactory/deployments/my-service/state.json \
  --release-env /srv/merchfactory/deployments/my-service/release.env \
  --target-image ghcr.io/merchfactory/my-service@sha256:<digest> \
  --image-env-key SERVICE_IMAGE_REFERENCE \
  --environment staging \
  --approval-reference github-environment:staging/12345 \
  --source-revision <commit-sha> \
  --release-reference <release-id> \
  --verify-url https://service.example.invalid/ready
```

Für Worker oder interne Dienste kann statt HTTP ein ausführbares Verifikationsprogramm über `--verify-exec` verwendet werden.

## Update-Verhalten

Der Controller:

1. validiert Image und Compose-Auflösung,
2. pullt den Ziel-Digest,
3. schreibt `release.env` atomar,
4. startet nur den betroffenen Compose-Service neu,
5. wartet auf Container-/Smoke-Verifikation,
6. verschiebt den vorherigen bekannten guten Release in die Rollback-Historie,
7. schreibt den neuen Zustand atomar.

Parallele Deployments desselben Zustandsverzeichnisses werden per File Lock verhindert.

## Automatischer Rollback

Bei einem datenkompatiblen Update und fehlgeschlagenem Smoke-Test:

1. neuer Digest wird als fehlgeschlagen erfasst,
2. vorheriger bekannte gute Digest wird gepullt,
3. `release.env` wird atomar zurückgesetzt,
4. Compose erstellt den Service mit dem alten Digest neu,
5. dieselbe Verifikationsprobe muss erfolgreich sein,
6. State bleibt auf dem vorherigen bekannten guten Release,
7. der Deployment-Befehl endet trotzdem mit Fehlercode.

Damit kann CI/CD nicht versehentlich einen fehlgeschlagenen Release als Erfolg markieren, nur weil der Rollback funktioniert hat.

## Manueller Rollback

Beispiel:

```bash
python3 deployment/service-release.py rollback \
  --compose-file deployment/compose.yaml \
  --project-name my-service \
  --service my-service \
  --state-file /srv/merchfactory/deployments/my-service/state.json \
  --release-env /srv/merchfactory/deployments/my-service/release.env \
  --environment production \
  --approval-reference incident:INC-1234 \
  --verify-url https://service.example.invalid/ready
```

Der Controller verwendet die neueste bekannte gute Version aus `previous` und verifiziert auch den Rollback.

## Fehlerzustände

### Preflight fehlgeschlagen

Keine Änderung am laufenden Service.

### Pull fehlgeschlagen

Keine Änderung am laufenden Service.

### Deployment/Verifikation fehlgeschlagen, Auto-Rollback erlaubt

Bekannte gute Version wird wiederhergestellt und geprüft. Deployment bleibt als Fehler markiert.

### Deployment/Verifikation fehlgeschlagen, Auto-Rollback verboten

State erhält `failed-manual-intervention-required`. Weitere Änderungen erst nach Restore-/Roll-forward-Entscheidung.

### Rollback ebenfalls fehlgeschlagen

Status `rollback-failed`. Incident/Eskalation erforderlich; keine weiteren automatischen Änderungen.

## Stabilisierungsphase

Ein erfolgreicher technischer Smoke-Test beendet nicht die fachliche Beobachtung.

Für Production werden nach Freigabe insbesondere beobachtet:

- Error Rate,
- Latenz,
- CPU-/Memory-Verhalten,
- OOM/Restarts,
- Logs,
- Datenbankfehler,
- geschäftskritische Integrationen.

Bei relevanten Auffälligkeiten wird gemäß Rollback-Kriterien entschieden.

## Notfalländerungen

Emergency Changes benötigen:

- Incident-Referenz,
- kleinstmöglichen Scope,
- bekannte gute Rollback-Version,
- nachträglichen PR/Review.

Auch ein Hotfix wird über einen Digest deployt.

## Tests

Die CI führt einen echten Rollback-Test aus:

1. gepinntes `traefik/whoami` wird als bekannte gute Version deployt.
2. `/health` liefert HTTP 200.
3. ein anderer gepinnter, aber für diesen Testservice ungeeigneter Traefik-Digest wird als Update versucht.
4. der Smoke-Test schlägt fehl.
5. Controller rollt automatisch auf den vorherigen Whoami-Digest zurück.
6. `/health` liefert wieder HTTP 200.
7. State meldet `failed-rolled-back`.
8. der Deploymentversuch liefert einen Fehlercode.
9. der laufende Container verwendet wieder den ursprünglichen Digest.

Damit ist nicht nur der Happy Path, sondern die tatsächliche Wiederherstellung der letzten bekannten guten Version geprüft.

## Odoo-Ausblick

Bei Odoo ist die Datenänderungsklasse besonders wichtig.

- reiner Image-/Codewechsel ohne Migration kann automatisch rollbackfähig sein,
- additive, rückwärtskompatible Module-/Schemaänderungen benötigen Backup und Test,
- irreversible Modul-/Datenbankmigrationen dürfen nicht durch einen simplen Container-Downgrade „zurückgerollt“ werden.

Vor produktiven Odoo-Upgrades werden PostgreSQL-Backup/PITR, Filestore und Modulmigrationspfad gemeinsam bewertet.

## Referenzen

- `configuration/deployment-policy.json`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/07-disaster-recovery.md`
- `docs/52-container-registry-security.md`
- `docs/53-standard-service-template.md`
- `docs/59-docker-retention-cleanup.md`
