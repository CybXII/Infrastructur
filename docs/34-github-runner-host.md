# GitHub-Runner-Host auswählen

Die Runner-Plattform aus `CybXII/GitHub-Runners` wird nicht automatisch auf
jedem Server installiert. Pro Inventory kann gezielt **ein** bereits
verwalteter VPS über die Gruppe `runner_hosts` ausgewählt werden.

Die Runner-Plattform ist dabei eine Docker-Anwendung. Der ausgewählte Host darf
gleichzeitig andere Rollen besitzen. Ein dedizierter Runner-VPS ist später eine
stärkere Sicherheitsgrenze, aber keine technische Voraussetzung.

## Auswahl im Inventory

Der gewünschte Server wird zusätzlich der Gruppe `runner_hosts` zugeordnet.

Beispiel:

```yaml
all:
  children:
    bootstrap_targets:
      children:
        app_servers: {}
        runner_hosts: {}

    app_servers:
      hosts:
        app-01:
          ansible_host: 192.0.2.10

    runner_hosts:
      hosts:
        app-01:
          ansible_host: 192.0.2.10
```

In diesem Beispiel läuft die Runner-Plattform als zusätzliche Docker-Anwendung
auf `app-01`.

Alternativ kann später ein eigener Host verwendet werden:

```yaml
runner_hosts:
  hosts:
    runner-01:
      ansible_host: 192.0.2.20
```

Der Bootstrap bricht aktuell absichtlich ab, wenn in einem Inventory mehr als
ein `runner_host` ausgewählt wurde. Mehrere GitHub-Scopes werden von einem
Controller auf diesem Host verwaltet; mehrere konkurrierende Controller auf
verschiedenen Hosts werden dadurch vermieden.

## Runner-Modell

Die Runner-Plattform ist Multi-Scope-fähig. Der Development-Host überwacht
aktuell diese GitHub-Scopes:

```text
https://github.com/Merchfactory
https://github.com/CybXII/n8n-deployment
```

Beide verwenden das Routing-Label:

```text
ephemeral-linux
```

GitHub-Organisationen können organisationsweit angebunden werden. Private
Repositories eines persönlichen GitHub-Accounts müssen dagegen einzeln als
Repository-Scope eingetragen werden.

`MAX_RUNNERS=2` ist ein globales Limit über alle konfigurierten Scopes
zusammen. Im Multi-Scope-Betrieb bleibt `MIN_RUNNERS=0`, damit im Leerlauf
keine Job-Runner laufen.

Im Leerlauf läuft nur der Controller mit einem Listener je GitHub-Scope. Bei
einem GitHub-Job werden dynamisch erzeugt:

```text
Controller
   |
   +-- ephemeral Runner
   |
   +-- eigener Docker-in-Docker Sidecar
```

Nach dem Job werden die temporären Container wieder entfernt.

Damit kann derselbe Runner-Pool normale CI-Jobs, Docker-/Compose-Tests und
Deployments ausführen.

## Secret

Das private Runner-Repository und die Runner-Registrierungen benötigen
zunächst einen GitHub-Token. Dieser wird **nicht** im Inventory gespeichert.

Der Token muss Zugriff auf alle konfigurierten GitHub-Scopes besitzen. Ist ein
zusätzlicher Scope vorübergehend nicht autorisiert oder nicht erreichbar,
bleiben die anderen Scopes aktiv; der betroffene Scope wird vom Controller mit
Backoff erneut versucht.

Vor dem Ansible-Aufruf muss er als Umgebungsvariable verfügbar sein:

```bash
export RUNNER_TOKEN='...'
```

In GitHub Actions soll derselbe Wert als Repository Secret
injiziert werden. Die Rolle schreibt ihn ausschließlich in:

```text
/opt/merchfactory/github-runners/.env
```

mit Dateimodus `0600`.

Langfristig ist GitHub-App-Authentifizierung vorgesehen.

## Bootstrap-Ablauf

1. Neue Infrastruktur verwendet zunächst GitHub-hosted Actions.
2. Der ausgewählte Host durchläuft den normalen Infrastructure-Bootstrap.
3. Docker, Hardening und Monitoring werden wie bei anderen verwalteten Hosts eingerichtet.
4. Nur auf dem Host in `runner_hosts` wird `CybXII/GitHub-Runners` deployed.
5. Controller und universelles Runner-Image werden gebaut.
6. Der Controller registriert je GitHub-Scope einen Listener/Scale-Set mit dem
   Routing-Label `ephemeral-linux`.
7. Ein Smoke-Test validiert den Runner.
8. Danach kann `RUNNER_MODE` von `github-hosted` auf `self-hosted` umgestellt werden.

