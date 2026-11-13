# Automatisierte Firewall-Konfiguration

## Zweck

Die Rolle `firewall` setzt auf AlmaLinux OS 9 und Rocky Linux 9 eine restriktive, rollenbasierte `firewalld`-Konfiguration um. Sie wird nach Benutzerverwaltung und SSH-Hardening ausgeführt.

## Sicherheitsmodell

Standardmäßig gilt:

- `firewalld` ist installiert, aktiviert und gestartet,
- die Zone `public` wird verwaltet,
- das Zonenziel wird auf `DROP` gesetzt,
- nur ausdrücklich deklarierte Dienste und direkte Ports werden freigegeben,
- nicht deklarierte permanente Dienste und direkte Ports werden standardmäßig entfernt,
- der aktive SSH-Port wird vor dem Default-Deny geöffnet,
- unbekannte Serverrollen führen zu einem kontrollierten Abbruch,
- Regeln werden permanent und unmittelbar angewendet.

Der aus `ssh_hardening_port` übernommene SSH-Port wird automatisch als TCP-Port ergänzt. Dadurch wird verhindert, dass das Firewall-Hardening den administrativen Zugang während des Bootstrap-Laufs abschneidet.

## Reihenfolge und Aussperrungsschutz

Die Rollen werden in dieser Reihenfolge ausgeführt:

1. `base_installation`
2. `user_management`
3. `ssh_hardening`
4. `firewall`

Vor dem Setzen des restriktiven Zonenziels werden alle benötigten Dienste und Ports freigegeben. Bei exklusiver Portverwaltung wird der erforderliche SSH-Port **zuerst** aktiviert; erst danach werden veraltete, nicht deklarierte direkte Portfreigaben entfernt. Dadurch kann ein alter Port-Drift bereinigt werden, ohne den administrativen Zugang vorzeitig zu schließen.

Quellgebundene Freigaben aus `firewall_allowed_source_ports` werden als Rich Rules verwaltet und gehören nicht zu `--list-ports`; sie werden von der exklusiven Verwaltung direkter Ports daher nicht versehentlich entfernt.

Nach dem Reload wird geprüft, ob der SSH-Port in der aktiven Zone sichtbar ist.

Beim ersten produktiven Lauf muss trotzdem eine bestehende Administrationssitzung geöffnet bleiben, bis eine zweite SSH-Anmeldung erfolgreich getestet wurde. Zusätzlich müssen externe Provider-Firewalls oder Security Groups geprüft werden.

## Rollenprofile

Die Rolle enthält bewusst kleine Standardprofile:

```yaml
firewall_role_profiles:
  base: []
  load_balancer:
    - 80/tcp
    - 443/tcp
  app: []
  database: []
  monitoring: []
  backup: []
```

Ein Server erhält seine Profile über:

```yaml
firewall_server_roles:
  - base
  - load_balancer
```

Damit werden für einen Load Balancer zusätzlich `80/tcp` und `443/tcp` geöffnet.

Leere Profile öffnen keine Ports. Datenbank-, Monitoring- und Backup-Ports müssen bewusst über Inventarvariablen oder später konkretisierte Rollen gesetzt werden.

Node Exporter aus #86 ist absichtlich **keine** Ausnahme: `9100/tcp` wird nicht in der öffentlichen Zone geöffnet. Der Agent bindet ausschließlich an das interne Docker-Bridge-Gateway `172.30.250.1:9100`; die systemd-Unit erlaubt IP-Traffic zusätzlich nur aus `172.30.250.0/24`. Damit bleibt die öffentliche firewalld-Baseline unverändert.

## Wichtige Variablen

