# Application-owned Edge Routing

## Ziel

Die Infrastructure verwaltet die gemeinsame Edge-Plattform, nicht die
Routing-Konfiguration einzelner Anwendungen.

Die Plattform stellt bereit:

- Traefik auf den öffentlichen Ports 80/tcp und 443/tcp,
- den ACME-/Let's-Encrypt-Resolver,
- das gemeinsame Docker-Netz `merchfactory-edge`,
- den File Provider für dynamische Traefik-Konfiguration,
- einen kontrollierten Schreibpfad für freigegebene Deployment-Benutzer.

Anwendungs-Repositories verwalten dagegen ihre eigenen Router, Services und
anwendungsspezifischen Middlewares.

## Handoff-Verzeichnis

Traefik beobachtet:

```text
/opt/merchfactory/platform/traefik/config/dynamic/
```

Auf einem kombinierten Development-/Application-Host erhält der dedizierte
Deployment-Benutzer `deploy` per ACL Schreibzugriff auf dieses Verzeichnis.
Die übergeordneten Plattformverzeichnisse bleiben für ihn nur durchquerbar.

Der Benutzer ist bereits Mitglied der Docker-Gruppe und damit technisch
root-äquivalent. Der Dynamic-Config-Zugriff erweitert daher keine bestehende
Host-Sicherheitsgrenze, sondern schafft einen expliziten Deployment-Vertrag.

## Verantwortlichkeiten

Infrastructure:

```text
Internet
   |
   | 80 / 443
   v
Traefik
   |
   +-- ACME / Let's Encrypt
   +-- File Provider
   +-- merchfactory-edge
```

Application Repository:

```text
deployment
   |
   +-- application container -> merchfactory-edge
   |
   +-- app-<service>.yaml
       -> Traefik dynamic config directory
```

Anwendungsrouten sollen einen eindeutigen Dateinamen mit Präfix `app-`
verwenden, zum Beispiel:

```text
app-n8n-development.yaml
app-odoo-development.yaml
app-api-customer-a.yaml
```

Dadurch kollidieren Application-Deployments nicht mit statischen
Infrastructure-Dateien wie `dashboard.yaml`.

## Hot Reload

Traefiks File Provider läuft mit `watch: true`. Application-Deployments
schreiben ihre Konfiguration deshalb atomar in das Dynamic-Config-Verzeichnis.
Ein Neustart des Traefik-Containers ist für normale Route-Änderungen nicht
erforderlich.

## Sicherheitsgrenzen

- Die Anwendung darf nicht den Docker-Socket von Traefik voraussetzen.
- Datenbanken und interne Worker bleiben außerhalb von `merchfactory-edge`.
- Nur der eigentliche HTTP-Service wird an das Edge-Netz angeschlossen.
- TLS-Schlüssel und ACME-State bleiben Eigentum der Infrastructure.
- Application-Repositories dürfen keine Änderungen an der statischen
  Traefik-Konfiguration oder dem ACME-State vornehmen.

## Application-owned service directory provisioning

Infrastructure installs a **generic**, root-owned, argument-validated command
on the application host; the Infrastructure repository no longer lists individual
application names for directory creation:

```bash
sudo -n /usr/local/sbin/merchfactory-provision-service odoo
```

Each application repository invokes this once from its deployment pipeline.
Only a validated service name is accepted, not a path or arbitrary UID. The
command ensures these paths, without deleting or recursively chowning existing
service data:

- `/opt/merchfactory/apps/<service>` – `deploy:deploy`, `0750`;
- `/opt/merchfactory/backups/<service>` – `deploy:deploy`, `0700`;
- `/srv/merchfactory/persistent/<service>` – `deploy:deploy`, `0750`.

The root platform directories remain managed by Infrastructure. Service-specific
subdirectories, Compose, backups and routes are owned by the application repo.
An existing directory with unexpected ownership or mode causes a failure, not
an automatic migration. The trusted `deploy` account is already in the Docker
group and therefore root-equivalent; this explicit sudo command does not create
a new separate host trust boundary.

To install or update this generic contract without running host-wide DNF/kernel
updates, use the **Provision Application Host (manual)** workflow from the
Infrastructure `development` branch after review/merge. It executes only the
`app_deployment_host` Ansible role. It does not deploy any application.
