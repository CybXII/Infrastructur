# Scripts

## Zweck

Dieses Verzeichnis enthält kleine, wiederverwendbare Betriebs-, Validierungs- und Entwicklungswerkzeuge.

## Einstieg

Hier liegen CI-Helfer, Wartungs-, Diagnose-, Migrations- und Validierungsskripte.

Für den Server-Bootstrap stehen zur Verfügung:

- `create-bootstrap-test-inventories.py` erzeugt zur Laufzeit getrennte
  Inventare für den initialen Provider-Zugang und den anschließend verwalteten
  Bootstrap-Benutzer.
- `test-bootstrap-idempotency.sh` prüft zwei Läufe mit derselben Identität.
- `test-bootstrap-fresh-host.sh` orchestriert Preflight, initialen Bootstrap,
  Identitätswechsel, Idempotenz sowie Sicherheits- und Funktionschecks.

Die Fresh-Host-Skripte erwarten ausschließlich temporäre Inventare. Private
Schlüssel und reale Zugangsdaten werden nicht als Argumente übergeben und
nicht im Repository gespeichert.

Für Container-Images stehen zusätzlich zur Verfügung:

- `validate-image-policy.py` normalisiert Compose-Manifeste und prüft Digest-Pinning, explizite Registrynamen sowie First-Party-/Drittanbieter-Allowlist.
- `check-secrets.py` prüft Repository und Git-Historie auf wahrscheinliche Secret-Leaks.
- `render-service-template.py` erzeugt aus dem Standard-Service-Template eine vollständige, platzhalterfreie Service-Struktur und validiert zentrale Eingaben bereits vor der Ausgabe.

## Abgrenzung

Komplexe Deployment- oder Backup-Logik bleibt in den jeweiligen Fachverzeichnissen. Skripte müssen Eingaben validieren, sinnvolle Exit-Codes liefern und sichere Standardwerte verwenden.

## Referenzen

- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`

## v0.5 Plattformvalidierung

`validate-platform-validation.py` prüft die maschinenlesbare Evidence-Matrix aus `configuration/platform-validation.json`.

Der Validator bestätigt unter anderem:

- Pflichtbereiche Routing, TLS, Isolation, Persistenz und Rollback,
- Existenz der referenzierten Testdateien,
- Existenz der referenzierten GitHub-Actions-Jobs,
- zentrale dokumentierte Fehlerfälle,
- die explizite Monitoring-Freigabe,
- den abgeschlossenen Release-Gate-Stand von v0.5.

Aufruf:

```bash
python3 scripts/validate-platform-validation.py
```


## Docker-Retention und Cleanup

`docker-retention-cleanup.py` plant und führt ein rollback-sicheres Docker-Cleanup aus.

Dry-Run:

```bash
python3 scripts/docker-retention-cleanup.py
```

Apply:

```bash
sudo python3 scripts/docker-retention-cleanup.py --apply
```

Geschützt werden laufende/noch referenzierte Containerimages sowie `current` und die zwei vorherigen known-good Digests aus den Deployment-States. Automatisches Volume-Pruning ist ausgeschlossen.

Details: `docs/59-docker-retention-cleanup.md`.

## v0.6 Monitoring-Stack

`validate-monitoring-stack.py` prüft `configuration/monitoring-stack.json` gegen die Architektur aus ADR-0008.

Unter anderem werden geprüft:

- Pflichtkomponenten und Versionsformat,
- zentrale Container vs. Host-Agenten,
- Prometheus Pull-/Retention-Vertrag,
- Public-Ingress-Grenzen,
- Docker-Socket-/TCP-API-Grenzen,
- Alloy/Loki-Logpipeline,
- External-Probe-Unabhängigkeit,
- Persistenzpfade,
- Issue-Zuordnung #85–#99.

Aufruf:

```bash
python3 scripts/validate-monitoring-stack.py
```