| Variable | Standard | Bedeutung |
|---|---:|---|
| `firewall_zone` | `public` | verwaltete firewalld-Zone |
| `firewall_default_target` | `DROP` | Standardbehandlung nicht erlaubter Verbindungen |
| `firewall_manage_zone_target` | `true` | Zonenziel verwalten |
| `firewall_ssh_port` | Wert aus `ssh_hardening_port` | freizugebender SSH-Port |
| `firewall_require_ssh_access` | `true` | SSH-Freigabe zwingend absichern |
| `firewall_allowed_services` | `[dhcpv6-client]` | erlaubte firewalld-Dienstnamen |
| `firewall_manage_services_exclusively` | `true` | nicht deklarierte permanente Dienste entfernen |
| `firewall_allowed_ports` | `[]` | zusätzliche direkte Ports wie `8080/tcp` |
| `firewall_manage_ports_exclusively` | `true` | nicht deklarierte permanente direkte Ports entfernen |
| `firewall_allowed_source_ports` | `[]` | quellgebundene Portfreigaben |
| `firewall_rich_rules` | `[]` | zusätzliche firewalld Rich Rules |
| `firewall_server_roles` | `[base]` | aktive Rollenprofile |
| `firewall_interface` | leer | optionale feste Interface-Zuordnung |

## Direkte Ports und Dienste

```yaml
firewall_allowed_services:
  - https

firewall_allowed_ports:
  - 8080/tcp
  - 8443/tcp
```

Dienste und Ports werden permanent und sofort aktiviert.

Standardmäßig werden sowohl Dienste als auch direkte Ports **exklusiv** verwaltet. Ein zuvor manuell oder von einem alten Deployment geöffneter direkter Port wird beim nächsten Bootstrap entfernt, wenn er nicht mehr in `firewall_effective_ports` enthalten ist. Das bewusste Deaktivieren dieser Exklusivität ist eine Betriebsabweichung und sollte nur für einen klar dokumentierten Übergangszustand verwendet werden.

## Quellgebundene Regeln

Interne Dienste sollten möglichst nicht global freigegeben werden:

```yaml
firewall_allowed_source_ports:
  - source: 10.20.0.0/24
    port: '5432'
    protocol: tcp
```

Dies erzeugt eine Rich Rule, die PostgreSQL nur aus dem angegebenen Netz erlaubt.

## Zusätzliche Rich Rules

```yaml
firewall_rich_rules:
  - 'rule family="ipv4" source address="10.30.0.0/24" service name="node-exporter" accept'
```

Rich Rules müssen vollständig und fachlich geprüft übergeben werden.

## Default-Deny

`firewall_default_target: DROP` verwirft nicht ausdrücklich erlaubten eingehenden Traffic. Ausgehender Traffic wird durch diese Rolle nicht pauschal eingeschränkt.

Ein vollständiges Egress-Filtering ist nicht Bestandteil von v0.4 und benötigt ein gesondertes Netzwerk- und Betriebsmodell.

## Idempotenz

Dienste, direkte Ports, Interfaces und Rich Rules werden über `ansible.posix.firewalld` zustandsorientiert verwaltet. Dienste und direkte Ports werden standardmäßig gegen den deklarativen Sollzustand abgeglichen; veraltete Einträge werden entfernt. Wiederholte Läufe mit unveränderten Variablen dürfen keine fachlich unnötigen Regeländerungen erzeugen.

Ein Reload wird nur nach Änderungen an permanenten Einstellungen ausgelöst.

## Validierung und Fehlerverhalten

Der Lauf bricht kontrolliert ab, wenn:

- der Portbereich ungültig ist,
- Listenvariablen falsch aufgebaut sind,
- eine unbekannte Serverrolle angegeben wird,
- `firewalld` nicht installiert oder startbar ist,
- eine Regel nicht angewendet werden kann,
- der SSH-Port nach der Anwendung nicht aktiv sichtbar ist.

Fehler werden nicht ignoriert.

## Rollback

Bei einem Problem:

1. bestehende SSH-Sitzung geöffnet lassen,
2. Zonenkonfiguration mit `firewall-cmd --zone=<zone> --list-all` prüfen,
3. benötigten SSH-Port nötigenfalls manuell freigeben,
4. Zonenziel vorübergehend auf `default` oder `ACCEPT` zurücksetzen,
5. Konfiguration korrigieren und das Playbook erneut ausführen.

Ein Repository-Rollback erfolgt durch Revert des zugehörigen Commits.

## Abgrenzung

Nicht Bestandteil dieser Rolle sind:

- externe Provider-Firewalls und Security Groups,
- Router- oder VLAN-Firewalls,
- Fail2ban,
- VPN- und Bastion-Architektur,
- vollständiges Egress-Filtering,
- dynamische Container-Portfreigaben,
- Hochverfügbarkeits- oder Cluster-Firewallregeln.
