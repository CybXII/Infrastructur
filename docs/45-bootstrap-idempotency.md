# Bootstrap-Idempotenztests

## Zweck

Der Bootstrap soll einen Server deklarativ in einen definierten Sollzustand bringen. Ein erneuter Lauf gegen denselben unveränderten Host darf deshalb keine fachlich unnötigen Änderungen mehr erzeugen.

Issue #63 automatisiert diese Prüfung über zwei unmittelbar aufeinanderfolgende Ausführungen desselben Bootstrap-Playbooks.

## Testprinzip

Der Test führt aus:

```text
Bootstrap Lauf 1
    ↓
Sollzustand herstellen
    ↓
Bootstrap Lauf 2
    ↓
Ansible changed == 0 ?
    ├── ja  → Test erfolgreich
    └── nein → CI schlägt fehl
```

Der erste Lauf darf Änderungen erzeugen. Der zweite Lauf muss erfolgreich enden und über alle getesteten Hosts zusammen exakt `0` Änderungen melden.

Damit werden die im vollständigen Bootstrap enthaltenen Rollen gemeinsam geprüft:

- `base_installation`
- `package_updates`
- `system_time`
- `user_management`
- `storage_preparation`
- `ssh_hardening`
- `firewall`
- `fail2ban`
- `docker_runtime`

Der Test prüft damit nicht nur einzelne Tasks isoliert, sondern das Zusammenspiel des vollständigen v0.4-Bootstrap-Zustands.

## Testscript

Das Script liegt unter:

```text
scripts/test-bootstrap-idempotency.sh
```

Aufruf:

```bash
bash scripts/test-bootstrap-idempotency.sh \
  ansible/inventories/development/hosts.yml \
  bootstrap-test-01
```

Parameter:

1. Pfad zum Ansible-Inventar.
2. Optionaler Host-/Gruppen-Limit-Ausdruck.

Die Ansible-Ausgabe wird mit dem JSON-Callback `ansible.posix.json` erfasst. Das Script wertet die Host-Statistik aus und beendet sich mit Exit-Code `1`, sobald der zweite Lauf eine Änderung, einen Fehler oder einen nicht erreichbaren Host meldet.

## CI-Workflow

Der Workflow liegt unter:

```text
.github/workflows/bootstrap-idempotency.yml
```

Er wird bewusst ausschließlich über `workflow_dispatch` gestartet. Ein Bootstrap-Test benötigt einen echten EL9-Testhost mit systemd, firewalld, SSH und Docker-Funktionalität. Ein normaler GitHub-Runner oder ein einfacher Container bildet diese Host-Eigenschaften nicht ausreichend realistisch ab.

Der Idempotenzworkflow ist ein **Managed-Host-Test**. Er verbindet sich nicht mehr über den initialen Provider-/Root-Benutzer, sondern direkt über den vom Bootstrap verwalteten technischen Benutzer `bootstrap`.

Der Workflow verwendet das GitHub Environment `development` und benötigt folgende Secrets:

```text
DEVELOPMENT_BOOTSTRAP_TEST_HOST
DEVELOPMENT_BOOTSTRAP_TEST_SSH_KEY
DEVELOPMENT_BOOTSTRAP_TEST_KNOWN_HOSTS
```

Bedeutung:

- `*_HOST`: IP-Adresse oder DNS-Name des freigegebenen Testhosts.
- `*_SSH_KEY`: privater SSH-Schlüssel des verwalteten Development-Bootstrap-Zugangs.
- `*_KNOWN_HOSTS`: vertrauenswürdiger known-hosts-Eintrag bzw. die Einträge für den Testhost.

`DEVELOPMENT_BOOTSTRAP_TEST_USER` wird für diesen Managed-Host-Idempotenzworkflow nicht verwendet. Der Verbindungsbenutzer ist deklarativ `bootstrap`.

Der Public Key wird im Runner aus dem Private Key abgeleitet und zusammen mit dem Testhost in ein temporäres vollständiges Managed-Host-Inventar überführt. Dadurch enthält das Inventar neben der SSH-Verbindung auch den gewünschten Benutzer-, sudo- und SSH-Hardening-Zustand.

