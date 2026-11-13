# Docker Repository und Runtime

## Zweck

Die Rolle `docker_runtime` installiert Docker Engine, Docker CLI, containerd, Buildx und das Compose Plugin reproduzierbar auf den für v0.4 unterstützten AlmaLinux-9- und Rocky-Linux-9-Systemen.

Die Installation erfolgt ausschließlich aus dem offiziellen Docker-CE-Stable-Repository. Die Paketversionen sind bewusst im Repository gepinnt, damit ein identischer Infrastructure-Stand nicht zu unterschiedlichen Docker-Versionen auf verschiedenen Servern führt.

## Offizielle Paketquelle

Verwendet wird:

```text
https://download.docker.com/linux/centos/9/x86_64/stable
```

AlmaLinux 9 und Rocky Linux 9 sind RHEL-kompatible EL9-Systeme. Für diese Zielplattform wird das offizielle Docker-CentOS/EL9-Repository verwendet. Die Repository-GPG-Prüfung ist aktiviert und verwendet den offiziellen Docker-GPG-Key.

## Gepinnte Versionen

Stand dieses Infrastructure-Releases:

| Komponente | Paketversion |
|---|---|
| Docker Engine | `docker-ce-29.7.2-1.el9` |
| Docker CLI | `docker-ce-cli-29.7.2-1.el9` |
| containerd | `containerd.io-2.3.3-1.el9` |
| Buildx Plugin | `docker-buildx-plugin-0.36.1-1.el9` |
| Compose Plugin | `docker-compose-plugin-5.4.0-1.el9` |

Versionserhöhungen erfolgen bewusst über einen Infrastructure-PR. Dadurch werden Docker-Upgrades reviewbar und durchlaufen dieselbe Development → Staging → Production-Promotion wie andere Infrastrukturänderungen.

`allow_downgrade: true` stellt zusätzlich sicher, dass ein Server, auf dem versehentlich eine neuere Paketversion installiert wurde, wieder auf den im Repository definierten Sollzustand gebracht werden kann.

## Sichere Daemon-Basiskonfiguration

Die Rolle verwaltet `/etc/docker/daemon.json` und setzt standardmäßig:

```json
{
  "data-root": "/var/lib/docker",
  "live-restore": true,
  "userland-proxy": false,
  "no-new-privileges": true,
  "log-driver": "local",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5",
    "compress": "true"
  }
}
```

Bedeutung:

- `live-restore`: laufende Container sollen einen Docker-Daemon-Neustart möglichst überstehen.
- `userland-proxy: false`: vermeidet den zusätzlichen Userspace-Proxy, sofern Kernel-NAT verwendet werden kann.
- `no-new-privileges: true`: Container können standardmäßig keine zusätzlichen Privilegien über setuid/setgid gewinnen.
- `local` Log Driver plus `20m × 5` und Kompression: begrenzt lokale Containerlogs auf eine feste Rotation pro Container und reduziert das Risiko von Dateisystemfüllung.

Die vollständige lokale Logging-/Retention-Policy steht in `docs/56-log-rotation.md`. Änderungen an den Daemon-Logging-Defaults gelten nur für neu erstellte Container; bestehende Container müssen kontrolliert neu erstellt werden.

Alte Docker-Runtime-Artefakte werden nicht pauschal per `docker system prune` bereinigt. Das rollback-sichere Lifecycle-Verfahren aus `docs/59-docker-retention-cleanup.md` entfernt ausschließlich definierte Altartefakte und schließt persistente Volumes aus.

Diese Einstellungen ersetzen keine Container-Härtung. Capabilities, read-only Filesystems, Secrets, Netzwerksegmentierung und servicebezogene Security-Optionen werden auf Container-/Stack-Ebene definiert.

CPU-, Memory- und PID-cgroups werden ebenfalls servicebezogen gesetzt. Die verbindliche Baseline steht in `docs/55-container-resource-limits.md`; der Docker-Daemon selbst erhält dadurch keine pauschalen globalen Containerlimits.

## Docker-Gruppe

