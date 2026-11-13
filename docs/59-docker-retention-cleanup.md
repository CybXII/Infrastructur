# Docker-Retention und Cleanup

## Zweck

Dieses Dokument definiert die kontrollierte Bereinigung von gestoppten Containern, ungenutzten Images, Dangling Images und Build-Cache für die Merchfactory Container Platform. Es setzt Issue #231 um.

Das Cleanup ist ausdrücklich **kein** allgemeines `docker system prune -a --volumes`.

## Sicherheitsprinzipien

Automatisches Cleanup darf niemals:

- laufende Container entfernen,
- Images laufender Container entfernen,
- Images entfernen, die von verbleibenden Containern benötigt werden,
- den aktuellen known-good Release-Digest entfernen,
- die zwei vorherigen Rollback-Digests entfernen,
- persistente Volumes löschen,
- `docker volume prune` ausführen,
- Images mit `--force` entfernen.

## Cleanup-Scope

### Gestoppte Container

Nur Container mit:

```text
com.merchfactory.managed=true
```

sind automatisch cleanup-fähig.

Zusätzlich kann ein Container explizit geschützt werden:

```text
com.merchfactory.cleanup.protect=true
```

Standard-Retention:

```text
7 Tage
```

Nur Zustände `created`, `exited` und `dead` werden betrachtet.

### Ungenutzte Images

Standard-Retention:

```text
30 Tage
```

Automatisch entfernt werden nur ungenutzte Images aus:

- dem First-Party-Namespace aus `configuration/container-image-policy.json`,
- explizit allowgelisteten Drittanbieter-Repositories.

Images, die von irgendeinem verbleibenden Container verwendet werden, bleiben geschützt.

### Dangling Images

Standard-Retention:

```text
7 Tage
```

Dangling Images besitzen weder Tags noch Repo-Digests und werden nach der Frist entfernt, sofern sie nicht durch einen Container oder Deployment-State geschützt sind.

### Build-Cache

Standard-Retention:

```text
168 Stunden / 7 Tage (`168h`)
```

Bereinigung:

```bash
docker builder prune --force --filter until=168h
```

Es wird kein Volume-Prune gekoppelt.

## Rollback-Schutz

Das Cleanup liest:

```text
/srv/merchfactory/deployments/*/state.json
```

und schützt pro Service:

- `current.image`,
- die ersten zwei Einträge aus `previous[].image`.

Damit entspricht das Host-Cleanup dem Rollback-Modell aus #79 und der Registry-Retention.

Kann ein geschützter Digest lokal nicht aufgelöst werden, wird die Referenz im Report als unresolved geführt. Die Referenz selbst bleibt weiterhin als geschützter Release-State bestehen.

## Deployment-Sicherheitsgate

Cleanup mit `--apply` läuft nur, wenn ein stabiler Release-State vorhanden ist.

Erlaubte letzte Zustände:

```text
success
failed-rolled-back
manual-rollback-success
```

Diese Zustände entstehen erst nach erfolgreicher Verifikation beziehungsweise erfolgreich verifiziertem Rollback.

Cleanup wird übersprungen, wenn:

- noch kein Release-State vorhanden ist,
- ein Deployment-Lock aktiv ist,
- der letzte Deploymentzustand nicht stabil ist,
- z. B. `rollback-failed` oder `failed-manual-intervention-required` vorliegt.

Damit erfüllt das Cleanup die Leitplanke „erst nach erfolgreichem Deployment und Healthcheck“.

## Dry-Run

Standardmäßig verändert das Skript nichts:

```bash
python3 scripts/docker-retention-cleanup.py
```

Ausgegeben werden:

- Sicherheitsgate,
- geschützte Release-Digests,
- zu entfernende Container,
- zu entfernende Images,
- geplanter Build-Cache-Befehl,
- expliziter Hinweis, dass Volumes nicht angefasst werden.

## Apply

```bash
sudo python3 /usr/local/sbin/merchfactory-docker-cleanup \
  --apply \
  --policy /etc/merchfactory/docker-cleanup-policy.json \
  --image-policy /etc/merchfactory/container-image-policy.json \
  --deployment-state-root /srv/merchfactory/deployments \
  --report /var/log/merchfactory/docker-cleanup/latest.json
```

Reihenfolge:

1. alte managed Stopped-Container,
2. nicht mehr verwendete cleanup-fähige Images,
3. alter Build-Cache.

Volumes werden nie automatisch bereinigt.

## Reproduzierbarkeit

Die Policy ist maschinenlesbar:

```text
configuration/docker-cleanup-policy.json
```

Die Hostinstallation erfolgt über:

```text
ansible/roles/docker_cleanup/
```

Installiert werden:

- Cleanup-Skript,
- Cleanup-Policy,
- Container-Image-Policy,
- systemd Service,
- systemd Timer,
- Report-Verzeichnis.

## Zeitplan

Standard:

```text
Sonntag 04:30
RandomizedDelaySec=900
Persistent=true
```

Das liegt nach dem bestehenden Paketupdate-Fenster am Sonntag 03:30.

## Logging und Report

Jeder Lauf schreibt nach journald und optional einen strukturierten Report:

```text
/var/log/merchfactory/docker-cleanup/latest.json
```

Der Report enthält keine Secrets.

## Fehlerverhalten

Ein fehlgeschlagenes einzelnes Container-/Image-Removal wird protokolliert und führt zu einem Fehlerstatus des Cleanup-Laufs.

Es wird nicht mit `--force` nachbereinigt.

Ein Safety-Gate-Skip ist kein Fehler, sondern ein bewusstes Nicht-Ausführen.

## Persistente Volumes

Automatisches Volume-Cleanup ist verboten.

Nicht verwendet werden:

```text
docker volume prune
docker system prune --volumes
```

Persistente Daten werden ausschließlich über die expliziten Backup-/Lifecycle-Prozesse behandelt.

## Tests

Der Integrationstest validiert:

1. Dry-Run verändert nichts.
2. unstabiler Deployment-State blockiert Apply.
3. stabiler Release-State erlaubt Apply.
4. current und previous Rollback-Digests bleiben vorhanden.
5. Image eines laufenden Containers bleibt vorhanden.
6. alter managed Stopped-Container wird entfernt.
7. ungenutztes First-Party-Testimage wird entfernt.
8. Dangling Image wird entfernt.
9. Build-Cache-Prune wird ausgeführt.
10. persistentes Docker-Volume bleibt vorhanden.
11. es wird kein `docker volume prune` ausgeführt.

## Referenzen

- `configuration/docker-cleanup-policy.json`
- `configuration/container-image-policy.json`
- `configuration/deployment-policy.json`
- `deployment/service-release.py`
- `docs/52-container-registry-security.md`
- `docs/57-update-rollback.md`
- `docs/58-container-platform-validation.md`
