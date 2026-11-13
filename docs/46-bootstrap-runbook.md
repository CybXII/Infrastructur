# Server-Bootstrap Runbook

## Zweck

Dieses Runbook beschreibt den vollständigen v0.4-Server-Bootstrap so, dass ein neuer unterstützter Server ohne zusätzliches Chatwissen vorbereitet, konfiguriert, geprüft und bei Fehlern nachvollziehbar behandelt werden kann.

Der Bootstrap basiert auf Ansible und richtet einen bereits provisionierten AlmaLinux-9- oder Rocky-Linux-9-Server reproduzierbar ein. Die Betriebssysteminstallation bzw. VPS-Erstellung selbst ist nicht Bestandteil des Bootstraps.

## Zielbild

```text
Provider / Administrator
    ↓
frischer unterstützter EL9-Server
    ↓
initialer SSH-Zugang
    ↓
Fresh-Host-Bootstrap
    ↓
verwalteter Benutzer bootstrap
    ↓
gehärteter, reproduzierbarer Server-Sollzustand
    ↓
spätere Änderungen über Managed-Host-Bootstrap
```

Ansible stellt den Serverzustand her. GitHub Actions bzw. der Operator entscheidet, wann und gegen welches Environment ein Lauf ausgeführt wird.

## Unterstützte Zielsysteme

Primär unterstützt:

- AlmaLinux OS 9
- x86_64

Optional kompatibel:

- Rocky Linux 9
- x86_64

Andere Distributionen, andere Major-Versionen und andere Architekturen sind für v0.4 nicht freigegeben. Das Playbook validiert Distribution, Major-Version und Architektur vor den Rollen.

Siehe `docs/33-supported-operating-systems.md`.

## Voraussetzungen auf dem Zielserver

Vor dem ersten Bootstrap müssen mindestens folgende Voraussetzungen erfüllt sein:

1. unterstütztes Betriebssystem ist installiert und gebootet;
2. Server ist per SSH erreichbar;
3. initialer Provider-/Administrationsbenutzer existiert;
4. Public-Key-Authentifizierung funktioniert;
5. initialer Benutzer besitzt erforderliche Root-/sudo-Rechte ohne interaktive Passwortabfrage;
6. Python 3 ist unter `/usr/bin/python3` verfügbar;
7. DNS-Auflösung funktioniert;
8. ausgehender HTTPS-Zugriff zu Paketquellen funktioniert;
9. Systemzeit ist für TLS-Verbindungen hinreichend plausibel;
10. ausreichend freier Speicher ist vorhanden.

Der automatisierte Fresh-Host-Preflight aus Issue #65 prüft diese Voraussetzungen, soweit sie technisch vom Zielhost aus verifizierbar sind.

## Voraussetzungen auf dem Control-/CI-System

Benötigt werden:

- Python 3
- `ansible-core >= 2.17,<2.19`
- Collections aus `ansible/requirements.yml`
- Git Checkout des Infrastructure-Repositories
- SSH Private Key für das Zielsystem
- vertrauenswürdiger `known_hosts`-Eintrag

Installation:

```bash
python3 -m pip install 'ansible-core>=2.17,<2.19'
ansible-galaxy collection install -r ansible/requirements.yml
```

## Repository-Struktur

```text
ansible/
├── ansible.cfg
├── requirements.yml
├── playbooks/
│   └── bootstrap.yml
├── inventories/
│   ├── development/
│   ├── staging/
│   └── production/
└── roles/
    ├── base_installation/
    ├── package_updates/
    ├── system_time/
    ├── user_management/
    ├── storage_preparation/
    ├── system_logging/
    ├── ssh_hardening/
    ├── firewall/
    ├── fail2ban/
    ├── docker_runtime/
    ├── app_deployment_host/
    ├── traefik_edge_host/
    ├── github_runner_host/
    └── docker_cleanup/
```

Die Inventare enthalten keine Secrets.

## Inventar und Hostvariablen

Umgebungsspezifische Inventare liegen unter:

```text
ansible/inventories/development/
ansible/inventories/staging/
ansible/inventories/production/
```

Serverrollen:

- `load_balancers`
- `app_servers`
- `database_servers`
- `monitoring_servers`
- `backup_servers`
- `app_deployment_hosts`
- `edge_hosts`
- `runner_hosts`

