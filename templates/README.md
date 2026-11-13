# Templates

## Zweck

Dieses Verzeichnis enthält wiederverwendbare, nicht direkt produktiv eingesetzte Vorlagen für Dienste, Konfigurationen und Betriebsabläufe.

## Struktur

```text
templates/
  configurations/
  services/
  compose/
  systemd/
  runbooks/
```

### `configurations/`

Vorlagen für deklarative Konfigurationsdateien. Sie enthalten ausschließlich neutrale Standardwerte und eindeutig erkennbare Platzhalter.

### `services/`

Grundstrukturen für neue Dienste, einschließlich erwarteter Metadaten, Abhängigkeiten und Betriebsanforderungen.

Das verbindliche Container-Service-Template liegt unter:

```text
templates/services/container-service/
```

Es wird mit `scripts/render-service-template.py` gerendert und erzeugt eine vollständige Service-Struktur mit Compose, Routing, Monitoring, Logging, Backup, Secrets und Betriebsdokumentation. Details stehen in `docs/53-standard-service-template.md`.

### `compose/`

Wiederverwendbare Compose-Fragmente und Ausgangsdateien. Produktive Images müssen später eindeutig versioniert oder über Digests referenziert werden.

### `systemd/`

Vorlagen für systemd-Units und Timer. Benutzer, Pfade und Abhängigkeiten müssen vor Verwendung konkret festgelegt werden.

### `runbooks/`

Vorlagen für Betriebs-, Wartungs-, Störungs- und Wiederherstellungsanweisungen.

## Platzhalterkonvention

Platzhalter werden in Großbuchstaben und mit doppelten geschweiften Klammern geschrieben:

```text
{{SERVICE_NAME}}
{{ENVIRONMENT}}
{{HOSTNAME}}
{{IMAGE_REFERENCE}}
{{CONFIG_PATH}}
```

Beispielwerte müssen offensichtlich nicht produktiv sein, beispielsweise:

```text
example.invalid
192.0.2.10
example-service
CHANGE_ME
```

Produktive Domains, IP-Adressen, Kundendaten, Tokens, Passwörter, Zertifikate und private Schlüssel sind in Vorlagen nicht zulässig.

## Nutzung

Für neue containerisierte Dienste wird das Standard-Service-Template bevorzugt über den Renderer erzeugt:

```bash
python3 scripts/render-service-template.py --output <ziel> --set ...
```

Der Renderer verlangt alle im Template-Manifest deklarierten Platzhalter und verweigert unvollständige Ausgaben.

Andere Vorlagen werden weiterhin manuell übernommen:

1. geeignete Vorlage kopieren,
2. Datei in den fachlich zuständigen Bereich übernehmen,
3. alle Platzhalter ersetzen oder bewusst entfernen,
4. umgebungsspezifische Werte in `configuration/environments/` ablegen,
5. Secrets ausschließlich zur Laufzeit bereitstellen,
6. Ergebnis validieren und die zugehörige README sowie Tests ergänzen.

Vorlagen werden niemals unverändert als produktive Artefakte behandelt.

## Benennung

- Vorlagendateien tragen einen eindeutigen Suffix wie `.template`, `.example` oder `.sample`.
- Datei- und Verzeichnisnamen verwenden `kebab-case`.
- Jede neue Vorlage benötigt einen dokumentierten Zweck und einen klaren Zielbereich.

## Abgrenzung

- Produktive Konfiguration gehört nach `configuration/`.
- Deployment-Manifeste gehören nach `deployment/`.
- ausführbare Hilfslogik gehört nach `scripts/`.
- vereinfachte Referenzbeispiele gehören nach `examples/`.

## Referenzen

- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`