Der private Schlüssel wird nur zur Laufzeit in die Runner-Umgebung geschrieben. Er wird weder committed noch als Artifact gespeichert und am Ende des Jobs entfernt.

## Warum kein automatischer PR-Lauf auf jedem Commit?

Die Inventare enthalten absichtlich noch keine realen Serverziele. Außerdem verändert der Bootstrap Betriebssystemzustand, Firewall, SSH, Pakete und Docker. Ein solcher Integrationstest darf daher nicht versehentlich gegen einen beliebigen Development- oder Production-Host laufen.

Deshalb ist der v0.4-Idempotenztest aktuell ein expliziter CI-Integrationstest gegen einen dafür vorgesehenen Development-Testhost.

Sobald eine dauerhaft verfügbare Testinstanz oder ein automatisiertes Ephemeral-Host-Provisioning existiert, kann derselbe Test später an Pull Requests oder Promotion-Workflows gekoppelt werden.

## CI-Auswertung

Der Workflow erzeugt:

```text
artifacts/bootstrap-idempotency/first-run.json
artifacts/bootstrap-idempotency/second-run.json
artifacts/bootstrap-idempotency/summary.txt
```

`summary.txt` enthält beispielsweise:

```text
Bootstrap idempotency result
inventory=/tmp/bootstrap-idempotency-inventory.json
limit=bootstrap-test
first_run_changed=3
second_run_changed=0
```

Die Zusammenfassung wird zusätzlich in den GitHub Actions Job Summary geschrieben. Die vollständigen Ergebnisse werden für 14 Tage als CI-Artifact gespeichert.

## Fehlerfall

Ein Test gilt als fehlgeschlagen, wenn:

- einer der beiden Bootstrap-Läufe fehlschlägt,
- ein Host nicht erreichbar ist,
- Ansible keine auswertbare Host-Statistik erzeugt,
- der zweite Lauf mindestens eine Änderung meldet.

Eine Änderung im zweiten Lauf muss untersucht werden. Sie darf nicht pauschal ignoriert werden, da wiederkehrende `changed`-Meldungen auf nicht idempotente Tasks, instabile externe Zustände oder eine unvollständige Zustandsprüfung hinweisen können.

Falls ein Task fachlich zwangsläufig bei jedem Lauf eine Änderung erzeugen müsste, soll zunächst geprüft werden, ob er deklarativ oder mit korrektem `changed_when` modelliert werden kann. Eine Allowlist für permanente Änderungen ist bewusst nicht vorgesehen.

## Abgrenzung zu Issue #65

Issue #63 prüft die **Wiederholbarkeit** eines bereits verwalteten Testhosts.

Issue #65 validiert zusätzlich den vollständigen Bootstrap auf einem **leeren/frischen Server**. Dort wird insbesondere geprüft, ob sämtliche Voraussetzungen für einen Erstlauf tatsächlich vollständig sind und ob der Vertrauensübergang vom initialen Provider-Zugang zum verwalteten Benutzer funktioniert.

Beide Tests ergänzen sich:

```text
#65 Fresh Host
→ kann ein leerer Server vollständig aufgebaut werden?

#63 Idempotency / Managed Host
→ bleibt der fertig aufgebaute Server beim zweiten Lauf unverändert?
```

Der automatisierte Fresh-Host-Ablauf aus #65 verwendet zwei Verbindungsidentitäten: den initialen Provider-Benutzer für den ersten Lauf und den durch den Bootstrap verwalteten Benutzer `bootstrap` für Reconnect, zweiten Lauf und Nachprüfung. Der separate Idempotenzworkflow beginnt dagegen direkt im dauerhaft vorgesehenen Managed-Host-Zustand.

## Referenzen

- Issue #63
- Issue #65
- Issue #66
- `.github/workflows/bootstrap-idempotency.yml`
- `.github/workflows/bootstrap-managed-host.yml`
- `.github/workflows/bootstrap-fresh-host.yml`
- `scripts/create-bootstrap-test-inventories.py`
- `scripts/test-bootstrap-idempotency.sh`
