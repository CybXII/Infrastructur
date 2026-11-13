# Secret-Management

## Zweck

Dieses Dokument definiert das verbindliche Secret-Management der Merchfactory Container Platform ab v0.5. Es setzt Issue #73 um und konkretisiert die Security-Baseline aus `docs/04-security.md` sowie die Datenklasse D aus `docs/50-volume-persistence-model.md`.

Ziel ist, dass Passwörter, Tokens, private Schlüssel und vergleichbare Credentials niemals Bestandteil des Repository-Inhalts, eines Container-Images oder normaler Deployment-Logs werden.

## Grundmodell

Das Plattformmodell trennt drei Ebenen:

1. **Secret-Quelle** – autorisierter Ursprungsort eines Secret-Wertes.
2. **Host-Runtime-Kopie** – restriktive Datei unter `/srv/merchfactory/secrets`.
3. **Container-Injection** – explizite Compose-Freigabe nach `/run/secrets/<name>`.

Ein Container erhält ausschließlich die Secrets, die im jeweiligen Service unter `secrets:` freigegeben wurden.

## Verbindlicher Hostpfad

Runtime-Secrets liegen außerhalb des Repository-Checkouts unter:

```text
/srv/merchfactory/secrets/
└── <service>/
    └── <secret-name>
```

Der Root-Pfad wird durch die Storage-Rolle mit Modus `0700` vorbereitet.

Secret-Dateien:

- enthalten ausschließlich den Secret-Wert,
- werden standardmäßig mit `0400` angelegt,
- besitzen die numerische UID/GID des Prozesses, der das Secret im Container lesen muss,
- werden atomar ersetzt,
- werden nicht über Kommandozeilenargumente übergeben,
- werden nicht in normale Datei- oder Volume-Backups aufgenommen.

Für einen technisch erforderlichen Gruppenlesezugriff ist `0440` zulässig und servicebezogen zu begründen.

## Secret-Quellen

### GitHub Environment Secrets

GitHub Environment Secrets sind für kontrollierte, automatisierte Deployments zulässig.

Regeln:

- Development, Staging und Production verwenden getrennte Environments.
- Produktionszugriff benötigt die im CI/CD-Modell vorgesehene Freigabe.
- Ein Workflow erhält nur die für den konkreten Deployment-Schritt benötigten Secrets.
- Secret-Werte dürfen nicht mit `echo`, `set -x`, Debug-Ausgaben oder Artefakten ausgegeben werden.
- Ein GitHub Secret ist kein Recovery-Tresor, da der gespeicherte Wert später nicht wieder ausgelesen werden kann.

### Autorisierter Recovery-/Credential-Tresor

Geschäftskritische Secrets benötigen zusätzlich eine getrennte Recovery-Quelle, aus der ein berechtigter Operator den Wert bei vollständigem Hostverlust wiederherstellen kann.

Die konkrete Vault-/Passwortmanager-Technologie ist noch nicht festgelegt. Unabhängig vom Produkt gelten:

- getrennt vom Produktivhost,
- verschlüsselt,
- Zugriff nach Least Privilege,
- Notfallzugriff dokumentiert,
- kritische Recovery-Zugänge nicht von genau dem System abhängig machen, das wiederhergestellt werden soll,
- Recovery-Test mindestens halbjährlich gemäß Disaster-Recovery-Konzept.

### Manuelle Bootstrap-/Recovery-Eingabe

Für Bootstrap oder Notfallwiederherstellung darf ein Secret kontrolliert über stdin an das Installationswerkzeug übergeben werden. Der Wert darf dabei nicht als Kommandozeilenargument erscheinen.

Beispiel:

```bash
printf '%s' "$SECRET_FROM_APPROVED_SOURCE" \
  | sudo bash platform/secrets/scripts/install-secret-file.sh \
      example-service api-token 1000 1000
```

Der Variablenwert darf nicht aus einer committed `.env`-Datei stammen.