Der eigentliche Runner-Switch bleibt bewusst ein separater Schritt. Bei einem
Ausfall der eigenen Runner-Plattform kann dadurch wieder auf GitHub-hosted
Runner zurückgeschaltet werden.

## Netzwerk und spätere VPN-Härtung

Für die Runner-Plattform müssen keine eingehenden öffentlichen Ports geöffnet
werden. Der Controller verbindet sich ausgehend mit GitHub.

Später sollen Deployments über das interne VPN zu Development-, Staging- und
Production-Hosts erfolgen. Dadurch müssen administrative Dienste der
Zielserver nicht öffentlich für die Runner erreichbar sein.

## Development-Testhost als Runner-Host

Der bestehende private Development-Server, der bereits über
`Bootstrap Managed Host` aktualisiert wird, kann zusätzlich die Runner-Plattform
betreiben.

Dafür verwendet der Workflow die GitHub-Variable:

```text
DEVELOPMENT_RUNNER_HOST_ENABLED
```

Solange sie nicht exakt auf `true` gesetzt ist, bleibt das bestehende Verhalten
unverändert und der Development-Host wird nicht der Gruppe `runner_hosts`
zugeordnet.

Die aktuelle Runner-Plattform unterstützt mehrere GitHub-Scopes. Für den
Development-Host sind `Merchfactory` und `CybXII/n8n-deployment`
konfiguriert.

1. im Repository `Merchfactory/Infrastructure` das Repository Secret
   `RUNNER_TOKEN` mit Zugriff auf alle konfigurierten Scopes hinterlegen,
2. `DEVELOPMENT_RUNNER_HOST_ENABLED=true` setzen,
3. `Bootstrap Managed Host` erneut starten.

Der erzeugte Managed-Host-Inventarbaum enthält dann denselben Host in
`bootstrap_targets` und `runner_hosts`. Der normale Bootstrap bleibt erhalten;
anschließend wird zusätzlich die Runner-Plattform auf diesem Server installiert
beziehungsweise aktualisiert.

Die Runner-Rolle verfolgt den tatsächlich installierten Commit in
`/opt/merchfactory/github-runners/.source-sha` und baut beziehungsweise startet
die Plattform nur neu, wenn sich Quellstand oder Konfiguration geändert haben.
Dadurch bleibt der bestehende Bootstrap-Idempotenztest auch mit aktiviertem
Runner-Host sinnvoll.

### SSH-Deployment-User

Der Managed-Host-Workflow führt neben dem administrativen Benutzer
`bootstrap` auch den App-Deployment-Benutzer `deploy` in der
`AllowUsers`-Liste von OpenSSH. Damit bleibt der über einen eigenen SSH-Key
abgesicherte CI/CD-Zugang für App-Deployments nach einem erneuten Ansible-
Bootstrap erhalten:

```text
AllowUsers bootstrap deploy
```

Der Benutzer `deploy` ist nicht der Host-Maintenance-Benutzer; hostweite
Änderungen bleiben dem GitHub-hosted Bootstrap-/Recovery-Pfad vorbehalten.

## Verbindliches Betriebsmodell

Der Runner-Host darf in der aktuellen Entwicklungsphase gleichzeitig normale
Development-Workloads betreiben. Insbesondere sind auf demselben VPS zulässig:

- Odoo Development
- Development-Datenbanken
- Monitoring
- weitere Development-Apps
- GitHub-Runner-Plattform

Diese Co-Location ist ausdrücklich als Übergangs- und Testtopologie unterstützt.
Ein späterer dedizierter Runner-VPS bleibt möglich, ist aber keine Voraussetzung.

### Trennung von Host-Maintenance und App-Deployment

Normale App-Deployments dürfen später über `ephemeral-linux` auf denselben Host
laufen, wenn sie ausschließlich ihr eigenes Compose-Projekt beziehungsweise
ihren eigenen Service-Scope verändern.

Hostweite Änderungen dürfen nicht vom Self-hosted Runner auf seinem eigenen
Host ausgeführt werden. Dazu gehören insbesondere:

```text
Docker-Daemon oder Docker-Pakete aktualisieren/neustarten
Host rebooten
SSH-/Firewall-/Hardening-Grundlagen ändern
Runner-Plattform installieren, aktualisieren oder reparieren
globale Container-Cleanup-Befehle gegen alle Host-Container
```

Dafür bleiben `Bootstrap Fresh Host`, `Bootstrap Managed Host` und `Bootstrap Idempotency` fest auf
GitHub-hosted `ubuntu-24.04` gebunden. Dieser Recovery-Pfad darf nicht über
einen späteren `RUNNER_MODE`-Schalter auf `ephemeral-linux` umgestellt werden.

### Maintenance-Ablauf

