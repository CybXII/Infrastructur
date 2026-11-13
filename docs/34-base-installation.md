# Automatisierte Basisinstallation

## Zweck

Die Ansible-Rolle `base_installation` bereitet ein unterstütztes Enterprise-Linux-9-Zielsystem für die weiteren Bootstrap-Schritte vor. Sie installiert ausschließlich allgemeine Systemwerkzeuge und stellt grundlegende Laufzeitvoraussetzungen bereit. Benutzerverwaltung, SSH-Hardening, Firewall-Regeln, Fail2ban, Update-Strategie, Storage und Docker werden in eigenen Issues umgesetzt.

## Unterstützte Zielsysteme

Die Rolle folgt `docs/33-supported-operating-systems.md`:

- AlmaLinux OS 9 auf x86_64: primär unterstützt
- Rocky Linux 9 auf x86_64: optional kompatibel

Das Playbook bricht vor schreibenden Änderungen ab, wenn Distribution, Major-Version oder Architektur nicht unterstützt werden.

## Enthaltene Vorbereitung

Standardmäßig werden folgende Pakete installiert:

- `bash-completion`
- `ca-certificates`
- `curl`
- `dnf-plugins-core`
- `firewalld`
- `git`
- `jq`
- `policycoreutils-python-utils`
- `python3`
- `python3-libselinux`
- `rsync`
- `tar`
- `unzip`
- `vim-minimal`
- `wget`

Zusätzlich werden:

- DNF-Metadaten mit begrenzten Wiederholungsversuchen aktualisiert,
- das CRB-Repository standardmäßig aktiviert,
- EPEL nur bei ausdrücklicher Aktivierung installiert,
- `firewalld` aktiviert und gestartet,
- Python 3 und der SELinux-Status abschließend validiert.

## Variablen

| Variable | Standard | Bedeutung |
|---|---:|---|
| `base_installation_packages` | Paketliste der Rolle | vollständig gewünschte Basispakete |
| `base_installation_enable_crb` | `true` | CRB-Repository aktivieren |
| `base_installation_update_cache` | `true` | DNF-Metadaten aktualisieren |
| `base_installation_install_epel` | `false` | EPEL-Repository installieren |
| `base_installation_epel_package` | `epel-release` | Paketname für EPEL |

Die Paketliste kann über Gruppen- oder Hostvariablen erweitert oder vollständig ersetzt werden. Secrets gehören nicht in diese Variablen.

## Ausführung

Aus dem Verzeichnis `ansible`:

```bash
ansible-playbook -i <inventar> playbooks/bootstrap.yml --limit <zielhost>
```

Vor dem ersten produktiven Lauf:

```bash
ansible-playbook -i <inventar> playbooks/bootstrap.yml --limit <zielhost> --check --diff
```

Der Check-Modus ersetzt keinen Test auf einem frischen Zielsystem, reduziert aber das Risiko unbeabsichtigter Änderungen.

## Idempotenz

Die Paketinstallation und der Dienstzustand verwenden idempotente Ansible-Module. Ein zweiter vollständiger Lauf muss ohne fachlich unnötige Änderungen enden. Die spätere CI- und Integrationstest-Umsetzung erfolgt im Rahmen von Issue #63.

## Fehlerverhalten

- Nicht unterstützte Betriebssysteme führen vor Rollenaufruf zu einem kontrollierten Abbruch.
- DNF-Metadaten, EPEL und Paketinstallation werden maximal dreimal versucht.
- Ein fehlender DNF-Paketmanager führt zu einem expliziten Fehler.
- Fehlendes `/usr/bin/python3` oder deaktiviertes SELinux führt nach der Installation zu einem Fehler.
- Fehler werden nicht ignoriert und erzeugen einen nicht erfolgreichen Ansible-Exitstatus.

## Rollback

Die Rolle entfernt keine vorhandenen Pakete und verändert keine kundenspezifischen Repository-Dateien. Ein vollständiger Rollback besteht deshalb aus:

1. Revert der Infrastrukturänderung im Repository,
2. optionalem Entfernen neu installierter Pakete nach manueller Abhängigkeitsprüfung,
3. optionalem Deaktivieren von CRB oder EPEL, sofern diese nicht von anderen Komponenten benötigt werden.

Das automatische Entfernen von Paketen ist bewusst nicht Bestandteil der Rolle, da dadurch bereits vorhandene Systemabhängigkeiten beschädigt werden könnten.
