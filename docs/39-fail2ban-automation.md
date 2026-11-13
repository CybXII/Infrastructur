# Automatisierte Fail2ban-Konfiguration

## Zweck

Die Rolle `fail2ban` schützt den SSH-Dienst und erkennt wiederholt auffällige Quellen über das Recidive-Jail. Sie wird nach SSH-Hardening und Firewall ausgeführt.

## Standardkonfiguration

- Backend: `systemd`
- Ban-Aktion: `firewallcmd-rich-rules`
- SSH-Port: aus `ssh_hardening_port`
- SSH-Jail: 10 Fehlversuche in 10 Minuten, 1 Stunde Ban
- Recidive-Jail: 5 erneute Bans innerhalb eines Tages, 1 Woche Ban
- Logging: `/var/log/fail2ban.log`
- Loopback-Adressen sind von Bans ausgenommen

## Sicherheitsmodell

Fail2ban ergänzt SSH-Hardening und Firewall, ersetzt diese aber nicht. Die Rolle öffnet keine Ports. Bans werden über firewalld Rich Rules umgesetzt.

Externe dynamische Administrator-IP-Adressen werden nicht pauschal in `ignoreip` aufgenommen. Zusätzliche Ausnahmen müssen bewusst über Inventarvariablen gesetzt werden.

## Wichtige Variablen

```yaml
fail2ban_ignoreip:
  - 127.0.0.1/8
  - ::1

fail2ban_sshd_maxretry: 10
fail2ban_sshd_findtime: 10m
fail2ban_sshd_bantime: 1h

fail2ban_recidive_maxretry: 5
fail2ban_recidive_findtime: 1d
fail2ban_recidive_bantime: 1w
```

## Statusprüfung

```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
sudo fail2ban-client status recidive
sudo fail2ban-client get sshd actions
```

Die Wirksamkeit kann von einem separaten Testsystem durch kontrollierte fehlgeschlagene SSH-Anmeldungen geprüft werden. Ein produktiver Administratorzugang darf dabei nicht als Testquelle verwendet werden.

## Idempotenz

Pakete, Konfiguration und Dienstzustand werden deklarativ verwaltet. Ein unveränderter zweiter Lauf darf keine unnötigen Änderungen erzeugen.

## Fehlerverhalten

Der Lauf bricht ab, wenn:

- Variablen ungültig sind,
- EPEL oder Fail2ban nicht installiert werden können,
- `fail2ban-client -t` die Konfiguration ablehnt,
- der Dienst nicht gestartet werden kann,
- ein aktiviertes Jail nicht abgefragt werden kann.

## Rollback

1. Konfigurationsänderung im Repository zurücknehmen.
2. Bootstrap erneut ausführen.
3. `fail2ban-client -t` prüfen.
4. Dienst neu starten.
5. Status der Jails prüfen.

Bei vollständiger Deaktivierung muss vorher bewertet werden, ob ein gleichwertiger Schutz aktiv ist.

## Abgrenzung

Nicht Bestandteil sind zentrale SIEM-Anbindung, automatische Alarmierung, dienstspezifische Custom Filter und providerseitige Blocklisten. Diese Erweiterungen können später ergänzt werden.
