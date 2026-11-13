# Serverinventar und Hostvariablen

## Zweck

Die Inventarstruktur trennt die drei Umgebungen `development`, `staging` und `production` und bildet Serverrollen deklarativ über Ansible-Gruppen ab. Dadurch können mehrere Server mit gleichem Rollenprofil sowie hostspezifische Abweichungen verwaltet werden, ohne Verbindungsgeheimnisse im Repository zu speichern.

## Verzeichnisstruktur

```text
ansible/
└── inventories/
    ├── development/
    │   ├── hosts.yml
    │   ├── group_vars/
    │   │   └── all.yml
    │   └── host_vars/              # bei Bedarf anlegen
    ├── staging/
    │   ├── hosts.yml
    │   ├── group_vars/
    │   │   └── all.yml
    │   └── host_vars/              # bei Bedarf anlegen
    ├── production/
    │   ├── hosts.yml
    │   ├── group_vars/
    │   │   └── all.yml
    │   └── host_vars/              # bei Bedarf anlegen
    └── host_vars/
        └── example-host.yml.example
```

Die Dateien `group_vars/all.yml` enthalten ausschließlich gemeinsame, nicht geheime Variablen der jeweiligen Umgebung. Hostspezifische Abweichungen gehören in `<environment>/host_vars/<inventory-hostname>.yml`.

## Serverrollen

Jedes Umgebungsinventar definiert dieselben logischen Gruppen:

- `load_balancers`
- `app_servers`
- `database_servers`
- `monitoring_servers`
- `backup_servers`

Alle diese Gruppen sind Kinder von `bootstrap_targets`. Dadurch bleibt das bestehende Bootstrap-Playbook unverändert auf `hosts: bootstrap_targets` ausgerichtet, kann aber später beliebig viele Hosts und Rollen aufnehmen.

Beispiel für zwei App-Server und einen Datenbankserver:

```yaml
all:
  children:
    bootstrap_targets:
      children:
        load_balancers: {}
        app_servers: {}
        database_servers: {}
        monitoring_servers: {}
        backup_servers: {}

    app_servers:
      hosts:
        app-01:
          ansible_host: 10.20.10.11
        app-02:
          ansible_host: 10.20.10.12

    database_servers:
      hosts:
        db-01:
          ansible_host: 10.20.20.11
```

IP-Adressen und DNS-Namen sind keine Authentifizierungsgeheimnisse und können grundsätzlich im Inventar verwaltet werden. Ob interne Adressierung öffentlich im Repository stehen soll, ist trotzdem eine organisatorische Entscheidung. Zugangsdaten gehören niemals hierher.

## Gemeinsame Variablen

Umgebungsweite Werte werden unter `group_vars/all.yml` gepflegt:

```yaml
merchfactory_environment: production
ansible_python_interpreter: /usr/bin/python3
```

Rollenbezogene gemeinsame Variablen können später bei Bedarf in zusätzlichen Dateien wie diesen abgelegt werden:

```text
group_vars/app_servers.yml
group_vars/database_servers.yml
group_vars/load_balancers.yml
```

Damit gilt die Reihenfolge:

```text
Role Defaults
    ↓
Environment group_vars/all.yml
    ↓
Role-specific group_vars/<group>.yml
    ↓
Host-specific host_vars/<host>.yml
```

Hostspezifische Werte sollen nur verwendet werden, wenn ein einzelner Server tatsächlich vom Gruppenstandard abweichen muss.

## Hostspezifische Variablen

Beispiel:

```text
ansible/inventories/production/host_vars/app-01.yml
```

```yaml
---
ansible_host: 10.20.10.11
ansible_port: 22

storage_mounts:
  - path: /srv/merchfactory/persistent
    src: /dev/disk/by-id/example-device
    fstype: xfs
    opts: defaults,noatime
    state: mounted
```

Ein nicht automatisch geladenes Muster liegt unter `ansible/inventories/host_vars/example-host.yml.example`.

## Secrets und Verbindungsdaten

Folgende Werte dürfen **nicht** in `hosts.yml`, `group_vars` oder `host_vars` committed werden:

- private SSH-Schlüssel,
- SSH-Passwörter,
- sudo-/become-Passwörter,
- API-Tokens,
- Registry-Passwörter,
- Vault-Passwörter,
- TLS-Private-Keys,
- sonstige Zugangsdaten.

Diese Werte werden durch die CI/CD-Ebene bzw. GitHub Environment Secrets bereitgestellt. Das bestehende Namensschema bleibt:

```text
DEVELOPMENT_*
STAGING_*
PRODUCTION_*
```

Beispielsweise kann GitHub Actions den SSH-Benutzer und einen temporär bereitgestellten privaten Schlüssel an Ansible übergeben, ohne den Schlüssel im Inventory zu speichern.

## Inventar auswählen

Development:

```bash
ansible-playbook \
  -i ansible/inventories/development/hosts.yml \
  ansible/playbooks/bootstrap.yml
```

Staging:

```bash
ansible-playbook \
  -i ansible/inventories/staging/hosts.yml \
  ansible/playbooks/bootstrap.yml
```

Production:

```bash
ansible-playbook \
  -i ansible/inventories/production/hosts.yml \
  ansible/playbooks/bootstrap.yml
```

Die CI/CD-Pipeline muss das Inventar explizit anhand der Zielumgebung auswählen. Es wird bewusst kein globales Production-Inventar als Default in `ansible.cfg` hinterlegt.

## Inventar prüfen

Vor einem Deployment kann die aufgelöste Struktur ohne Verbindung zu den Zielservern geprüft werden:

```bash
ansible-inventory \
  -i ansible/inventories/development/hosts.yml \
  --graph
```

und vollständig aufgelöst:

```bash
ansible-inventory \
  -i ansible/inventories/development/hosts.yml \
  --list
```

Solange noch keine realen Hosts eingetragen sind, bleiben die Gruppen absichtlich leer. Das verhindert, dass Beispieladressen versehentlich als Deployment-Ziele verwendet werden.

## Multi-Server-Erweiterung

Ein neuer Server wird später nicht durch eine neue Pipeline implementiert, sondern primär durch einen Inventareintrag einer vorhandenen Rolle. Beispiel:

```yaml
app_servers:
  hosts:
    app-01:
      ansible_host: 10.20.10.11
    app-02:
      ansible_host: 10.20.10.12
    app-03:
      ansible_host: 10.20.10.13
```

Alle drei Hosts gehören dadurch zum selben Rollenprofil. Abweichungen werden nur über `host_vars` ergänzt, nicht durch Kopieren eigener Playbooks.

## Abgrenzung

Dieser Task definiert die Inventar- und Variablenstruktur. Er legt noch keine realen Serveradressen, SSH-Zugangsdaten oder produktiven Secrets fest. Die tatsächliche Belegung der Inventare erfolgt, sobald konkrete Hosts für Development, Staging und Production bereitgestellt sind.
