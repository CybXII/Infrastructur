# Automatisierte Benutzer- und Gruppenverwaltung

## Zweck

Die Ansible-Rolle `user_management` verwaltet Administrations-, Service- und Betriebsbenutzer reproduzierbar. Gruppen, Benutzer, zusätzliche Gruppenmitgliedschaften, SSH-Schlüssel und Sudo-Regeln werden deklarativ über Inventarvariablen beschrieben.

Die Rolle setzt voraus, dass die Basisinstallation erfolgreich ausgeführt wurde.

## Sicherheitsmodell

- Benutzer werden standardmäßig mit gesperrtem Passwort angelegt.
- Administrativer Zugriff erfolgt über SSH-Schlüssel.
- Autorisierte Schlüssel werden standardmäßig exklusiv verwaltet.
- Sudo-Regeln werden als einzelne Dateien unter `/etc/sudoers.d` abgelegt.
- Jede Sudoers-Datei wird vor dem Schreiben mit `visudo` validiert.
- Zu entfernende Benutzer werden ausdrücklich über eine separate Liste angegeben.
- Home-Verzeichnisse entfernter Benutzer bleiben standardmäßig erhalten.

## Abhängigkeit installieren

Vor dem Bootstrap:

```bash
ansible-galaxy collection install -r ansible/requirements.yml
```

Die Rolle verwendet `ansible.posix.authorized_key`.

## Variablen

### Gruppen

```yaml
user_management_groups:
  - name: merchfactory-admins
    system: false

  - name: merchfactory-services
    system: true
```

### Benutzer

```yaml
user_management_users:
  - name: deploy
    primary_group: merchfactory-admins
    groups:
      - wheel
    shell: /bin/bash
    create_home: true
    password_lock: true
    authorized_keys:
      - "ssh-ed25519 AAAA... deployment-key"
    authorized_keys_exclusive: true
    sudo: true
    sudo_nopasswd: true
    sudo_commands:
      - /usr/bin/systemctl
      - /usr/bin/docker

  - name: app-service
    primary_group: merchfactory-services
    shell: /sbin/nologin
    create_home: false
    system: true
    password_lock: true
    sudo: false
```

SSH-Schlüssel in der Dokumentation sind ausschließlich Platzhalter. Reale Schlüssel werden über sichere Inventar- oder Secret-Quellen bereitgestellt und nicht fest im Repository gespeichert.

### Zugänge entziehen

```yaml
user_management_absent_users:
  - ehemaliger-benutzer

user_management_remove_home_for_absent_users: false
```

Die Entfernung löscht zunächst zugehörige verwaltete Sudo-Regeln und entfernt anschließend den Benutzer. Das Home-Verzeichnis wird nur bei ausdrücklicher Aktivierung gelöscht.

## Unterstützte Benutzerfelder

| Feld | Standard | Bedeutung |
|---|---|---|
| `name` | Pflicht | Benutzername |
| `uid` | automatisch | feste UID, sofern notwendig |
| `primary_group` | Systemstandard | primäre Gruppe |
| `groups` | `[]` | vollständige Liste zusätzlicher Gruppen |
| `shell` | `/bin/bash` | Login-Shell |
| `home` | automatisch | benutzerdefiniertes Home-Verzeichnis |
| `create_home` | `true` | Home-Verzeichnis erstellen |
| `system` | `false` | Systembenutzer anlegen |
| `password_lock` | `true` | Passwort-Login sperren |
| `authorized_keys` | `[]` | erlaubte öffentliche SSH-Schlüssel |
| `authorized_keys_exclusive` | `true` | nicht deklarierte Schlüssel entfernen |
| `sudo` | `false` | eigene Sudoers-Datei verwalten |
| `sudo_nopasswd` | `false` | `NOPASSWD` aktivieren |
| `sudo_commands` | `['ALL']` | erlaubte Sudo-Befehle |

## Idempotenz

Ansible verwaltet Benutzer, Gruppen, Dateien und SSH-Schlüssel zustandsorientiert. Ein zweiter Lauf darf keine fachlich unnötigen Änderungen erzeugen.

Bei zusätzlichen Gruppen gilt `append: false`. Die deklarierte Liste ist daher der gewünschte vollständige Zustand und entfernt nicht mehr deklarierte zusätzliche Gruppenmitgliedschaften.

## Kontrolle und Fehlerverhalten

Der Lauf bricht kontrolliert ab, wenn:

- Benutzer- oder Gruppendefinitionen keine Listen sind,
- eine benötigte Gruppe fehlt,
- ein Benutzer nicht angelegt werden kann,
- ein SSH-Schlüssel ungültig ist,
- `visudo` eine Sudo-Regel ablehnt,
- Besitz- oder Dateiberechtigungen nicht gesetzt werden können.

Fehler werden nicht ignoriert.

## Rollback

Ein fachlicher Rollback erfolgt durch Rücknahme der betreffenden Inventardefinition und erneute Ausführung des Playbooks.

Benutzer werden nicht automatisch entfernt, nur weil sie aus `user_management_users` verschwinden. Für einen kontrollierten Entzug müssen sie ausdrücklich in `user_management_absent_users` aufgenommen werden. Dadurch werden versehentliche Aussperrungen vermieden.

## Abgrenzung

Nicht Bestandteil dieser Rolle sind:

- Änderung globaler SSH-Daemon-Einstellungen,
- Firewall-Regeln,
- Fail2ban,
- zentrale Identitätsdienste wie LDAP oder FreeIPA,
- automatische Rotation privater SSH-Schlüssel,
- Secret-Speicherung im Repository.

Diese Themen werden separat umgesetzt oder geplant.
