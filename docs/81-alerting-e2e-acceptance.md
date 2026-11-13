# #98 – Alarmierung: Routing, Zustellung, Eskalation und Live-Abnahme

## Grenzen

Nur **Development**. Keine selbstständige Änderung an Firewall, Dienstports,
Webhook-Secrets oder produktiven Workloads. PR-CI nutzt ungültige lokale
Webhook-Fixtures; es sendet **keine** Nachrichten an den echten Discord-Kanal.
Die abschließenden echten FIRING/RESOLVED-Tests sind ein **bewusster manueller
Abnahmeschritt** nach dem kontrollierten Deployment.

## Behobener Routingvertrag (ab Deployment dieses PR)

| Prometheus-Severity | Alertmanager-Receiver | Reaktion |
|---|---|---|
| `high` | `discord-critical` | dringend während betreuter Zeit |
| `critical` (kompatibel) | `discord-critical` | dringend während betreuter Zeit |
| `warning` | `discord-warning` | reguläre zeitnahe Prüfung |
| `info` | `discord-info` | dokumentieren |
| unbekannt | `discord-default` | als Klassifikationsfehler nachverfolgen |

`high` und `critical` dürfen `warning`/`info` für dieselbe
`environment`/`service`/`instance`-Kombination inhibieren; der
bestehende Down/Unavailable-Inhibitor bleibt separat. Bei fehlenden oder
falsch vergebenen Labels ist Inhibition **kein** verlässlicher Ersatz für
die Prüfung mehrerer Alarme.

Die Discord-Meldung zeigt die originale Severity und bei Verfügbarkeit
`instance`, `mountpoint` und `device`. Das bisherige Label `host` kann
`prometheus` statt dem SSH-Hostnamen enthalten – bei Dateisystemproblemen
immer Mountpoint und tatsächliche Quelle anhand von Node Exporter prüfen.

## Reproduzierbare CI- und statische Abnahme

1. `tests/unit/test_alertmanager_discord.py` prüft Route/Alias/Template.
2. `tests/static/test-discord-notification-contract.sh` prüft Secretvertrag.
3. `tests/integration/test-alertmanager-deployment.sh` startet isoliert
   Alertmanager mit Dummy-Webhook; `amtool check-config` und
   `amtool config routes test --verify.receivers` prüfen `high`,
   `critical`, `warning`, `info` und unbekannte Severity.
4. Die synthetischen `promtool`-Tests prüfen Alarmausdrücke und Schwellen,
   **nicht** eine Discord-Zustellung. Die Tests von #96 decken 75/85 %
   Festplattenbelegung ab.
5. Ein grüner PR bedeutet **nicht**, dass der laufende Development-VPS
   bereits dieselbe Alertmanager-Konfiguration verwendet.

## Echte Development-FIRING-/RESOLVED-Prüfung

**Vorbereitungen:** Monitoring-Core-Deployment nach dem Merge grün;
genau ein betriebsbereiter Development-Alertmanager, funktionierender
Discord-Webhook und keine aktuell laufende Recovery-/Deployer-Störung.
Start und Label der Testnachricht dokumentieren. Test meldet einen
eindeutig synthetischen `monitoring-e2e-test`-Dienst und löst keine
echten Ausfälle aus.

Der Test verwendet ausschließlich `docker exec` am internen
Development-Alertmanager, **keinen öffentlich erreichbaren API-Port**.
Ausführen auf dem verwalteten Development-VPS:

```bash
# Read-only: Laufzeitroute gegen den echten Container prüfen
# Commit-SHA aus dem grünen Development-Monitoring-Deploy übernehmen
SOURCE_SHA="<deployment-source-sha>"
SMOKE="/srv/merchfactory/releases/development-monitoring/$SOURCE_SHA/scripts/test-development-alert-routing.sh"
test -f "$SMOKE" || { echo "Smoke-Skript fehlt im Release" >&2; exit 1; }
sudo bash "$SMOKE" --plan high
# Alternativ: sudo bash "$SMOKE" --plan warning

# Erst nach bewusster Freigabe: genau einen synthetischen high-Alert senden
sudo bash "$SMOKE" --apply --confirm-development high
```

`--plan [high|warning|info]` prüft ausschließlich das angegebene Routing,
ohne einen Alarm einzuspeisen. Der Live-Test verwendet UTF-8-parserkompatibel
quotierte Annotationen, damit keine irreführenden Parser-Fallback-Warnungen
die Zustellungsdiagnose überlagern.