Alle Bootstrap-Ziele hängen unter `bootstrap_targets`. Zusätzliche Hostgruppen
aktivieren nach dem Basis-Bootstrap gezielt App-Deployment-, Edge- oder
Runner-Funktionen auf demselben physischen Server.

Gemeinsame nicht geheime Werte gehören in `group_vars`, hostspezifische nicht geheime Abweichungen in `host_vars`.

Siehe `docs/44-server-inventory.md`.

## Secrets und Zugangsdaten

Private Schlüssel, Passwörter, Tokens und andere Geheimnisse dürfen nicht in Inventaren oder Repository-Dateien gespeichert werden.

Namensschema:

```text
DEVELOPMENT_*
STAGING_*
PRODUCTION_*
```

Für die aktuellen Development-Bootstrap-Workflows werden verwendet:

```text
DEVELOPMENT_BOOTSTRAP_TEST_HOST
DEVELOPMENT_BOOTSTRAP_TEST_SSH_KEY
DEVELOPMENT_BOOTSTRAP_TEST_KNOWN_HOSTS
```

Nur der Fresh-Host-Workflow benötigt zusätzlich:

```text
DEVELOPMENT_BOOTSTRAP_TEST_USER
```

Dieser Wert bezeichnet den initialen Provider-Benutzer, bei einem frisch installierten Testhost typischerweise `root`.

Der Managed-Host- und der separate Idempotenzworkflow verbinden sich dagegen direkt als `bootstrap` und verwenden `DEVELOPMENT_BOOTSTRAP_TEST_USER` nicht.

## Manueller Bootstrap mit Ansible

Vor dem Lauf:

```bash
ssh -i /pfad/zum/key user@server
sudo -n true
/usr/bin/python3 --version
```

Inventar prüfen:

```bash
ansible-inventory \
  -i ansible/inventories/development/hosts.yml \
  --graph
```

Verbindung prüfen:

```bash
ansible \
  -i ansible/inventories/development/hosts.yml \
  bootstrap_targets \
  -m ping
```

Bootstrap ausführen:

```bash
ansible-playbook \
  -i ansible/inventories/development/hosts.yml \
  ansible/playbooks/bootstrap.yml
```

Für einen einzelnen Host kann `--limit <host>` verwendet werden. Bei Staging und Production muss das jeweils passende Inventory explizit gewählt werden.

## Reihenfolge des Bootstraps

Das Playbook führt aktuell folgende Rollen aus:

1. `base_installation`
2. `package_updates`
3. `system_time`
4. `user_management`
5. `storage_preparation`
6. `system_logging`
7. `ssh_hardening`
8. `firewall`
9. `fail2ban`
10. `docker_runtime`
11. `node_exporter`
12. `cadvisor`
13. `alloy`
14. `docker_cleanup`

Danach folgen auf explizit zugeordneten Hosts die Rollen
`app_deployment_host`, `traefik_edge_host` und `github_runner_host`.

Die Reihenfolge ist sicherheitsrelevant: Der verwaltete Benutzer und dessen Schlüsselzugang werden hergestellt, bevor SSH-Hardening und Firewall den initialen Zugang einschränken.

## Rollenübersicht

### Base Installation

Installiert und prüft grundlegende Systempakete und Paketvoraussetzungen.

Siehe `docs/34-base-installation.md`.

### Paket- und Updateverwaltung

Verwaltet Sicherheitsupdates, `dnf-automatic`, Wartungsfenster und Neustartbedarf. Automatische Reboots sind standardmäßig deaktiviert.

Siehe `docs/40-package-update-management.md`.

### Zeit, Locale und NTP

Standardwerte:

- Zeitzone `Europe/Berlin`
- Locale `en_US.UTF-8`
- NTP über `chronyd`

Siehe `docs/41-time-locale-ntp.md`.

### Benutzerverwaltung

Verwaltet Benutzer, Gruppen, SSH-Schlüssel und sudoers-Dateien deklarativ.

Siehe `docs/36-user-group-management.md`.

### Storage-Vorbereitung

Erstellt die standardisierten Plattformpfade und kann vorbereitete Dateisysteme mounten. Die Rolle formatiert keine Datenträger.

Siehe `docs/42-storage-directory-preparation.md`.

### SSH-Hardening

Erzwingt den vorgesehenen Public-Key-Zugang und prüft neben der Syntax auch die effektive `sshd -T`-Konfiguration.

