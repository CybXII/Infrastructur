# v0.4 Review – Server Bootstrap

## Zweck

Dieses Dokument fasst den Abschlussreview für Epic #51 und Issue #66 zusammen. Geprüft wird, ob der v0.4-Server-Bootstrap den vereinbarten Funktions-, Sicherheits-, Idempotenz- und Dokumentationsstand erreicht hat und als Basis für v0.5 – Container Platform freigegeben werden kann.

## Prüfstand

Fachlicher Bootstrap-Stand:

```text
1cc1f42da756f974ceb0404a9b6187bc434044b8
```

Der Stand wurde anschließend über `development -> staging -> main` promotet. PR #246 synchronisierte die reine Promotion-Historie wieder nach `development`; zwischen `main` und `development` bestanden dabei keine Dateidifferenzen.

Der abschließende Fresh-Host-Nachweis erfolgte über GitHub Actions Run `34413968035`, Attempt `3`.

## Scope

Der v0.4-Bootstrap umfasst:

1. `base_installation`
2. `package_updates`
3. `system_time`
4. `user_management`
5. `storage_preparation`
6. `ssh_hardening`
7. `firewall`
8. `fail2ban`
9. `docker_runtime`

Das Bootstrap-Playbook validiert vor der Rollenausführung AlmaLinux OS 9 bzw. Rocky Linux 9 auf x86_64.

## Ergebnis der Definition of Done

### Bootstrap- und Idempotenztests

**Erfüllt.**

Der Fresh-Host-Test wurde auf einem neu installierten AlmaLinux-9-x86_64-Server ausgeführt. Der Preflight bestätigte unter anderem:

- unterstütztes Zielsystem,
- funktionierenden initialen Provider-/Root-Zugang,
- ausreichenden freien Speicher,
- erreichbare Paketquellen,
- funktionierende DNS- und HTTPS-Verbindungen,
- noch nicht vorhandenen verwalteten Benutzer,
- noch nicht vorhandene Docker-CE-Installation.

Anschließend wurden erfolgreich ausgeführt:

```text
initialer Provider-/Root-Zugang
    ↓
erster vollständiger Bootstrap
    ↓
verwalteten Benutzer bootstrap verwenden
    ↓
Reconnect als bootstrap
    ↓
zweiter vollständiger Bootstrap
    ↓
Idempotenzprüfung
    ↓
Sicherheits- und Funktionsverifikation
```

Der Reconnect als `bootstrap` war erfolgreich. Der zweite Bootstrap-Lauf erfüllte die strikte Idempotenzanforderung; die anschließende Verifikation endete ohne Fehler.

### Sicherheits- und Funktionschecks

**Erfüllt.**

Der finale Fresh-Host-Lauf bestätigte unter anderem:

- `sshd` aktiv,
- `firewalld` aktiv,
- `fail2ban` aktiv,
- `chronyd` aktiv,
- `dnf-automatic.timer` aktiv,
- `docker` aktiv,
- SELinux `Enforcing`,
- passwortloses sudo für den verwalteten Bootstrap-Benutzer,
- Root-SSH deaktiviert,
- Passwort- und Keyboard-Interactive-Authentifizierung deaktiviert,
- Public-Key-Authentifizierung aktiviert,
- X11-, TCP- und Agent-Forwarding deaktiviert,
- `AllowUsers bootstrap` wirksam,
- restriktives firewalld-Zonenziel,
- ausschließlich erwartete permanente Firewall-Ports und -Dienste,
- SSH- und Recidive-Jail in Fail2ban,
- synchronisierte Systemzeit,
- standardisierte Merchfactory-Storage-Verzeichnisse,
- restriktives Docker-Datenverzeichnis,
- erreichbaren Docker-Daemon,
- funktionierendes Docker Compose.

## Feststellungen aus den realen Bootstrap-Läufen

Die praktische Validierung hat mehrere reale Abweichungen aufgedeckt, die vor dem Abschluss korrigiert wurden:

- nicht verfügbarer Ansible-`yaml`-Callback,
- falscher temporärer SSH-Key-Pfad durch einen ungeeigneten Runner-Kontext,
- nicht idempotenter Modus von `/var/lib/docker`,
- SSH-Drop-in-Priorität mit abweichender effektiver `sshd -T`-Konfiguration,
- fehlende Trennung zwischen einmaligem Fresh-Host-Aufbau und dauerhaftem Managed-Host-Pfad,
- unvollständiges deklaratives Managed-Host-Inventar,
- additive statt exklusive permanente Firewall-Serviceverwaltung.

Die Fehler wurden nicht durch Workarounds ausgeblendet, sondern im deklarativen Sollzustand, in den Tests oder in der CI-Orchestrierung korrigiert. Der abschließende Fresh-Host-Lauf bestätigt den gemeinsamen korrigierten Stand.

## Dokumentationsreview

Die v0.4-Dokumentation deckt die unterstützten Betriebssysteme, alle Bootstrap-Rollen, Inventare, Idempotenz und das operative Bootstrap-Runbook ab.

Beim Abschlussreview wurden zwei kleinere Dokumentationsabweichungen gegenüber dem inzwischen korrigierten CI-Verhalten festgestellt:

1. `docs/45-bootstrap-idempotency.md` beschreibt `DEVELOPMENT_BOOTSTRAP_TEST_USER` noch als Secret des manuellen Idempotenzworkflows. Der aktuelle Workflow verbindet sich dagegen ausschließlich als verwalteter Benutzer `bootstrap` und benötigt dieses Secret dort nicht mehr.
2. Der Fresh-Host-Abschnitt in `docs/46-bootstrap-runbook.md` verwendet teilweise noch Formulierungen aus der früheren automatischen Trigger-Phase. Der aktuelle Fresh-Host-Workflow ist ausschließlich per `workflow_dispatch` startbar und zusätzlich über `DEVELOPMENT_BOOTSTRAP_FRESH_HOST_ENABLED` geschützt.

Diese Abweichungen sind keine Runtime- oder Security-Blocker, müssen aber im Rahmen von Issue #66 bereinigt werden, bevor der Dokumentationspunkt als vollständig abgeschlossen gilt.

## Supportgrenze

Für v0.4 gilt:

- AlmaLinux OS 9 auf x86_64 ist das primär unterstützte und praktisch validierte Zielsystem.
- Rocky Linux 9 auf x86_64 bleibt optional kompatibel. Ein fehlender Rocky-Lauf blockiert die AlmaLinux-Freigabe nicht.
- andere Distributionen und Architekturen sind nicht freigegeben.

## Bewusste Abgrenzungen und technische Schulden

Folgende Themen gehören nicht zum v0.4-Scope und blockieren den Abschluss nicht:

- automatische VPS-/VM-Provisionierung,
- Betriebssysteminstallation,
- produktive Applikationscontainer,
- Reverse Proxy und TLS-Terminierung,
- endgültiges Docker-Service-Netzwerk- und Portmodell,
- persistente Applikationsdatenbanken und HA,
- zentrale Monitoring-/Alerting-Plattform,
- Multi-Site-Failover.

Docker-Retention und kontrollierter Cleanup bleiben separat in Issue #231 für Epic #67/v0.5 erfasst. Persistente Volumes dürfen dabei nicht pauschal bereinigt werden.

## Freigabebewertung

Der technische v0.4-Bootstrap ist nach dem erfolgreichen Clean-Room-Test für AlmaLinux OS 9 auf x86_64 freigabefähig.

Für den formalen Abschluss von Issue #66 verbleiben ausschließlich:

1. die zwei oben genannten Dokumentationsabweichungen bereinigen,
2. Repository-/Governance-Checks des Abschluss-PRs erfolgreich ausführen,
3. Review-Stand nach `development` mergen und regulär promoten,
4. danach Issue #66 und Epic #51 auf `status: done` setzen und schließen.

Nach diesem Abschluss kann Epic #67 – v0.5 Container Platform aktiv gestartet werden.

## Referenzen

- Epic #51
- Issue #63
- Issue #64
- Issue #65
- Issue #66
- Epic #67
- Issue #231
- PR #236 bis #243
- PR #246
- GitHub Actions Run `34413968035`, Attempt `3`
- `ansible/playbooks/bootstrap.yml`
- `docs/33-supported-operating-systems.md`
- `docs/45-bootstrap-idempotency.md`
- `docs/46-bootstrap-runbook.md`
