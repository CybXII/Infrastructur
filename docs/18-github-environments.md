# GitHub Environments und Deployment-Governance

## Zweck

Dieses Dokument definiert das Deployment-Modell für Entwicklungs-, Staging- und Produktionsumgebungen unter der Vorgabe, den GitHub-Betrieb zunächst ohne kostenpflichtige Zusatzfunktionen umzusetzen.

Dabei wird zwischen drei Dingen unterschieden:

- fachlichen Zielumgebungen,
- GitHub Environments als zusätzlicher Schutzschicht,
- Repository-Secrets als aktuell nutzbare Secret-Basis für Deployments.

## Fachliche Umgebungen

Die fachlichen Zielumgebungen sind:

- `development` – Integration und technische Validierung
- `staging` – produktionsnahe Prüfung und Release-Abnahme
- `production` – freigegebener Produktivbetrieb

Die zugehörigen Branches sind:

| Umgebung | Branch | Zweck |
|---|---|---|
| Development | `development` | Integrationsstand |
| Staging | `staging` | Release Candidate |
| Production | `main` | produktiv freigegebener Stand |

## Aktueller kostenfreier Betriebsmodus

GitHub Environments mit Environment-Secrets, Required Reviewers, Wait Timern und technisch erzwungenen Deployment-Branch-Regeln werden im aktuellen Tarif nicht vorausgesetzt.

Automatisierte Deployments bleiben dennoch möglich. Dafür werden Repository-Secrets verwendet und über eindeutige Präfixe nach Zielumgebung getrennt.

Beispiele:

```text
DEVELOPMENT_SSH_HOST
DEVELOPMENT_SSH_USER
DEVELOPMENT_SSH_PRIVATE_KEY

STAGING_SSH_HOST
STAGING_SSH_USER
STAGING_SSH_PRIVATE_KEY

PRODUCTION_SSH_HOST
PRODUCTION_SSH_USER
PRODUCTION_SSH_PRIVATE_KEY
```

Weitere Secrets folgen demselben Schema, beispielsweise:

```text
STAGING_DEPLOY_PATH
STAGING_API_TOKEN
PRODUCTION_DEPLOY_PATH
PRODUCTION_API_TOKEN
```

## Eigenschaften von Repository-Secrets

Repository-Secrets stehen Workflows dieses Repositorys zur Verfügung, sobald sie ausdrücklich über den `secrets`-Kontext referenziert werden.

Die Präfixe sorgen für eine klare fachliche Trennung, stellen jedoch keine harte technische Zugriffssperre zwischen Umgebungen dar. Ein Workflow könnte grundsätzlich auch ein Secret mit einem anderen Präfix referenzieren.

Diese Einschränkung wird durch folgende Maßnahmen kompensiert:

- getrennte Workflow-Dateien je Zielumgebung
- branchgebundene Trigger
- explizite Secret-Weitergabe
- kein `secrets: inherit`
- getrennte SSH-Schlüssel und Zugangsdaten je Umgebung
- serverseitiges Least Privilege
- keine Deployment-Secrets in Pull-Request-Workflows
- keine Deployments aus Arbeitsbranches

## Empfohlene Workflow-Struktur

```text
.github/workflows/
├── deploy-development.yml
├── deploy-staging.yml
├── deploy-production.yml
└── reusable-deployment.yml
```

Die drei auslösenden Workflows definieren jeweils:

- den erlaubten Branch,
- die Zielumgebung,
- die passenden Repository-Secrets,
- die Concurrency-Gruppe,
- die Berechtigungen.

Der wiederverwendbare Workflow enthält die gemeinsame Deployment-Logik, erhält aber nur die ausdrücklich weitergegebenen Secrets.

Beispiel für Staging:

```yaml
jobs:
  deploy:
    uses: ./.github/workflows/reusable-deployment.yml
    with:
      target_environment: staging
    secrets:
      ssh_host: ${{ secrets.STAGING_SSH_HOST }}
      ssh_user: ${{ secrets.STAGING_SSH_USER }}
      ssh_private_key: ${{ secrets.STAGING_SSH_PRIVATE_KEY }}
```

Der wiederverwendbare Workflow deklariert nur die benötigten Werte:

```yaml
on:
  workflow_call:
    inputs:
      target_environment:
        required: true
        type: string
    secrets:
      ssh_host:
        required: true
      ssh_user:
        required: true
      ssh_private_key:
        required: true
```