Siehe `docs/37-ssh-hardening.md`.

### Firewall

Verwaltet firewalld mit restriktiver Baseline und deklarativen permanenten Freigaben.

Siehe `docs/38-firewall-automation.md`.

### Fail2ban

Konfiguriert SSH- und Recidive-Schutz über firewalld.

Siehe `docs/39-fail2ban-automation.md`.

### Docker Runtime

Installiert gepinnte Docker-Engine-, CLI-, containerd-, Buildx- und Compose-Versionen aus dem offiziellen Docker-CE-Repository.

Siehe `docs/43-docker-runtime.md`.

### Docker Retention / Cleanup

Installiert das rollback-sichere Cleanup-Skript, die zugehörigen Policies sowie einen systemd-Service und wöchentlichen Timer. Beim Bootstrap wird ausschließlich ein Dry-Run ausgeführt; der Timer führt Apply nur bei stabilem Deployment-State aus.

Persistente Volumes sind ausdrücklich vom Cleanup ausgeschlossen.

Siehe `docs/59-docker-retention-cleanup.md`.

## Sicherheitsannahmen

- `known_hosts`-Prüfung bleibt aktiviert;
- Secrets werden nicht committed;
- Root-/Provider-Zugang dient nur dem Fresh-Host-Vertrauensübergang;
- der dauerhaft verwaltete Administrationszugang ist `bootstrap`;
- normale Benutzer werden nicht automatisch zur Docker-Gruppe hinzugefügt;
- der dedizierte CI/CD-Benutzer `deploy` erhält auf `app_deployment_hosts`
  bewusst Docker-Zugriff und ist entsprechend als hochprivilegierter Zugang zu behandeln;
- Docker-Socket wird nicht extern veröffentlicht;
- Storage wird nicht destruktiv formatiert;
- persistente Docker-Volumes werden nicht pauschal bereinigt;
- Applikationscontainer und Service-Netzwerke sind noch nicht Bestandteil von v0.4.

## Fresh-Host-Workflow

Workflow:

```text
.github/workflows/bootstrap-fresh-host.yml
```

Der Workflow ist **ausschließlich manuell über `workflow_dispatch`** startbar. Er läuft weder bei `push` noch bei `pull_request`.

Für einen echten Lauf müssen gelten:

1. der zu prüfende Branch/Ref wird beim manuellen Start bewusst ausgewählt, für die Development-Abnahme `development`;
2. `DEVELOPMENT_BOOTSTRAP_FRESH_HOST_ENABLED=true`;
3. alle vier Fresh-Host-Secrets sind gesetzt;
4. der Zielhost ist tatsächlich frisch und besteht den Preflight.

Benötigte Secrets:

```text
DEVELOPMENT_BOOTSTRAP_TEST_HOST
DEVELOPMENT_BOOTSTRAP_TEST_USER
DEVELOPMENT_BOOTSTRAP_TEST_SSH_KEY
DEVELOPMENT_BOOTSTRAP_TEST_KNOWN_HOSTS
```

Die Variable wird nur für einen bewusst freigegebenen Fresh-Host-Test auf `true` gesetzt. Nach Abschluss wird sie wieder auf:

```text
DEVELOPMENT_BOOTSTRAP_FRESH_HOST_ENABLED=false
```

gesetzt. Selbst bei `true` startet der Workflow nicht automatisch; die Variable ist eine zusätzliche Schutzschicht innerhalb des manuell ausgelösten Jobs.

### Fresh-Host-Ablauf

```text
manueller workflow_dispatch
    ↓
Fresh-Host-Preflight ohne Änderungen
    ↓
erster Bootstrap mit initialem Provider-Benutzer
    ↓
Benutzer bootstrap vorhanden
    ↓
Root-/Passwortzugang gehärtet
    ↓
Reconnect als bootstrap
    ↓
zweiter vollständiger Bootstrap
    ↓
changed == 0
    ↓
Sicherheits- und Funktionschecks
    ↓
CI-Artefakte und Job Summary
```

Der Preflight prüft unter anderem Zielsystem, initiale Identität, freien Speicher, Paketquellen, DNS/HTTPS sowie den erwarteten frischen Zustand ohne verwalteten Benutzer und Docker CE.

Die Abschlussprüfung umfasst unter anderem:

