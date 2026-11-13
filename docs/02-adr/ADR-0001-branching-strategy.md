# ADR-0001: Branching-Strategie

- Status: proposed
- Datum: 2026-07-23
- Aktualisiert: 2026-07-26
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Das Repository muss parallele Arbeit, nachvollziehbare Reviews und kontrollierte Freigaben ermöglichen. Gleichzeitig soll der Prozess für ein kleines Team praktikabel bleiben und die unterschiedlichen Reifegrade von Entwicklung, produktionsnaher Prüfung und produktiver Freigabe klar abbilden.

Ein ausschließlich auf `main` ausgerichteter trunk-basierter Workflow bildet diese Anforderungen nicht ausreichend ab. Für die Merchfactory Infrastructure Platform werden drei dauerhafte Branches benötigt, die den definierten Promotion- und Freigabefluss widerspiegeln.

## Entscheidung

Wir verwenden ein dreistufiges Branch-Modell mit folgenden dauerhaften Branches:

- `development`: Integrationsbranch für laufende und fachlich abgeschlossene Änderungen,
- `staging`: freigegebener Stand für produktionsnahe Prüfung,
- `main`: produktiv freigegebener und versionierbarer Stand.

Kurzlebige Arbeitsbranches werden grundsätzlich von `development` erstellt. Zulässige Präfixe sind insbesondere:

- `feature/`
- `fix/`
- `docs/`
- `chore/`
- `refactor/`
- `test/`
- `agent/`

Der reguläre Integrations- und Promotion-Fluss lautet:

```text
Arbeitsbranch -> development -> staging -> main
```

Änderungen aus Arbeitsbranches werden über Pull Requests nach `development` integriert. Freigaben nach `staging` und `main` erfolgen über separate Promotion-Pull-Requests.

Direkte Änderungen auf `development`, `staging` oder `main` sind nicht vorgesehen. Eine direkte Promotion von `development` nach `main` ist nur in ausdrücklich dokumentierten Übergangs- oder Notfallsituationen zulässig.

Kurzlebige Branches werden nach erfolgreichem Merge manuell gelöscht. Die dauerhaften Branches `development`, `staging` und `main` dürfen nicht gelöscht oder durch Force Push überschrieben werden.

## Konsequenzen

### Positiv

- Entwicklungs-, Prüf- und Produktionsstände sind klar voneinander getrennt.
- Änderungen können stufenweise freigegeben und nachvollziehbar geprüft werden.
- Pull Requests bilden eine vollständige Review- und Auditspur.
- CI/CD kann je Branch unterschiedliche Prüfungen und Deployment-Ziele verwenden.
- Produktive Releases lassen sich gezielt aus einem zuvor geprüften Staging-Stand erzeugen.

### Negativ

- Promotion-Pull-Requests erzeugen zusätzlichen Prozessaufwand.
- Merge-Commits können dazu führen, dass Branches trotz identischem Inhalt unterschiedliche Commit-Stände anzeigen.
- Dauerhafte Branches müssen regelmäßig synchronisiert und gegen unbeabsichtigtes Löschen geschützt werden.

### Risiken und Maßnahmen

- Risiko unbeabsichtigter Branch-Divergenz: Promotion ausschließlich in der festgelegten Richtung durchführen.
- Risiko versehentlicher Löschung dauerhafter Branches: automatische Löschung von Head-Branches bleibt deaktiviert, bis technische Schutzregeln für private Repositories verfügbar sind.
- Risiko direkter Änderungen: Branch Protection beziehungsweise Rulesets werden in v0.3 eingerichtet, sobald Tarif und Repository-Einstellungen dies zulassen.
- Risiko großer Pull Requests: Änderungen werden nach Issues und klaren Deliverables zerlegt.

## Betrachtete Alternativen

### Trunk-basierter Workflow mit ausschließlich `main`

- Vorteil: geringe langfristige Branch-Divergenz und einfacher Prozess.
- Nachteil: keine klare Trennung zwischen laufender Entwicklung, produktionsnaher Prüfung und produktiver Freigabe.
- Grund der Ablehnung: bildet den geplanten Deployment- und Freigabeprozess nicht ausreichend ab.

### Klassisches GitFlow

- Vorteil: explizite Develop-, Release- und Hotfix-Branches.
- Nachteil: zusätzlicher Prozessaufwand und höhere Merge-Komplexität.
- Grund der Ablehnung: für Teamgröße und Projektphase zu schwergewichtig; das dreistufige Modell deckt die benötigten Reifegrade mit weniger Komplexität ab.

## Referenzen

- Issue #4
- Epic #2
- `docs/01-architecture.md`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/10-development-guidelines.md`