Der Test-Alert läuft nach **3 Minuten** ohne erneute Einspeisung ab.
Die Discord-Meldung kann wegen der Grouping-Intervalle verzögert sein:
`group_wait=30s`, `group_interval=5m`, `repeat_interval=4h`.
Nach ausreichendem Zeitfenster **FIRING und RESOLVED getrennt in Discord
prüfen**; beide Nachrichten müssen denselben `test_run` bzw.
`alertname`/Labels entsprechen. `test_run` wird als `Testlauf` im Discord-Template angezeigt. Der Exit-Code des Skripts bestätigt
nur die Annahme durch Alertmanager, **nicht** Discord-Zustellung.
Das Skript darf weder automatisch beim Merge noch in einem regulären
CI-Lauf mit `--apply` ausgeführt werden.

Anschließend je einen `warning`- und `info`-Smoke mit demselben
Aufruf und letzter Severity durchführen, sofern benötigt. Echte
Inhibition muss gesondert anhand **gleichzeitig aktiver, passend
gelabelter** Tests überprüft werden; einzelne Smoke-Meldungen beweisen
noch keine Inhibition.

## Bereits beobachteter Live-Fall – 17.10.2026

Auf dem Development-VPS wurde
`HostFilesystemSpaceCritical` mit `severity=high` real über
Discord als **FIRING** empfangen. Das Root-Dateisystem war zu diesem
Zeitpunkt zu **91 %** belegt. Ursache: nicht bereinigte anonyme
Docker-in-Docker-Volumes des ephemeren Runner-Controllers. Nach
gezielter Bereinigung von **1.390** identifizierten DinD-Volumes sank
die Root-Belegung laut `df` auf rund **29–31 %**.

**Was das beweist:** Alarmbedingung erkannt; Prometheus → Alertmanager →
Discord hat zumindest für diesen konkreten Alarm funktioniert.
**Was es nicht beweist:** tatsächliche `RESOLVED`-Zustellung,
`discord-critical`-Routing nach dem neuen Patch, korrekte Inhibition,
Zertifikats-/DNS- und Backup-Alarm-E2E oder eine garantierte
Benachrichtigungszeit. Der alte `high`-Alarm wurde über
`discord-default` zugestellt.

## Abnahmeprotokoll

Für **jeden** Testfall dokumentieren:

```text
Datum/Uhrzeit (UTC), Development-Release-SHA:
Alertname, Severity, Labels, erwarteter Receiver:
Prometheus pending/firing (falls Prometheus-Regeltest):
Alertmanager received, matching receiver:
Discord FIRING (Zeit, Inhalt, Kanal, nachprüfbare Evidenz):
Discord RESOLVED (Zeit, Inhalt, Kanal, nachprüfbare Evidenz):
Zeit von Auslösung bis FIRING; Zeit bis RESOLVED:
Inhibition aktiv (ja/nein/nicht geprüft):
Fehlalarm / fehlende Signale / Datenverlust:
Runbook-Pfad und Reaktionsprüfung:
Fehlerursache, Follow-up-Issue und Reviewer:
```

Bewertung pro Szenario: **PASS**, **FAIL** oder **BLOCKED**.
Kein fehlender Test wird als PASS eingetragen. Testfelder mit
Kundendaten oder Secrets nicht ins Issue kopieren.

## Definition of Done

- [x] Programmatische Severity/Receiver-Konsistenz und statische
      Inhibition-Konfiguration vorbereitet.
- [x] Reales `HostFilesystemSpaceCritical`-FIRING im Development
      dokumentiert.
- [ ] Echte Development-Receiver nach Merge/Deployment prüfen.
- [ ] FIRING **und** RESOLVED für `high`, `warning` und mindestens
      ein relevantes Betriebsszenario in Discord bestätigen.
- [ ] Inhibition für gleiche Labels mit gleichzeitigen Alerts bestätigen.
- [ ] Backup- und externe HTTP/DNS/TLS-Proben nur im jeweils
      autorisierten Testzustand durchführen und dokumentieren.
- [ ] Verzögerung, Fehlalarme, fehlende Signale, Runbook und
      Eskalationszuständigkeiten bewerten.

Issue #98 wird **nicht** allein durch grüne PR-Checks geschlossen.
Verweis: `docs/80-monitoring-runbook.md`,
`docs/69-discord-alerting.md`, #95 und #96.