- sudo des verwalteten Benutzers,
- kritische Dienste,
- effektive SSH-Hardening-Werte,
- SELinux `Enforcing`,
- Firewall-Baseline,
- Fail2ban-Jails,
- Zeitsynchronisation,
- Storage-Verzeichnisse,
- Docker-Datenverzeichnis,
- Docker-Daemon und Docker Compose.

Der erfolgreiche v0.4-Abnahmelauf ist in `docs/47-v0-4-review.md` dokumentiert.

## Managed-Host-Workflow

Workflow:

```text
.github/workflows/bootstrap-managed-host.yml
```

Der Managed-Host-Pfad ist für bereits provisionierte Server vorgesehen. Er verbindet sich **direkt als `bootstrap`** und benötigt keinen initialen Provider-/Root-Zugang mehr.

Trigger:

- manuell über `workflow_dispatch`;
- bei relevanten Pushes auf `development`.

Der Job wird nur ausgeführt, wenn:

```text
DEVELOPMENT_BOOTSTRAP_MANAGED_HOST_ENABLED=true
```

Der Workflow:

1. erzeugt aus Host und Bootstrap-Key ein vollständiges deklaratives Managed-Host-Inventar;
2. prüft die Verbindung als `bootstrap`;
3. führt den vollständigen Bootstrap aus;
4. führt denselben Bootstrap ein zweites Mal aus und verlangt `changed=0`;
5. führt die Sicherheits- und Funktionschecks aus;
6. speichert die Testzusammenfassung als CI-Artefakt.

Dieser Pfad ist der reguläre Development-Updateweg nach der einmaligen Fresh-Host-Provisionierung.

## Separater Idempotenzworkflow

Workflow:

```text
.github/workflows/bootstrap-idempotency.yml
```

Dieser Workflow wird ausschließlich manuell gestartet und beginnt ebenfalls direkt als `bootstrap`. Details siehe `docs/45-bootstrap-idempotency.md`.

## Nach dem Lauf prüfen

Operative Basischecks:

```bash
systemctl is-active sshd
systemctl is-active firewalld
systemctl is-active fail2ban
systemctl is-active chronyd
systemctl is-active docker
systemctl is-enabled merchfactory-docker-cleanup.timer
systemctl list-timers merchfactory-docker-cleanup.timer
chronyc tracking
firewall-cmd --list-all
fail2ban-client status
docker --version
docker compose version
docker info
```

Für SSH-Hardening zusätzlich:

```bash
sudo sshd -T
```

## CI-Artefakte

Fresh Host speichert für 14 Tage unter anderem:

```text
artifacts/bootstrap-fresh-host/first-run.json
artifacts/bootstrap-fresh-host/second-run.json
artifacts/bootstrap-fresh-host/preflight.log
artifacts/bootstrap-fresh-host/verification.log
artifacts/bootstrap-fresh-host/summary.txt
```

Managed Host und Idempotenz verwenden die Ausgaben aus `scripts/test-bootstrap-idempotency.sh`.

Private Schlüssel und Secret-Werte dürfen nicht als Artifact gespeichert werden.

## Troubleshooting

### Host nicht erreichbar

```bash
ssh -vvv user@host
```

Prüfen:

- DNS/IP,
- Provider-Firewall bzw. Security Group,
- SSH-Port,
- Private/Public-Key-Paar,
- `known_hosts`.

### `Permission denied (publickey)`

Prüfen:

- korrekten Benutzer,
- korrekten Private Key,
- `authorized_keys`,
- Rechte von `.ssh` und `authorized_keys`,
- unveränderte mehrzeilige CI-Secrets.

### `Host key verification failed`

Host-Key-Prüfung nicht deaktivieren. Bei Neuinstallation ändert sich der Host-Key; den neuen Fingerprint unabhängig prüfen und `DEVELOPMENT_BOOTSTRAP_TEST_KNOWN_HOSTS` aktualisieren.

### `sudo` / `become` schlägt fehl

```bash
sudo -n true
```

Der Befehl muss ohne Passwortabfrage erfolgreich sein.

### Zielsystem wird abgelehnt

```bash
cat /etc/os-release
uname -m
```

Für v0.4 werden AlmaLinux 9 bzw. optional Rocky Linux 9 auf x86_64 akzeptiert.

### Paketinstallation schlägt fehl

