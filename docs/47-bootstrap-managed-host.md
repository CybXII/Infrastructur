# Bootstrap bereits verwalteter Hosts

## Zweck

Der Fresh-Host-Pfad und der laufende Konfigurationsbetrieb werden getrennt behandelt.

Ein Fresh Host wird einmalig über den initialen Provider-Zugang aufgebaut. Dabei legt der Bootstrap den verwalteten Benutzer `bootstrap` an, installiert dessen SSH-Schlüssel und härtet anschließend den SSH-Zugang.

Nach dieser Vertrauensübergabe dürfen spätere Infrastrukturänderungen nicht erneut den initialen Benutzer verwenden. Updates, Korrekturen und Validierungen verbinden sich direkt als `bootstrap`.

## Fresh-Host-Pfad

Workflow: `.github/workflows/bootstrap-fresh-host.yml`

Dieser Workflow ist nur manuell auslösbar und setzt einen tatsächlich frischen Zielhost voraus.

Ablauf:

1. Verbindung über `DEVELOPMENT_BOOTSTRAP_TEST_USER`.
2. Fresh-Host-Preflight.
3. erster vollständiger Bootstrap.
4. Reconnect als `bootstrap`.
5. zweiter Bootstrap über `bootstrap` mit `changed=0`.
6. Sicherheits- und Funktionschecks über `bootstrap`.

Der Workflow darf nicht als allgemeiner Update-Workflow verwendet werden.

## Managed-Host-Pfad

Workflow: `.github/workflows/bootstrap-managed-host.yml`

Dieser Pfad ist für bereits von Merchfactory verwaltete Development-Hosts vorgesehen. Er verwendet von Beginn an den Benutzer `bootstrap`.

Ablauf:

1. Verbindung als `bootstrap` prüfen.
2. aktuellen Infrastructure-Stand mit Ansible anwenden.
3. zweiten Bootstrap-Lauf ausführen und `changed=0` verlangen.
4. Sicherheits- und Funktionschecks ausführen.

Seit #86 gehört auch der Node-Exporter-Host-Agent zum deklarativen Bootstrap. Der Verifikationslauf bestätigt Dienststatus, ausschließliche Bindung an `172.30.250.1:9100` und zentrale CPU-/Memory-/Filesystem-/Netzwerkmetriken.

Der automatische Development-Lauf ist zusätzlich durch die Repository-Variable `DEVELOPMENT_BOOTSTRAP_MANAGED_HOST_ENABLED=true` abgesichert.

## Credentials

Beide Development-Pfade verwenden die bestehenden Secrets:

- `DEVELOPMENT_BOOTSTRAP_TEST_HOST`
- `DEVELOPMENT_BOOTSTRAP_TEST_SSH_KEY`
- `DEVELOPMENT_BOOTSTRAP_TEST_KNOWN_HOSTS`

Nur der Fresh-Host-Pfad benötigt zusätzlich:

- `DEVELOPMENT_BOOTSTRAP_TEST_USER`

Der private Schlüssel wird nur temporär auf dem GitHub Runner mit Modus `0600` abgelegt und nach dem Job entfernt.

## Langfristiges Deployment-Modell

Dieselbe Trennung gilt später für Staging und Production:

- Erstprovisionierung: initialer Provider-Zugang -> verwalteter Zugang.
- laufender Betrieb: ausschließlich verwalteter Deployment-/Bootstrap-Benutzer.
- Infrastrukturänderungen werden deklarativ und idempotent angewendet; ein Update installiert den Server nicht neu.
- Fresh-Host-Tests bleiben separate Abnahmetests für Neuaufbauten und Disaster-Recovery-Szenarien.

Damit kann derselbe Infrastructure-Stand kontrolliert auf bestehende Server ausgerollt werden, ohne den initialen Root-/Provider-Zugang wieder zu aktivieren.
