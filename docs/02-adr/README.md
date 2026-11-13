# Architecture Decision Records

Dieses Verzeichnis enthält verbindliche Architecture Decision Records (ADRs) für die Merchfactory Infrastructure Platform.

## Zweck

ADRs dokumentieren technische Entscheidungen, die langfristige Auswirkungen auf Architektur, Sicherheit, Betrieb oder Wartbarkeit haben. Sie ergänzen `docs/01-architecture.md` und machen nachvollziehbar, warum eine Lösung gewählt oder verworfen wurde.

## Wann eine ADR erforderlich ist

Eine ADR ist anzulegen oder zu aktualisieren, wenn eine Entscheidung mindestens einen der folgenden Bereiche wesentlich beeinflusst:

- Architekturgrenzen oder Verantwortlichkeiten
- Sicherheitsmodell oder Vertrauensgrenzen
- Branching-, Release- oder Deployment-Strategie
- Persistenz, Backup, Restore oder Disaster Recovery
- zentrale Plattformtechnologien oder externe Abhängigkeiten
- verbindliche Standards mit langfristiger Wirkung

Reine Implementierungsdetails ohne langfristige Tragweite benötigen keine eigene ADR.

## Statuswerte

- `proposed` – Entscheidung ist vorbereitet, aber noch nicht freigegeben.
- `accepted` – Entscheidung ist verbindlich.
- `superseded` – Entscheidung wurde durch eine neuere ADR ersetzt.
- `deprecated` – Entscheidung soll nicht mehr für neue Implementierungen verwendet werden.
- `rejected` – Entscheidung wurde geprüft und verworfen.

Nur diese Statuswerte sind zulässig. Der Status wird in Kleinbuchstaben im Kopf der ADR geführt.

## Nummerierung und Dateinamen

`ADR-NNNN-kurzer-titel.md`

Regeln:

1. Die Nummer wird vierstellig und fortlaufend vergeben.
2. Die nächste Nummer ergibt sich aus der höchsten bereits verwendeten ADR-Nummer plus eins.
3. Eine vergebene Nummer wird niemals wiederverwendet, auch wenn eine ADR später verworfen oder ersetzt wird.
4. Der Kurztitel verwendet `kebab-case`.
5. `ADR-TEMPLATE.md` ist keine nummerierte Entscheidung und bleibt als Vorlage bestehen.

## Pflichtstruktur

Jede ADR enthält mindestens:

1. Titel
2. Status
3. Datum
4. Entscheider
5. Kontext
6. Entscheidung
7. Konsequenzen
8. Betrachtete Alternativen
9. Referenzen

Als Ausgangspunkt ist verbindlich `docs/02-adr/ADR-TEMPLATE.md` zu verwenden.

## Ablauf im Issue- und PR-Prozess

1. Das Architekturthema wird über das Issue-Template `Architekturthema erfassen` vorbereitet.
2. Das Issue benennt den ADR-Bedarf und verknüpft bestehende relevante ADRs.
3. Die ADR wird im Feature-Branch erstellt oder aktualisiert.
4. Der Pull Request verweist unter `Verknüpfte Issues und ADRs` auf das Issue und die ADR.
5. Neue ADRs starten grundsätzlich mit `proposed`.
6. Mit der fachlichen Freigabe im Pull Request kann der Status auf `accepted` gesetzt werden.
7. Ersetzt eine neue Entscheidung eine bestehende ADR, werden beide Dokumente über `Ersetzt` und `Ersetzt durch` miteinander verknüpft.

Für offene Issues wird im Pull Request ausschließlich `Refs #...` verwendet. Das Issue wird erst nach Promotion nach `main` und fachlicher Abnahme geschlossen.

## Änderungsregeln

Akzeptierte ADRs werden nicht rückwirkend inhaltlich umgeschrieben. Zulässig sind rein redaktionelle Korrekturen, die die Entscheidung nicht verändern.

Ändert sich eine akzeptierte Entscheidung fachlich, wird eine neue ADR angelegt. Die alte ADR erhält den Status `superseded` oder `deprecated` und verweist auf die neue ADR.

## Index

- ADR-0001 – Branching Strategy
- ADR-0002 – GitHub Environments
- ADR-0003 – Repository Directory Layout
- ADR-0004 – Infrastructure as Code
- ADR-0005 – Container Strategy
- ADR-0006 – Security First
- ADR-0007 – Backup Strategy
- ADR-0008 – Monitoring- und Observability-Stack
- ADR-0009 – Flexible Deployment-Topologien und Placement
- ADR-0010 – Self-hosted Runner Betriebs- und Bootstrap-Modell

Verknüpft mit Issue #4, Issue #26 und Epic #23.