## Compose-Injection

Docker Compose Secrets werden dateibasiert verwendet:

```yaml
services:
  app:
    secrets:
      - source: app-api-token
        target: api-token

secrets:
  app-api-token:
    file: ${APP_API_TOKEN_FILE:-/srv/merchfactory/secrets/app/api-token}
```

Im Container erscheint das Secret unter:

```text
/run/secrets/api-token
```

Anwendungen sollen Secrets nach Möglichkeit direkt als Datei lesen oder eine vom Image unterstützte `*_FILE`-Konvention verwenden.

Secret-Werte werden nicht als normale Environment-Variablen in Compose-Dateien injiziert.

### Wichtige Rechte-Eigenschaft

Bei file-basierten Compose-Secrets wird die Quelldatei als Bind Mount verwendet. UID/GID/Mode aus der Compose-Long-Syntax werden für eine `file:`-Quelle nicht zuverlässig umgemappt. Deshalb werden Ownership und Mode verbindlich auf dem Host vorbereitet.

## Zugriffmodell

### Operator

Ein Operator darf Secret-Dateien nur über kontrollierte `sudo`-Vorgänge installieren oder rotieren. Normale Repository- und Deployment-Lesezugriffe berechtigen nicht automatisch zum Lesen produktiver Secrets.

### Docker Engine

Der Docker-Daemon benötigt Hostzugriff auf die Quelldatei, um sie in den Container einzubinden.

### Service

Der Service erhält nur explizit deklarierte Secrets. Andere Secret-Dateien werden nicht in den Container gemountet.

### CI/CD

CI/CD darf Secret-Werte nur in dem Job erhalten, der sie tatsächlich benötigt. Pull Requests aus nicht vertrauenswürdigen Quellen erhalten keine produktiven Secrets.

## Secret-Inventar

Zu jedem Secret werden ausschließlich Metadaten versioniert, niemals der Wert.

Mindestens:

- stabile Secret-ID,
- betroffener Service,
- Zweck,
- Runtime-Ziel,
- verantwortliche Rolle,
- Rotationsauslöser bzw. Intervall,
- Recovery erforderlich: ja/nein,
- Neustart/Reload nach Rotation erforderlich: ja/nein.

Die Referenz liegt unter `examples/services/example-service/configuration/secrets.yaml.example`.

## Installation

`platform/secrets/scripts/install-secret-file.sh`:

- liest den Wert ausschließlich von stdin,
- verweigert leere Eingaben,
- validiert Service- und Secret-Namen gegen Path Traversal,
- schreibt zuerst eine temporäre Datei im Zielverzeichnis,
- setzt Owner, Group und Mode vor der Aktivierung,
- ersetzt den Zielwert atomar,
- gibt nur den Zielpfad, niemals den Secret-Wert aus.

## Rotation

Standardablauf:

1. Rotation beim externen System vorbereiten; wenn möglich alten und neuen Credential kurzzeitig parallel gültig halten.
2. Neuen Wert aus autorisierter Quelle beziehen.
3. Host-Runtime-Datei atomar ersetzen.
4. Betroffenen Container kontrolliert neu erstellen. Bei file-basierten Compose-Secrets wird nicht auf eine Live-Aktualisierung des bereits gemounteten Secret-Files vertraut.
5. technische und fachliche Funktion prüfen.
6. alten Credential am Quellsystem widerrufen.
7. Recovery-Kopie aktualisieren.
8. Rotationsdatum und Ergebnis dokumentieren, jedoch niemals den Wert.

Sofortige Rotation ist erforderlich bei:

- möglicher Offenlegung in Git, Logs oder Artefakten,
- kompromittiertem Benutzer-/Servicekonto,
- Verlust eines Systems mit ungeschütztem Zugriff,
- Rollenwechsel/Austritt einer Person mit Secret-Zugriff,
- Anbieter- oder Sicherheitsvorfall mit Credential-Bezug.

