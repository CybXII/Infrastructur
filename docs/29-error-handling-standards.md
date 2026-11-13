# Fehlerbehandlungsstandards

## Zweck

Dieses Dokument definiert verbindliche Regeln für Fehlerklassen, Exit Codes, Abbruchverhalten, Timeouts, Wiederholungen und sichere Fehlermeldungen.

## Grundprinzipien

Fehler werden früh erkannt, eindeutig klassifiziert, sicher protokolliert und kontrolliert behandelt. Ein Fehler darf weder still verschwinden noch unkontrollierte Teilzustände hinterlassen.

## Fehlerklassen

| Klasse | Bedeutung | Typische Reaktion |
|---|---|---|
| `validation_error` | Eingabe oder Konfiguration ungültig | sofort abbrechen, nicht wiederholen |
| `authentication_error` | Zugangsdaten fehlen oder sind ungültig | abbrechen, Secret prüfen |
| `authorization_error` | Berechtigung fehlt | abbrechen, Berechtigungsmodell prüfen |
| `not_found_error` | erwartete Ressource fehlt | abhängig vom Vertrag abbrechen oder definiert überspringen |
| `conflict_error` | Zustand verhindert Änderung | Zustand neu laden, idempotent behandeln |
| `rate_limit_error` | Gegenstelle begrenzt Anfragen | verzögert wiederholen |
| `timeout_error` | Operation überschreitet Zeitlimit | begrenzt wiederholen, sofern idempotent |
| `dependency_error` | externer Dienst nicht verfügbar | begrenzt wiederholen oder kontrolliert abbrechen |
| `data_integrity_error` | Daten widersprüchlich oder beschädigt | sofort stoppen und eskalieren |
| `internal_error` | unerwarteter interner Fehler | sicher abbrechen und diagnostizieren |

## Exit Codes

Für eigene Skripte gelten:

| Code | Bedeutung |
|---|---|
| `0` | erfolgreich |
| `2` | ungültige Argumente oder Konfiguration |
| `3` | Authentifizierungs- oder Berechtigungsfehler |
| `4` | Ressource oder Abhängigkeit fehlt |
| `5` | Konflikt oder ungültiger Systemzustand |
| `6` | temporärer externer Fehler nach ausgeschöpften Retries |
| `7` | Datenintegritätsfehler |
| `10` | unerwarteter interner Fehler |

Werkzeuge mit etablierten Exit Codes behalten deren Semantik. Wrapper dokumentieren die Übersetzung.

## Abbruchverhalten

Sofortiger Abbruch ist verpflichtend bei:

- ungültiger Pflichtkonfiguration
- fehlender Authentifizierung
- Datenintegritätsfehlern
- fehlgeschlagenem Backup vor riskanter Migration
- nicht verifizierbarem Zielsystem
- nicht erfüllten Sicherheitsvorbedingungen

Batch-Verarbeitung darf einzelne Datensätze nur dann isoliert ablehnen, wenn:

- der Fehler datensatzbezogen ist,
- weitere Datensätze unabhängig sind,
- Fehlerliste und Korrelation erhalten bleiben,
- ein definierter Gesamtstatus ausgegeben wird.

## Atomarität und Teilzustände

Operationen werden möglichst atomar oder idempotent umgesetzt. Bei mehreren Schritten gilt:

1. Vorbedingungen prüfen
2. Änderungen vorbereiten
3. kritische Änderung ausführen
4. Ergebnis verifizieren
5. bei Fehler rollbacken oder sicheren Zwischenzustand dokumentieren

Ein als erfolgreich gemeldeter Vorgang muss vollständig verifiziert sein.

## Timeouts

Jede Netzwerk-, Prozess- oder Sperroperation benötigt ein endliches Timeout.

Richtwerte:

| Operation | Richtwert |
|---|---|
| DNS/TCP-Verbindung | 5 Sekunden |
| normale API-Anfrage | 30 Sekunden |
| große Dateiübertragung | explizit nach Größe definiert |
| Deployment-Schritt | explizit pro Schritt, maximaler Gesamttimeout |
| Healthcheck | kurz und wiederholbar |

Timeouts werden nicht pauschal unbegrenzt erhöht. Ursache und erwartete Laufzeit sind zu prüfen.

## Retry-Regeln

