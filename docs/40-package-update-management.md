# Automatisierte Paket- und Updateverwaltung

## Zweck

Die Rolle `package_updates` definiert eine kontrollierte Update-Strategie für AlmaLinux OS 9 und Rocky Linux 9. Sicherheitsupdates werden standardmäßig priorisiert, ein Wartungsfenster wird über einen systemd-Timer festgelegt und ein möglicher Neustartbedarf wird nach Updates explizit erkannt.

Die Rolle wird direkt nach `base_installation` ausgeführt. Dadurch werden Sicherheitsaktualisierungen angewendet, bevor Benutzerverwaltung, SSH-Hardening, Firewall und Fail2ban ihren endgültigen Zustand setzen.

## Standardstrategie

Standardmäßig gilt:

- Strategie: `security`
- Sicherheitsupdates werden beim Bootstrap angewendet.
- `dnf-automatic` übernimmt spätere Sicherheitsupdates.
- Wartungsfenster: Sonntag 03:30 Uhr Serverzeit.
- zufällige Verzögerung: maximal 15 Minuten.
- automatische Neustarts sind deaktiviert.
- ein erforderlicher Neustart wird erkannt und im Bootstrap ausgegeben.

Das Wartungsfenster verwendet die lokale Systemzeit. Die verbindliche Zeitzone wird separat über Issue #59 konfiguriert.

## Strategien

`package_updates_strategy` unterstützt drei Werte:

| Wert | Verhalten |
|---|---|
| `security` | ausschließlich als Security Advisory markierte Updates |
| `all` | alle verfügbaren Updates |
| `disabled` | keine verwaltete automatische Updateausführung |

Für produktive Systeme ist `security` der Standard. Ein Wechsel auf `all` muss bewusst erfolgen, da Funktions- und Versionsänderungen außerhalb reiner Sicherheitskorrekturen eingespielt werden können.

## Wartungsfenster

Das Standardfenster wird über systemd `OnCalendar` definiert:

```yaml
package_updates_maintenance_window: "Sun *-*-* 03:30:00"
package_updates_randomized_delay_sec: 900
```

Der Timer wird als Override für `dnf-automatic.timer` verwaltet. `Persistent=true` stellt sicher, dass ein verpasstes Fenster nachgeholt werden kann, sobald der Server wieder läuft.

Beispiele:

```yaml
# täglich um 04:00 Uhr
package_updates_maintenance_window: "*-*-* 04:00:00"

# Samstag um 02:30 Uhr
package_updates_maintenance_window: "Sat *-*-* 02:30:00"
```

## Bootstrap-Updates

Standardmäßig werden Sicherheitsupdates bereits während des Bootstrap-Laufs eingespielt:

```yaml
package_updates_apply_on_bootstrap: true
package_updates_strategy: security
```

Bei `security` verwendet Ansible die DNF-Sicherheitsmetadaten. Bei `all` werden sämtliche verfügbaren Updates installiert. Paketquellen werden nicht stillschweigend hinzugefügt; Repository-Freigaben bleiben Bestandteil der Basisinstallation beziehungsweise expliziter Rollen.

## Neustartbedarf

Nach einem Bootstrap-Update wird mit folgendem Mechanismus geprüft, ob ein Neustart notwendig ist:

```bash
dnf needs-restarting -r
```

Rückgabewert `0` bedeutet, dass kein Neustart benötigt wird. Rückgabewert `1` wird als Neustartbedarf behandelt und nicht als technischer Fehler gewertet.

Standardmäßig erfolgt **kein automatischer Neustart**:

```yaml
package_updates_reboot_if_required: false
```

Damit ein Bootstrap einen erforderlichen Neustart selbst durchführen darf, muss dies ausdrücklich aktiviert werden:

```yaml
package_updates_reboot_if_required: true
package_updates_reboot_timeout: 900
```

Für produktive Systeme sollte ein automatischer Neustart nur aktiviert werden, wenn die Auswirkungen auf Anwendungen, Datenbanken, laufende Jobs und Verfügbarkeit bewertet wurden.

`dnf-automatic` führt durch diese Rolle keine ungeplanten automatischen Reboots aus. Neustarts bleiben ein eigener, kontrollierter Betriebsvorgang.

## Wichtige Variablen

| Variable | Standard | Bedeutung |
|---|---|---|
| `package_updates_strategy` | `security` | Updateumfang |
| `package_updates_apply_on_bootstrap` | `true` | Updates beim Bootstrap anwenden |
| `package_updates_automatic_enabled` | `true` | systemd-Timer aktivieren |
| `package_updates_maintenance_window` | `Sun *-*-* 03:30:00` | Wartungszeitpunkt |
| `package_updates_randomized_delay_sec` | `900` | maximale zufällige Verzögerung |
| `package_updates_reboot_if_required` | `false` | Neustart nach Bootstrap-Updates erlauben |
| `package_updates_reboot_timeout` | `900` | maximale Wartezeit beim kontrollierten Reboot |

## Status und Betrieb

Timer prüfen:

```bash
systemctl status dnf-automatic.timer
systemctl list-timers dnf-automatic.timer
```

Letzte automatische Updateausführung prüfen:

```bash
journalctl -u dnf-automatic.service
```

Neustartbedarf manuell prüfen:

```bash
dnf needs-restarting -r
```

Verfügbare Sicherheitsupdates prüfen:

```bash
dnf updateinfo list --security
```

## Fehlerverhalten

Der Bootstrap bricht kontrolliert ab, wenn:

- eine unbekannte Update-Strategie gesetzt wurde,
- `dnf-automatic` nicht installiert werden kann,
- die Updatekonfiguration nicht geschrieben werden kann,
- ein DNF-Update fehlschlägt,
- die Neustartprüfung einen unerwarteten Rückgabewert liefert,
- der automatische Timer trotz aktivierter Automatik nicht aktiviert werden kann.

Fehlgeschlagene geplante Updates sind über den systemd-Status und das Journal sichtbar und müssen im Betrieb überwacht werden. Automatische Fehlerunterdrückung ist nicht vorgesehen.

## Idempotenz

Konfiguration, Timerzustand und Paketstatus werden zustandsorientiert verwaltet. Ein zweiter Bootstrap-Lauf darf bei unverändertem Zielzustand keine unnötigen Konfigurationsänderungen erzeugen.

Bereits installierte Updates werden von DNF nicht erneut installiert.

## Rollback

Ein Rollback der Automatisierung erfolgt durch Zurücksetzen der Variablen oder Revert des entsprechenden Repository-Commits und anschließende erneute Ausführung des Bootstrap-Playbooks.

Bereits installierte Paketupdates werden **nicht automatisch heruntergestuft**. Ein Paket-Downgrade ist ein separater, risikobehafteter Vorgang und muss anhand des betroffenen Pakets geplant werden.

## Abgrenzung

Nicht Bestandteil dieser Rolle sind:

- automatische Major-Version-Upgrades des Betriebssystems,
- automatische Paket-Downgrades,
- ungeplante automatische Reboots nach zeitgesteuerten Updates,
- Applikations- oder Container-Updates,
- zentrale Patch-Management-Plattformen,
- Monitoring und Alarmierung fehlgeschlagener Update-Läufe.

Diese Themen können später über eigene Rollen oder Epics ergänzt werden.
