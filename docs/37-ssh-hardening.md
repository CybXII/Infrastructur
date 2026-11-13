# Automatisiertes SSH-Hardening

## Zweck

Die Rolle `ssh_hardening` setzt eine verbindliche SSH-Sicherheitsbaseline für AlmaLinux OS 9 und Rocky Linux 9 um. Sie wird nach der Benutzer- und Schlüsselverwaltung ausgeführt, damit vor der Deaktivierung unsicherer Zugänge mindestens ein verwalteter schlüsselbasierter Zugang vorhanden ist.

## Sicherheitsbaseline

Standardmäßig gelten:

- Root-Login deaktiviert,
- Passwort-Login deaktiviert,
- Keyboard-Interactive-Login deaktiviert,
- Public-Key-Authentifizierung aktiviert,
- leere Passwörter verboten,
- X11-, TCP- und Agent-Forwarding deaktiviert,
- maximal drei Authentifizierungsversuche,
- 30 Sekunden Login-Frist,
- inaktive Verbindungen werden kontrolliert beendet,
- DNS-Lookups durch `sshd` deaktiviert.

Die Werte werden in der verwalteten Drop-in-Datei `/etc/ssh/sshd_config.d/00-merchfactory-hardening.conf` abgelegt. Die frühe Sortierung ist bewusst gewählt: OpenSSH verwendet für viele globale Direktiven den ersten wirksamen Wert. Distributionseigene Drop-ins dürfen deshalb die Merchfactory-Sicherheitsbaseline nicht vorwegnehmen. Die Hauptdatei `/etc/ssh/sshd_config` wird nicht vollständig ersetzt.

Die frühere Datei `/etc/ssh/sshd_config.d/60-merchfactory-hardening.conf` wird bei einem Lauf automatisch entfernt. Dadurch bleibt auch ein bereits aufgebauter Host nach der Umstellung eindeutig konfiguriert.

## Aussperrungsschutz

Wenn Passwort-Login deaktiviert ist, prüft die Rolle vor Änderungen, ob in `user_management_users` mindestens ein Benutzer mit einem öffentlichen SSH-Schlüssel definiert ist. Fehlt ein solcher Zugang, bricht der Lauf ohne Änderung der SSH-Konfiguration ab.

Der erstmalige produktive Lauf muss in einer bestehenden administrativen Sitzung erfolgen. Eine zweite Sitzung sollte vor dem Schließen der ersten Verbindung getestet werden.

## Validierung und Reload

Die neue Drop-in-Datei wird vor dem Schreiben mit `sshd -t -f` validiert. Anschließend wird die vollständige Konfiguration mit `sshd -t` geprüft und `sshd` kontrolliert neu geladen. Ein Neustart des Dienstes ist nicht erforderlich.

Nach dem Reload liest die Rolle zusätzlich die tatsächlich effektive Konfiguration mit `sshd -T` aus. Die sicherheitsrelevanten Sollwerte werden einzeln gegen diese Ausgabe geprüft. Dadurch reicht eine syntaktisch gültige Drop-in-Datei nicht mehr aus: Wenn ein früher geladenes Distributions-Drop-in einen Wert übersteuert, schlägt der Bootstrap kontrolliert fehl.

Abschließend wird bestätigt, dass der Dienst weiterhin aktiv ist.

## Wichtige Variablen

| Variable | Standard | Bedeutung |
|---|---:|---|
| `ssh_hardening_port` | `22` | SSH-Port |
| `ssh_hardening_permit_root_login` | `no` | Root-Login-Regel |
| `ssh_hardening_password_authentication` | `false` | Passwort-Login |
| `ssh_hardening_kbd_interactive_authentication` | `false` | interaktive Passwortabfrage |
| `ssh_hardening_pubkey_authentication` | `true` | Public-Key-Anmeldung |
| `ssh_hardening_allow_users` | `[]` | optionale Benutzer-Allowlist |
| `ssh_hardening_allow_groups` | `[]` | optionale Gruppen-Allowlist |
| `ssh_hardening_allow_tcp_forwarding` | `false` | TCP-Forwarding |
| `ssh_hardening_allow_agent_forwarding` | `false` | Agent-Forwarding |
| `ssh_hardening_dropin_file` | `/etc/ssh/sshd_config.d/00-merchfactory-hardening.conf` | priorisierte verwaltete Drop-in-Datei |

Leere Allowlisten erzeugen keine `AllowUsers`- oder `AllowGroups`-Direktive. Dadurch werden nur ausdrücklich gesetzte Einschränkungen wirksam.

## Portänderungen

Eine Änderung des SSH-Ports darf erst erfolgen, nachdem Firewall, SELinux-Portkontext, Monitoring und externe Deployment-Zugänge angepasst wurden. Diese Abhängigkeiten werden in den folgenden Firewall- und Deployment-Issues umgesetzt. Der Standard bleibt deshalb Port 22.

## Idempotenz

Die Rolle verwendet zustandsorientierte Ansible-Module. Bei unveränderten Variablen darf ein zweiter Lauf keine fachlich unnötigen Änderungen oder erneuten Reloads auslösen.

Die Migration vom früheren `60-...`-Drop-in auf `00-...` erzeugt beim ersten Lauf erwartungsgemäß eine einmalige Änderung. Danach muss der Zustand idempotent sein.

## Fehlerverhalten

Der Lauf bricht kontrolliert ab, wenn:

- Variablen ungültig sind,
- kein schlüsselbasierter Zugang definiert ist,
- OpenSSH nicht installiert oder startbar ist,
- die Drop-in-Konfiguration ungültig ist,
- die Gesamtprüfung mit `sshd -t` fehlschlägt,
- die effektive Ausgabe von `sshd -T` nicht dem deklarativen Sollzustand entspricht,
- der Dienst nach dem Reload nicht aktiv ist.

Fehler werden nicht ignoriert.

## Rollback

Bei einem Konfigurationsproblem:

1. bestehende administrative Sitzung offen lassen,
2. Drop-in-Datei entfernen oder auf den letzten freigegebenen Stand zurücksetzen,
3. `/usr/sbin/sshd -t` ausführen,
4. `systemctl reload sshd` ausführen,
5. `/usr/sbin/sshd -T` gegen die erwarteten Werte prüfen,
6. neue Anmeldung in einer separaten Sitzung prüfen.

Ein Repository-Rollback erfolgt durch Revert des zugehörigen Commits und erneute Ausführung des Bootstrap-Playbooks.

## Abgrenzung

Nicht Bestandteil dieser Rolle sind:

- Firewall-Freigaben,
- Fail2ban,
- VPN- oder Bastion-Zugänge,
- Host-Schlüsselrotation,
- zentrale Identitätsdienste,
- automatische Änderung externer DNS- oder Provider-Firewalls.
