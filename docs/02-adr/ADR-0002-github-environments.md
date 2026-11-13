# ADR-0002: GitHub Environments

- Status: rejected
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Ursprünglich war vorgesehen, GitHub Environments für development, staging und
production zu verwenden, um Secrets, Variablen und Freigaben je Zielumgebung zu
trennen.

Für die aktuelle Projektphase soll diese Funktion nicht vorausgesetzt werden,
da sie abhängig vom GitHub-Plan zusätzliche Kosten beziehungsweise
Plan-Abhängigkeiten verursachen kann. Die Infrastructure Platform soll auch mit
Repository Secrets und Repository Variables vollständig betreibbar bleiben.

## Entscheidung

Der in dieser ADR ursprünglich vorgeschlagene verpflichtende Einsatz von GitHub
Environments wird nicht umgesetzt.

Aktuell gelten stattdessen folgende Regeln:

- keine environment-Zuordnung in GitHub-Actions-Jobs
- Secrets werden als Repository Secrets verwaltet
- nicht geheime Schalter werden als Repository Variables verwaltet
- umgebungsspezifische Namen bleiben explizit, zum Beispiel
  DEVELOPMENT_BOOTSTRAP_MANAGED_HOST_ENABLED
- sicherheitskritische Freigaben werden über Workflow-Gates, Branch-Regeln und
  bewusste manuelle Maintenance-Abläufe abgebildet

Die Entscheidung kann später über eine neue ADR neu bewertet werden, wenn sich
GitHub-Plan, Kostenmodell oder Anforderungen ändern.

## Konsequenzen

### Positiv

- keine Abhängigkeit von GitHub Environments oder zusätzlichen Plan-Funktionen
- einfacherer Bootstrap der Repository-Konfiguration
- Repository Secrets und Variables reichen für den aktuellen Entwicklungs- und
  Runner-Betrieb aus

### Negativ

- geringere native GitHub-Trennung von Secrets zwischen Zielumgebungen
- Produktionsfreigaben müssen über andere technische und organisatorische
  Gates abgesichert werden

## Betrachtete Alternativen

### GitHub Environments verpflichtend verwenden

- Vorteil: native Umgebungsbindung, Freigaben und Secret-Trennung.
- Nachteil: zusätzliche Plan-/Kostenabhängigkeit und mehr Konfigurationspflege.
- Grund der Ablehnung: für die aktuelle Projektphase nicht erforderlich.

## Referenzen

- Issue #4
- Epic #2
- docs/01-architecture.md
- ADR-0010