## Notfallzugriff

Break-Glass-Zugriff wird nur für Recovery oder Security-Incidents verwendet.

Anforderungen:

- mindestens zwei berechtigte Personen oder ein gleichwertig dokumentiertes organisatorisches Verfahren,
- Zugriff auf Recovery-Credentials auch bei Ausfall von GitHub oder des Produktions-VPS,
- jeder Notfallzugriff wird nachträglich dokumentiert,
- nach Verwendung werden betroffene Notfall-Credentials bewertet und bei Bedarf rotiert,
- Recovery-Verfahren werden mindestens halbjährlich getestet.

## Umgang mit versehentlich veröffentlichten Secrets

Ein Secret, das in Git, einem Log oder Artefakt sichtbar war, gilt als kompromittiert.

Reihenfolge:

1. betroffenen Credential widerrufen oder rotieren,
2. Auswirkung und Nutzungsprotokolle prüfen,
3. neue Runtime- und Recovery-Werte bereitstellen,
4. erst danach gegebenenfalls Git-Historie oder Artefakte bereinigen,
5. Folgeprüfung durchführen.

Das Entfernen eines Wertes aus der Git-Historie ersetzt niemals die Rotation.

## Repository-Schutz

Das Repository enthält einen eigenen Scanner:

```bash
python3 scripts/check-secrets.py --tree --history
```

Er prüft:

- aktuell getrackte Dateien,
- erreichbare Git-Historie,
- bekannte Token-/Key-Formate,
- private Schlüssel,
- verdächtige hochentropische Werte in typischen Secret-Zuweisungen.

Bei einem Treffer werden nur Fundort und Regelname ausgegeben, nicht der erkannte Wert.

CI checkt für diesen Test die vollständige Historie aus. Verdächtige Funde blockieren den Merge.

## Logging

Verboten:

- Secret-Werte in Shell-Debugausgaben,
- `set -x` während Secret-Verarbeitung,
- Secret-Inhalte in GitHub Actions Outputs,
- Secret-Werte in Monitoring-Labels,
- Secret-Dateien als Build-/Testartefakt,
- vollständige Environment-Dumps in Jobs mit Secrets.

Fehlermeldungen nennen ausschließlich Secret-ID, Zielpfad oder Metadaten.

## Backup und Recovery

Runtime-Dateien unter `/srv/merchfactory/secrets` sind keine normale Backup-Quelle. Klasse-D-Recovery erfolgt aus dem getrennten verschlüsselten Credential-/Recovery-Tresor.

Dadurch wird verhindert, dass ein reguläres Volume-Backup automatisch eine zweite unkontrollierte Sammlung produktiver Credentials erzeugt.

ACME-Schlüsselmaterial bleibt ein technischer Sonderfall: dessen bestehendes geschütztes Backup-Verfahren wird weiterhin verwendet und in die übergreifende Secret-Recovery-Strategie eingeordnet.

## Odoo-Ausblick

Für das spätere Odoo-Deployment betrifft dieses Modell unter anderem:

- PostgreSQL-Passwort,
- Odoo-Admin-/Master-Passwort,
- SMTP-Credentials,
- externe API-Tokens,
- Backup-Zugangsdaten.

Welche dieser Werte Odoo direkt aus Dateien lesen kann und wo ein sicherer Start-/Konfigurationsadapter erforderlich ist, wird im Odoo-Service-Deployment konkretisiert. Die Secret-Werte selbst bleiben unabhängig davon außerhalb des Repositorys.

## Abgrenzung

Nicht Bestandteil dieses Tasks sind:

- Auswahl eines konkreten externen Vault-Produkts,
- Odoo-spezifische Secret-Verarbeitung,
- vollständiger Deployment-Workflow,
- Registry- und Image-Scanning (#74),
- vollständiges Service-Template (#75),
- Backup-Verschlüsselungsimplementierung.