```bash
dnf repolist
dnf makecache
```

Zusätzlich DNS, HTTPS und Systemzeit prüfen.

### Chrony synchronisiert nicht

```bash
systemctl status chronyd
chronyc sources -v
chronyc tracking
```

### SSH-Verbindung nach Hardening verloren

Provider-Konsole bzw. Out-of-Band-Zugang verwenden. Nicht das Hardening pauschal abschalten.

```bash
sshd -t
sshd -T
systemctl status sshd
```

### Firewall blockiert Verkehr

```bash
firewall-cmd --get-active-zones
firewall-cmd --list-all
```

Provider- und Host-Firewall getrennt prüfen. Manuelle Anwendungsports sind kein dauerhafter Ersatz für deklarative Infrastrukturkonfiguration.

### Fail2ban startet nicht

```bash
systemctl status fail2ban
fail2ban-client -t
journalctl -u fail2ban
```

### Docker startet nicht

```bash
python3 -m json.tool /etc/docker/daemon.json
systemctl status docker
journalctl -u docker
docker info
```

## Rollback-Grundsatz

Der Bootstrap ist Infrastructure as Code. Änderungen werden primär durch Git-Revert oder einen korrigierenden Infrastructure-PR zurückgenommen und danach erneut über den vorgesehenen Promotion-/Deploymentpfad angewendet.

```text
fehlerhafte Infrastrukturänderung
    ↓
Git-Revert / korrigierender PR
    ↓
Development validieren
    ↓
Staging validieren
    ↓
Production ausrollen
```

Ein Rollback darf keine impliziten destruktiven Datenoperationen auslösen.

Bei SSH-/Firewall-Lockout ist die Provider-Konsole der Recovery-Weg. Storage wird nicht automatisch formatiert. Benutzer-/Schlüsseländerungen müssen mindestens einen verifizierten administrativen Zugang erhalten.

## Verbotene Schnelllösungen

Nicht als Standard-Fehlerbehebung verwenden:

- Host-Key-Prüfung deaktivieren;
- Firewall vollständig abschalten;
- SSH-Passwortauthentifizierung dauerhaft reaktivieren;
- Benutzer pauschal zur Docker-Gruppe hinzufügen;
- `chmod 777` auf Plattformpfade;
- `docker system prune --volumes` ungeprüft ausführen;
- Datenträger automatisch neu formatieren;
- Secrets in Inventar- oder Repository-Dateien schreiben.

## CI/CD und Environments

Regulärer Promotion-Flow:

```text
development
    ↓
staging
    ↓
main / production
```

Jede Umgebung besitzt ein eigenes Inventory und eigene Secrets. Production darf nicht implizit als Standardziel verwendet werden.

## Dokumentationsübersicht v0.4

- `docs/33-supported-operating-systems.md`
- `docs/34-base-installation.md`
- `docs/36-user-group-management.md`
- `docs/37-ssh-hardening.md`
- `docs/38-firewall-automation.md`
- `docs/39-fail2ban-automation.md`
- `docs/40-package-update-management.md`
- `docs/41-time-locale-ntp.md`
- `docs/42-storage-directory-preparation.md`
- `docs/43-docker-runtime.md`
- `docs/44-server-inventory.md`
- `docs/45-bootstrap-idempotency.md`
- `docs/47-v0-4-review.md`

## Abgrenzung

Nicht Bestandteil von v0.4 sind insbesondere:

- automatische VPS-/VM-Provisionierung,
- Betriebssysteminstallation,
- produktive Applikationscontainer,
- hochverfügbare Reverse-Proxy-Topologien,
- endgültige Multi-Host-Netzwerksegmentierung,
- persistente Applikationsdatenbanken und HA,
- zentrale Monitoring-/Alerting-Plattform,
- Multi-Site-Failover.

Diese Themen folgen in späteren Infrastrukturversionen, insbesondere Epic #67 / v0.5.

## Referenzen

- Epic #51
- Issue #63
- Issue #65
- Issue #66
- Epic #67
- `.github/workflows/bootstrap-fresh-host.yml`
- `.github/workflows/bootstrap-managed-host.yml`
- `.github/workflows/bootstrap-idempotency.yml`
- `scripts/create-bootstrap-test-inventories.py`
- `scripts/test-bootstrap-fresh-host.sh`
- `scripts/test-bootstrap-idempotency.sh`