Wiederholungen sind nur zulässig bei wahrscheinlich temporären und idempotenten Fehlern, insbesondere:

- HTTP `429`
- HTTP `502`, `503`, `504`
- Verbindungsabbruch vor bestätigter Verarbeitung
- temporäre DNS- oder Netzwerkfehler
- Timeout einer sicher wiederholbaren Leseoperation

Nicht automatisch wiederholen:

- Validierungsfehler
- `401` oder `403`
- Datenintegritätsfehler
- nicht idempotente Schreiboperation ohne Idempotency-Key
- fachliche Ablehnung

Standardstrategie:

```text
maximal 3 Versuche
exponentielles Backoff
1 s, 2 s, 4 s
zufälliger Jitter
Retry-After respektieren
```

Jeder Versuch protokolliert Versuchszahl und Korrelations-ID. Der letzte Fehler bleibt erhalten.

## Idempotenz

Schreiboperationen verwenden, soweit unterstützt:

- Idempotency-Key
- eindeutige externe Referenz
- Upsert mit klarer Konfliktregel
- Transaktion
- Vorher-Nachher-Verifikation

Ein Retry darf keine doppelten Bestellungen, Deployments, E-Mails, Labels oder Zahlungen erzeugen.

## Fehlermeldungen

Eine gute Fehlermeldung enthält:

- stabile Fehlerklasse oder Fehlerkennung
- betroffene Operation
- verständliche Ursache
- sichere Kontextangabe
- mögliche nächste Aktion
- Korrelations-ID

Beispiel:

```text
configuration_invalid: PRODUCTION_SSH_HOST fehlt; Deployment wurde vor Verbindungsaufbau abgebrochen; correlation_id=dep-7f21
```

Nicht zulässig:

```text
Something went wrong
Fehler 500
Token abc123 ist ungültig
```

Secrets, vollständige Payloads und unnötige personenbezogene Daten werden nicht ausgegeben.

## HTTP- und API-Fehler

Bei eigenen APIs gilt:

- `400` ungültige Anfrage
- `401` nicht authentifiziert
- `403` nicht berechtigt
- `404` Ressource fehlt
- `409` Konflikt oder bereits vorhandener Zustand
- `422` fachlich oder semantisch ungültig
- `429` Rate Limit
- `500` unerwarteter interner Fehler
- `502/503/504` Abhängigkeits- oder Verfügbarkeitsfehler

Antworten enthalten eine stabile Fehlerkennung und Korrelation, aber keine internen Stacktraces in Production.

## Shell-Skripte

Shell-Skripte verwenden grundsätzlich:

```bash
set -Eeuo pipefail
```

Zusätzlich:

- temporäre Dateien über `trap` bereinigen
- Rückgabewerte kritischer Befehle prüfen
- Variablen quoten
- keine Fehler mit `|| true` verschlucken, außer mit dokumentierter Absicht
- Fehlerhandler darf den ursprünglichen Exit Code nicht verlieren

## Diagnostik

Für jeden Fehler bleiben erhalten:

- Zeitstempel
- Fehlerklasse
- Komponente und Operation
- Korrelation
- Exit Code oder HTTP-Status
- Retry-Anzahl
- sichere Ursache
- Ergebnis von Rollback oder Cleanup

Stacktraces werden zentral geschützt gespeichert und nicht an externe Nutzer ausgegeben.

## Tests

Mindestens geprüft werden:

1. jede dokumentierte Fehlerklasse
2. Exit Codes
3. Timeout-Verhalten
4. Retry-Grenze und Backoff
5. nicht idempotente Operation ohne Retry
6. Cleanup und Rollback
7. Secret-Redaction
8. Erhalt der Korrelations-ID
9. Fehler nach teilweise ausgeführtem Ablauf

## Definition of Done für Issue #47

- Fehlerklassen und Exit Codes sind dokumentiert.
- Abbruch- und Teilverarbeitungsregeln sind definiert.
- Timeout-, Retry- und Idempotenzregeln sind festgelegt.
- Fehlermeldungen bleiben diagnostizierbar und sicher.
- Tests und Rollback-Verhalten sind berücksichtigt.

## Referenzen

- `docs/27-logging-standards.md`
- `docs/28-configuration-standards.md`
- Issue #47
- Epic #35
