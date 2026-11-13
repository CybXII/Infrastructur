# Konfigurationsstandards

## Zweck

Dieses Dokument definiert verbindliche Regeln für Konfigurationsdateien, Variablen, Defaults, Secrets, Prioritäten und Validierung.

## Grundprinzipien

Konfiguration ist explizit, reproduzierbar, versionierbar und von Secrets getrennt. Ungültige oder unvollständige Konfiguration führt zu einem kontrollierten Abbruch statt zu stillen Ersatzwerten.

## Bevorzugte Formate

| Zweck | Format |
|---|---|
| deklarative Infrastruktur und Anwendungen | YAML (`.yaml`) |
| strukturierter Datenaustausch | JSON |
| einfache Toolkonfiguration | TOML oder INI, wenn vom Werkzeug vorgesehen |
| Umgebungsvariablen-Beispiel | `.env.example` |
| Shell-Konfiguration | nur für klar begrenzte Shell-Anwendungsfälle |

Neue YAML-Dateien verwenden `.yaml`. Ökosystembedingte Standardnamen dürfen abweichen.

## Dateiaufbau

Konfigurationsdateien enthalten:

1. kurze Zweckbeschreibung, sofern Kommentare unterstützt werden
2. logisch gruppierte Schlüssel
3. dokumentierte Einheiten
4. explizite Defaults
5. keine auskommentierten Altstände
6. keine Secrets

Beispiel:

```yaml
service:
  environment: prd
  log_level: info

http:
  connect_timeout_seconds: 5
  request_timeout_seconds: 30
  max_retries: 3
```

## Schlüssel und Variablen

YAML-, JSON- und Ansible-Schlüssel verwenden `snake_case`. Umgebungsvariablen verwenden `UPPER_SNAKE_CASE`.

```text
request_timeout_seconds
backup_retention_days
SHOPIFY_API_URL
PRODUCTION_SSH_HOST
```

Namen enthalten Einheit oder Format, wenn sonst Mehrdeutigkeit entsteht:

```text
interval_seconds
retention_days
max_size_bytes
```

Unklare Namen wie `timeout`, `value`, `flag` oder `config2` sind nicht zulässig.

## Priorität und Vererbung

Von niedrig nach hoch gilt:

```text
integrierter sicherer Default
-> globale Repository-Konfiguration
-> Umgebungskonfiguration
-> Standort- oder Rollenkonfiguration
-> Host- oder Service-Override
-> zur Laufzeit injizierte Variable
```

Ein höherer Wert überschreibt nur den konkret benötigten Schlüssel. Ganze Konfigurationsblöcke werden nicht ohne Not dupliziert.

Host-spezifische Overrides benötigen eine dokumentierte technische Begründung.

## Defaults

Ein Default ist nur zulässig, wenn er:

- sicher ist,
- in allen betroffenen Umgebungen sinnvoll bleibt,
- keine produktive Identität oder Zugangsdaten enthält,
- dokumentiert ist,
- durch Validierung geprüft wird.

Für sicherheitskritische oder umgebungsspezifische Werte gibt es keinen stillen Default. Beispiele:

```text
PRODUCTION_SSH_HOST
DATABASE_PASSWORD
BACKUP_ENCRYPTION_KEY
PUBLIC_DOMAIN
```

Fehlende Pflichtwerte führen vor dem Start oder Deployment zum Abbruch.

## Secrets

Secrets werden getrennt von normaler Konfiguration verwaltet.

Zulässig:

- GitHub Repository-Secrets mit Umgebungspräfix
- verschlüsselte Ansible-Vault-Dateien nach gesonderter Einführung
- geschützte serverseitige Secret-Dateien außerhalb des Repositorys
- Secret-Manager, sobald eingeführt

Nicht zulässig:

- Secrets in YAML-, JSON- oder Compose-Dateien im Git-Repository
- echte Werte in `.env.example`
- Tokens in Kommandozeilenargumenten oder Logs
- gemeinsame Production-Secrets für Development oder Staging

Beispieldateien verwenden Platzhalter:

```dotenv
SHOPIFY_API_TOKEN=replace-me
DATABASE_PASSWORD=replace-me
```

## Umgebungsvariablen

Umgebungsvariablen werden beim Start typisiert und validiert. Texte wie `true`, `false`, Zahlen, URLs und Listen werden nicht ungeprüft weiterverwendet.

Boolean-Werte akzeptieren ausschließlich dokumentierte Formen, bevorzugt:

```text
true
false
```

Leere Zeichenketten gelten bei Pflichtwerten als fehlend.

## Validierung

Validierung erfolgt möglichst früh:

1. Syntax prüfen
2. Pflichtfelder prüfen
3. Datentypen prüfen
4. Wertebereiche und erlaubte Werte prüfen
5. Beziehungen zwischen Feldern prüfen
6. externe Abhängigkeiten in einem getrennten Preflight prüfen

Beispiele:

- Port zwischen 1 und 65535
- Timeout größer als 0
- Production darf keine Development-Domain verwenden
- `bkp`-Volumes benötigen eine Backupmethode
- TLS-Endpunkte benötigen eine gültige Domain

Für wiederverwendete Formate werden Schemas eingesetzt, beispielsweise JSON Schema oder werkzeugspezifische Linter.

## Fehlerverhalten

Ungültige Konfiguration führt zu:

- eindeutigem Fehlertext
- betroffenem Schlüssel oder Pfad
- erwarteter Form oder zulässigem Bereich
- nicht geheimem Ist-Zustand, sofern sicher
- Exit Code ungleich 0

Nicht zulässig sind stilles Ignorieren, automatisches Raten oder Rückfall auf unsichere Defaults.

Beispiel:

```text
configuration_invalid: http.request_timeout_seconds muss eine positive Ganzzahl sein
```

Secret-Werte werden auch bei Validierungsfehlern nicht ausgegeben.

## Änderungen und Kompatibilität

Konfigurationsänderungen werden klassifiziert:

- neuer optionaler Schlüssel mit sicherem Default: kompatibel
- neuer Pflichtschlüssel: Migration erforderlich
- Umbenennung oder Entfernung: Breaking Change
- geänderte Bedeutung oder Einheit: Breaking Change

Breaking Changes werden in Conventional Commits und Release Notes gekennzeichnet. Migration und Rollback sind zu dokumentieren.

## Beispiele und Vorlagen

Zu jeder komplexen Konfiguration gehört eine sichere Beispiel- oder Referenzdatei. Beispiele müssen syntaktisch gültig und frei von echten internen Daten sein.

## Tests

Mindestens geprüft werden:

- kleinste gültige Konfiguration
- vollständige Beispielkonfiguration
- fehlender Pflichtwert
- falscher Typ und ungültiger Wertebereich
- unbekannter Schlüssel, sofern verboten
- Secret-Redaction
- Umgebungskonflikt
- kompatibles Override-Verhalten

## Definition of Done für Issue #46

- Formate und Namensregeln sind dokumentiert.
- Priorität und Vererbung sind eindeutig.
- sichere Defaults und Pflichtwerte sind abgegrenzt.
- Secrets sind klar getrennt.
- Validierung und kontrolliertes Fehlerverhalten sind definiert.

## Referenzen

- `docs/18-github-environments.md`
- `docs/25-file-directory-naming-conventions.md`
- `docs/26-environments-host-groups.md`
- Issue #46
- Epic #35