## Branch- und Deployment-Zuordnung

Der reguläre Flow bleibt:

```text
Arbeitsbranch -> development -> staging -> main
```

Die Deployment-Zuordnung lautet:

```text
Push auf development -> Development-Deployment
Push auf staging     -> Staging-Deployment
Push auf main        -> Production-Deployment
```

Produktive Deployments dürfen nur auf einem Commit basieren, der über `staging -> main` freigegeben wurde.

## Verbindliche Sicherheitsregeln

- Deployment-Workflows laufen nicht bei `pull_request`.
- Pull-Request-Workflows erhalten keine Deployment-Secrets.
- Production-Secrets werden nur im Production-Workflow referenziert.
- Für jede Umgebung werden eigene SSH-Schlüssel und technische Benutzer verwendet.
- Kein Deployment-Schlüssel erhält Root-Zugriff.
- Der Production-Schlüssel darf ausschließlich auf Production verwendet werden.
- Der Staging-Schlüssel darf ausschließlich auf Staging verwendet werden.
- Serverzugänge werden auf die für das Deployment notwendigen Befehle und Pfade begrenzt.
- Secrets dürfen nicht in Logs ausgegeben werden.
- `.env`-Dateien und private Schlüssel werden nicht im Repository gespeichert.
- Secret-Rotation und Widerruf müssen dokumentiert werden.

## Berechtigungsmodell

Deployment-Workflows folgen Least Privilege:

```yaml
permissions:
  contents: read
```

Zusätzliche GitHub-Token-Berechtigungen werden nur gesetzt, wenn ein konkreter Deployment-Schritt sie benötigt.

Die eigentliche Zugriffstrennung erfolgt primär über:

- getrennte Secrets,
- getrennte technische Benutzer,
- getrennte SSH-Schlüssel,
- getrennte Zielserver,
- eingeschränkte Serverberechtigungen.

## Deployment-Anforderungen

Jeder spätere Deployment-Workflow muss mindestens enthalten:

- eindeutige Zielumgebung
- branchgebundenen Trigger oder bewusstes `workflow_dispatch`
- unveränderlichen Commit-SHA
- Concurrency pro Zielumgebung
- Preflight-Prüfung
- Healthcheck oder Smoke Test
- Fehlerbehandlung
- dokumentierten Rollback-Pfad
- minimale Berechtigungen
- keine Ausgabe von Secrets

Für Production ist zusätzlich eine bewusste Freigabe im Promotion-Prozess erforderlich. Solange keine technische Environment-Freigabe verfügbar ist, erfolgt diese organisatorisch über den Pull Request `staging -> main`.

## Rolle von GitHub Environments

GitHub Environments bleiben eine mögliche spätere zusätzliche Schutzschicht.

Sie können künftig ergänzen:

- Environment-Secrets
- Deployment-Branch-Regeln
- Required Reviewers
- Wait Timer
- getrennte Deployment-Historie je Environment

Sie sind jedoch keine Voraussetzung für funktionierende CI/CD-Deployments. Das aktuelle kostenfreie Modell basiert auf Repository-Secrets, klar getrennten Workflows und serverseitigem Least Privilege.

## Kostenkontrolle

Das aktuelle Modell verwendet:

- GitHub-hosted Standardrunner
- Repository-Secrets
- keine größeren Runner
- keine kostenpflichtigen Environment-Schutzfunktionen
- keine unnötigen Artefakte

Ein Tarifwechsel wird erst geprüft, wenn Environment-spezifische technische Freigaben oder eine stärkere Secret-Isolation einen konkreten Sicherheits- oder Betriebsmehrwert bringen.

## Status des aktuellen Arbeitspakets

Für den aktuellen Projektstand gilt:

- fachliche Umgebungen sind definiert
- Branch-Zuordnung ist festgelegt
- Repository-Secrets sind als zulässige kostenfreie Secret-Basis definiert
- Namenskonventionen je Umgebung sind festgelegt
- Sicherheitsgrenzen und Workflow-Struktur sind dokumentiert
- GitHub Environments bleiben optional
- aktive Deployment-Workflows und echte Secrets werden in separaten Arbeitspaketen eingeführt

## Referenzen

- `docs/03-server-layout.md`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/14-branch-protection.md`
- `docs/17-github-actions-foundation.md`
- Issue #32
- Epic #23
