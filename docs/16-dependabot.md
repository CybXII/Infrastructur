# Dependabot-Konfiguration

## Zweck

Dependabot überwacht die im Repository verwendeten Abhängigkeiten und erstellt kontrollierte Update-Pull-Requests. Für den aktuellen Projektstand betrifft dies ausschließlich GitHub Actions.

## Erfasstes Ökosystem

Aktiviert ist:

```text
github-actions
```

Dependabot durchsucht die Workflow-Dateien unter `.github/workflows/` nach verwendeten Actions und deren Versionen.

Weitere Paketökosysteme werden erst ergänzt, wenn im Repository tatsächlich entsprechende Manifestdateien vorhanden sind, beispielsweise für Python, npm, Docker oder Terraform.

## Zeitplan

Reguläre Versionsprüfungen erfolgen wöchentlich:

- Wochentag: Montag
- Uhrzeit: 06:00 Uhr
- Zeitzone: `Europe/Berlin`
- Zielbranch: `development`

Damit bleiben automatische Update-PRs im regulären Arbeits- und Promotion-Flow:

```text
Dependabot-PR -> development -> staging -> main
```

## Gruppierung

Minor- und Patch-Updates für GitHub Actions werden in einer gemeinsamen Gruppe zusammengefasst:

```text
github-actions-minor-patch
```

Major-Updates werden nicht gruppiert. Sie erscheinen als separate Pull Requests, damit Breaking Changes gezielt geprüft werden können.

## Begrenzung offener Pull Requests

Dependabot darf maximal fünf reguläre Versionsupdate-PRs gleichzeitig offen halten.

Die Begrenzung reduziert PR-Rauschen und verhindert, dass automatische Wartungsupdates die manuell geplante Arbeit verdrängen.

## Labels und Zuständigkeit

Automatisch erzeugte Pull Requests erhalten:

- `dependencies`
- `ci-cd`

Sie werden `CybXII` zugewiesen.

Commit-Nachrichten verwenden den Präfix:

```text
ci(deps)
```

Damit entsprechen sie den im Repository festgelegten Conventional-Commit-Regeln.

## Sicherheitsupdates

Dependabot Security Updates sind von regulären Versionsupdates zu unterscheiden.

- Reguläre Versionsupdates folgen dem Zeitplan aus `.github/dependabot.yml`.
- Sicherheitsupdates werden ereignisbezogen erzeugt, wenn GitHub eine verwundbare Abhängigkeit erkennt und die Security-Update-Funktion für das Repository aktiviert ist.
- Sicherheitsupdates sind fachlich höher zu priorisieren als normale Wartungsupdates.
- Vor dem Merge bleiben Tests, Review und der reguläre Promotion-Prozess verbindlich.

Die Aktivierung von Dependabot Alerts und Dependabot Security Updates erfolgt in den Repository-Einstellungen unter den Sicherheitsfunktionen. Die Konfigurationsdatei allein aktiviert diese Repository-Einstellungen nicht.

## Prüfanforderungen

Jeder Dependabot-PR wird wie ein normaler Pull Request behandelt:

1. Release Notes und Breaking Changes prüfen.
2. Repository- und Governance-Checks kontrollieren.
3. Berechtigungs- und Security-Auswirkungen bewerten.
4. Keine automatischen Merges aktivieren.
5. Nach Merge nach `development` regulär über `staging` nach `main` promoten.

## Kostenkontrolle

Dependabot selbst erzeugt keine kostenpflichtigen größeren Runner. Die durch Pull Requests ausgelösten Tests laufen weiterhin auf den vorhandenen GitHub-hosted Standardrunnern innerhalb des verfügbaren Freikontingents.

Die maximale Anzahl offener PRs und die Gruppierung von Minor- und Patch-Updates reduzieren unnötige Workflow-Läufe.

## Erweiterung

Neue Paketökosysteme werden nur ergänzt, wenn:

- relevante Manifestdateien vorhanden sind,
- Update- und Teststrategie geklärt ist,
- Zielbranch und Gruppierung festgelegt wurden,
- der zusätzliche CI-Verbrauch vertretbar ist.

## Referenzen

- `.github/dependabot.yml`
- `.github/workflows/tests.yml`
- `.github/workflows/governance.yml`
- `docs/14-branch-protection.md`
- `docs/15-branch-commit-conventions.md`
- Issue #30
- Epic #23
