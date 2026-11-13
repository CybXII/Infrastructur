# Logging-Standards

## Zweck

Dieses Dokument definiert verbindliche Logging-Anforderungen für Infrastruktur, Container, Skripte, Deployments und Automatisierungen.

## Grundprinzipien

Logs müssen maschinenlesbar, zeitlich eindeutig, korrelierbar, sicher und für den Betrieb nutzbar sein. Logs ersetzen weder Metriken noch Audit-Protokolle, ergänzen diese jedoch.

## Format

Neue Anwendungen und Automatisierungen verwenden bevorzugt strukturierte JSON-Logs mit genau einem Ereignis pro Zeile.

Mindestfelder:

```json
{
  "timestamp": "2026-07-27T02:00:00.123Z",
  "level": "info",
  "service": "shopify-bridge",
  "environment": "prd",
  "event": "order_import_completed",
  "message": "Bestellimport abgeschlossen",
  "correlation_id": "ord-8c31f2",
  "duration_ms": 842
}
```

Unstrukturierte Textlogs sind nur zulässig, wenn ein Werkzeug kein strukturiertes Format unterstützt. Sie müssen mindestens Zeitstempel, Schweregrad, Komponente und Nachricht enthalten.

## Zeitstempel

- ISO 8601 / RFC 3339
- UTC mit `Z`
- Millisekunden, sofern technisch verfügbar
- Systemzeit über NTP synchronisiert
- lokale Zeitzonen gehören nicht in persistierte technische Logs

## Schweregrade

| Level | Verwendung |
|---|---|
| `debug` | detaillierte Diagnose, standardmäßig in Production deaktiviert |
| `info` | erwartete Betriebsereignisse und erfolgreiche Zustandswechsel |
| `warning` | unerwarteter, aber kompensierter Zustand |
| `error` | fehlgeschlagene Operation mit Betriebs- oder Datenwirkung |
| `critical` | unmittelbare Betriebs-, Sicherheits- oder Datenintegritätsgefahr |

Erwartbare Validierungsfehler werden nicht pauschal als `critical` protokolliert.

## Ereignisnamen

`event` verwendet `snake_case`, ist stabil und beschreibt das Ergebnis:

```text
deployment_started
deployment_completed
deployment_failed
backup_completed
order_import_rejected
authentication_failed
```

Freitext steht in `message`; Auswertungen dürfen nicht vom exakten Nachrichtentext abhängen.

## Korrelation

Vorgänge über mehrere Systeme verwenden eine gemeinsame Korrelations-ID. Zulässige Felder:

- `correlation_id`
- `request_id`
- `job_id`
- `workflow_id`
- `order_reference`
- `deployment_id`

Interne technische IDs sind zulässig. Personenbezogene Daten werden nicht als Korrelations-ID verwendet.

## Kontextfelder

Je nach Ereignis werden ergänzt:

```text
host
container
project
component
operation
duration_ms
result
retry_count
http_status
exit_code
```

Felder bleiben typstabil. Zahlen werden nicht als Texte protokolliert.

## Sensitive Daten

Nie protokollieren:

- Passwörter und private Schlüssel
- API-Tokens, Session-Cookies und Authorization-Header
- vollständige Webhook-Signaturen
- Datenbank-Verbindungsstrings mit Zugangsdaten
- vollständige Zahlungsdaten
- vollständige Kundenadressen oder unnötige personenbezogene Daten
- Datei- oder Request-Inhalte, wenn sie vertrauliche Produktionsdaten enthalten

Zulässig sind maskierte Werte, beispielsweise:

```text
api_token=***
email=a***@example.com
```

Fehlerobjekte und externe API-Antworten werden vor dem Logging gefiltert.

## Container und Standardausgabe

Container schreiben Anwendungslogs nach `stdout` und Fehler nach `stderr`. Persistenz und Weiterleitung übernimmt die Plattform. Anwendungen schreiben keine unkontrollierten Logdateien in das Container-Dateisystem.

Lokale Containerlogs werden über den Docker-`local`-Driver mit fester Rotation begrenzt; servicebezogene Logging-Overrides sind in der Standardbaseline nicht zulässig. Details stehen in `docs/56-log-rotation.md`.

Docker- und Compose-Metadaten müssen Umgebung, Projekt, Service und Container zuordnen lassen.

## Infrastruktur und Automatisierungen

Skripte verwenden klare Präfixe oder strukturierte Ausgabe. Erfolgreiche Befehle werden nicht vollständig mit sensiblen Argumenten gespiegelt. Shell-Skripte verwenden kein globales `set -x` in Production.

Deployments protokollieren mindestens:

- Zielumgebung und Zielhost
- Commit-SHA oder Release-Tag
- Start, Ende und Ergebnis
- ausgeführte Hauptphase
- Rollback-Ergebnis, falls ausgelöst

## Weiterleitung

Produktive Logs werden zentral gesammelt. Das Zielsystem muss mindestens ermöglichen:

- Suche nach Zeit, Service, Umgebung und Korrelation
- Zugriffskontrolle
- Aufbewahrungsregeln
- Alarmierung auf definierte Ereignisse
- nachvollziehbare Löschung

Ein Ausfall der zentralen Weiterleitung darf Anwendungen nicht unbegrenzt blockieren. Puffer sind begrenzt und überwacht.

## Aufbewahrung

Richtwerte, sofern kein strengerer Fach- oder Rechtsbedarf besteht:

| Klasse | Aufbewahrung |
|---|---:|
| Debug | maximal 7 Tage |
| reguläre Betriebslogs | 30 Tage |
| Fehlerlogs | 90 Tage |
| Security-relevante Logs | 365 Tage |
| Audit-relevante Ereignisse | 365 Tage |
| Deployment-/Backup-Nachweise | 365 Tage |

Längere Aufbewahrung benötigt Zweck, Zugriffsschutz und Löschkonzept. Die lokale Docker-/journald-Rotation und das Verhältnis zur zentralen Aufbewahrung sind in `docs/56-log-rotation.md` verbindlich definiert.

## Alarmierung

Nicht jeder Fehler erzeugt einen Alarm. Alarmiert werden insbesondere:

- wiederholte oder anhaltende Fehler
- kritische Security-Ereignisse
- fehlgeschlagene Backups
- fehlgeschlagene produktive Deployments
- Datenintegritätsfehler
- vollständiger Ausfall der Logweiterleitung

Alarme enthalten Link oder Abfrage zur zugehörigen Korrelation, aber keine Secrets.

## Qualität und Tests

Neue Komponenten werden geprüft auf:

1. vorhandene Mindestfelder
2. korrekte UTC-Zeitstempel
3. stabile Schweregrade und Ereignisnamen
4. Korrelation über Prozessgrenzen
5. Redaction sensibler Daten
6. Verhalten bei nicht erreichbarer Logplattform
7. definierte Aufbewahrung

## Definition of Done für Issue #45

- Logformat und Mindestfelder sind definiert.
- Zeitstempel und Schweregrade sind verbindlich geregelt.
- Korrelation und Ereignisnamen sind festgelegt.
- sensitive Daten sind ausgeschlossen.
- Weiterleitung, Aufbewahrung und Alarmierung sind berücksichtigt.

## Referenzen

- `docs/21-server-naming-conventions.md`
- `docs/22-container-naming-conventions.md`
- `docs/23-network-naming-conventions.md`
- `docs/56-log-rotation.md`
- Issue #45
- Epic #35