Der Development-Host wird im späteren Normalbetrieb nicht bei jeder normalen
CI/CD-Ausführung bewusst neu gebootstrapped. Für geplante Host- oder
Runner-Wartung gilt:

1. neue Self-hosted Jobs nicht mehr auf dem Host einplanen; nach Einführung von
   `RUNNER_MODE` auf `github-hosted` umschalten,
2. laufende Jobs auslaufen lassen,
3. `DEVELOPMENT_BOOTSTRAP_MANAGED_HOST_ENABLED=true` nur für die bewusste
   Maintenance aktivieren,
4. GitHub-hosted Bootstrap ausführen,
5. Controller und `ephemeral-linux` per Smoke-Test prüfen,
6. Maintenance-Gate wieder deaktivieren,
7. danach geeignete Workflows wieder auf Self-hosted schalten.

`DEVELOPMENT_RUNNER_HOST_ENABLED` legt weiterhin fest, ob der Development-Host
beim Bootstrap zusätzlich als Runner-Host behandelt wird.

### Neustart-Recovery: Scale-Set-Ownership und Job-Zustellung

Seit dem Runner-Fix `CybXII/GitHub-Runners#13` bleiben die eigenen
Scale Sets über den Controller-Neustart hinweg bestehen. Die ID wird je
GitHub-Scope im geschützten Docker-Volume
`github-runner-platform-scale-set-ownership` gespeichert. Das Volume
**nicht** löschen oder mit `docker compose down -v` entfernen.

Ein nur als `running` gemeldeter Controller reicht für die Abnahme nicht
mehr aus: Sein Docker-Healthcheck wird erst `healthy`, wenn die Listener
für **alle** konfigurierten GitHub-Scopes laufen. Der Healthcheck beweist
allerdings **nicht**, dass GitHub auch einen Job zustellt.

Auf dem Development-VPS (lesende Prüfungen):

```bash
sudo docker inspect \
  -f 'Status={{.State.Status}} | Health={{.State.Health.Status}}' \
  github-runner-platform-controller

sudo docker logs --since 15m --tail 200 \
  github-runner-platform-controller 2>&1 \
  | grep -E 'Using verified owned|Starting runner scope|Getting next message|Ephemeral runner started|Runner scope stopped|ERROR|WARN' \
  | tail -n 60
```

Erwartet sind **beide** bekannten Scopes:
`https://github.com/Merchfactory` und
`https://github.com/CybXII/n8n-deployment`, jeweils mit
`Using verified owned runner scale set`, `Starting runner scope` und
regelmäßigen `Getting next message`-Einträgen ohne Fehler.

**Job-Zustellungs-Smoke-Test:** Einen neuen, unkritischen PR gegen
`development` öffnen. Der vorhandene Workflow `Repository Tests`
muss dann nachweislich einen `ephemeral-linux`-Job starten, dessen
`runner_name` GitHub ausweist und der erfolgreich endet. Bleiben
ausschließlich **vor dem Recovery erstellte** Actions-Runs `queued`,
diese über GitHub Actions gezielt abbrechen und bewusst erneut
auslösen; keinen hostweiten Bootstrap wiederholen. Bleiben auch
**neue** Jobs ohne Runner-Zuordnung `queued`, zunächst GitHub-Runner-
Group-Freigaben, Scope-Zuordnung und Broker-/Listener-Zustellung prüfen.
Ein `lastMessageID=0` alleine ist noch kein Verbindungsfehler.

Nach einem erfolgreich abgeschlossenen Testjob auf dem VPS:

```bash
sudo docker volume ls -q --filter dangling=true | wc -l
```

Erwartet: `0`. Persistente Volumes und fremde Scale Sets niemals
pauschal bereinigen. Eine einmalige Übernahme bisher nicht erfasster
registrierter Scale Sets ist im Runner-Repository dokumentiert und
erfordert vor der Freigabe die Prüfung, dass kein zweiter Controller
diese IDs verwaltet.

### App-Deployment auf einem gemeinsamen Runner-/Dev-Host

App-Deployments müssen eindeutige Compose-Projektnamen verwenden, zum Beispiel:

```text
merchfactory-development-odoo
merchfactory-development-postgres
merchfactory-development-prometheus
merchfactory-development-grafana
```

Self-hosted App-Deployments dürfen insbesondere keine pauschalen Befehle wie
`docker system prune -a`, das Entfernen aller Container oder das Stoppen des
Docker-Daemons verwenden. Der Runner-Controller bleibt ein eigener Stack und
wird nur über den GitHub-hosted Maintenance-/Recovery-Pfad verändert.

Die Architekturentscheidung ist in
`docs/02-adr/ADR-0010-self-hosted-runner-betriebsmodell.md` festgehalten.