Die Rolle fügt bewusst **keine Benutzer automatisch zur Gruppe `docker` hinzu**. Mitgliedschaft in dieser Gruppe ermöglicht praktisch Root-äquivalente Kontrolle über den Host und muss daher separat und explizit entschieden werden.

## Konfliktpakete

Vor der Installation werden bekannte konfliktträchtige Distribution-/Legacy-Pakete entfernt, unter anderem `docker`, `docker-engine` und `podman-docker`. Dies verhindert, dass `/usr/bin/docker` oder Runtime-Komponenten aus unterschiedlichen Paketquellen vermischt werden.

Podman selbst wird nicht pauschal entfernt; lediglich das Docker-Kompatibilitätspaket `podman-docker` wird ausgeschlossen.

## Bootstrap-Reihenfolge

`docker_runtime` läuft nach Storage-Vorbereitung und Security-Basisrollen. Damit sind Systemupdates, Zeitbasis, Benutzer, Verzeichnisse, SSH, Firewall und Fail2ban bereits definiert, bevor die Container-Runtime in Betrieb geht.

## Validierung

Nach der Installation prüft die Rolle:

```bash
systemctl is-active docker
docker --version
docker compose version
docker buildx version
docker info
```

Zusätzlich wird `/etc/docker/daemon.json` vor Verwendung mit `python3 -m json.tool` syntaktisch validiert.

Der Bootstrap bricht ab, wenn:

- der Docker-Dienst nicht aktiv ist,
- Engine, Compose oder Buildx nicht den gepinnten Versionen entsprechen,
- der Docker-Daemon über `docker info` nicht erreichbar ist.

## Aktualisierungsstrategie

Docker wird absichtlich nicht durch `dnf-automatic` beliebig auf eine neue Feature-Version gezogen. Die Rolle definiert konkrete Paketversionen. Ein Upgrade erfolgt so:

1. neue Versionen im offiziellen Docker-Repository prüfen,
2. Versionswerte in `docker_package_versions` ändern,
3. Repository-/CI-Prüfungen ausführen,
4. Development-System aktualisieren und Runtime-Funktion prüfen,
5. über Staging nach Production promoten.

Damit bleibt ein Docker-Upgrade ein kontrollierter Infrastruktur-Rollout statt eines unbeobachteten Paketupdates.

## Persistenz

Docker verwendet standardmäßig `/var/lib/docker` für Runtime-Daten wie Images, Layer und interne Metadaten. Dieser Pfad ist nicht als Backup-Ort für Anwendungsdaten gedacht.

Das Verzeichnis wird mit Eigentümer `root:root` und Modus `0710`
verwaltet. Dieser restriktive Zustand entspricht dem vom gestarteten
Docker-Daemon normalisierten Laufzeitzustand und verhindert wiederkehrende
Berechtigungsänderungen in nachfolgenden Bootstrap-Läufen.

Persistente Anwendungsdaten sollen spätere Compose-/Applikationsrollen in die in #60 definierten persistenten Plattformpfade binden. Container-Layer selbst gelten als reproduzierbar und nicht als fachliche Persistenz.

## Firewall-Hinweis

Docker kann eigene iptables/nftables-Regeln für veröffentlichte Containerports erzeugen. Deshalb dürfen Containerports später nicht allein aufgrund einer firewalld-Zone als geschützt betrachtet werden. Portfreigaben und Docker-Netzwerkmodell müssen in v0.5 gemeinsam mit Reverse Proxy und Container-Plattform definiert werden.

## Abgrenzung

Nicht Bestandteil dieses Tasks sind:

- Deployment konkreter Applikationscontainer,
- Docker Compose Stacks,
- Registry-Login oder Registry-Credentials,
- Reverse Proxy,
- Swarm/Kubernetes,
- zentrale Containerlogs,
- Docker-Socket-Freigabe an Anwendungen,
- automatische Aufnahme von Benutzern in die `docker`-Gruppe.

## Frischsystem- und Idempotenztests

Die Runtime-Prüfungen sind Bestandteil der Rolle. Der vollständige End-to-End-Bootstrap auf einem leeren AlmaLinux-/Rocky-System sowie der zweite Lauf zur Idempotenzprüfung werden zusätzlich in #63 und #65 abgedeckt.
