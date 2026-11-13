# Healthcheck-Standards

## Zweck

Dieses Dokument definiert die verbindlichen Liveness-, Readiness- und externen Probe-Standards für containerisierte Merchfactory-Dienste. Es setzt Issue #76 um und konkretisiert die Monitoring-Baseline aus `docs/08-monitoring.md`.

## Drei getrennte Signale

### Liveness

Liveness beantwortet ausschließlich:

> Läuft der Prozess noch und kann er lokal Fortschritt machen?

Umsetzung:

- Docker Compose `healthcheck`,
- lokal im Container ausgeführt,
- keine öffentlichen DNS-/Internet-Abhängigkeiten,
- keine optionalen externen APIs,
- keine Prüfung von Diensten, deren kurzer Ausfall durch Retry/Queue toleriert werden kann.

Eine zwingende lokale Runtime-Bedingung darf geprüft werden, wenn der Prozess ohne sie tatsächlich festhängt.

Standardwerte:

```text
interval: 30s
timeout: 5s
retries: 3
start_period: 10s
```

Für langsam startende Dienste darf `start_period` servicebezogen bis maximal 120 Sekunden erhöht werden. Die Abweichung wird im Service-README begründet.

### Readiness

Readiness beantwortet:

> Kann diese Instanz jetzt produktiv Requests verarbeiten?

Für über Traefik veröffentlichte HTTP-Dienste wird Readiness mit dem aktiven Traefik-Load-Balancer-Healthcheck umgesetzt.

Standardwerte:

```text
interval: 10s
timeout: 3s
expected status: 200
```

Readiness darf zwingende Abhängigkeiten prüfen, die unmittelbar für den Request-Pfad erforderlich sind, beispielsweise eine notwendige Datenbankverbindung.

Nicht in Readiness gehören optionale Analyse-, Reporting- oder Drittanbieter-Dienste, wenn die Anwendung Requests trotz deren Ausfall korrekt weiterverarbeiten kann.

### Externer Probe

Der externe Probe beantwortet:

> Ist der Dienst aus Sicht eines echten Clients über DNS, TLS, Reverse Proxy und Anwendung erreichbar?

Standardwerte:

```text
interval: 30s
timeout: 5s
expected status: 200
warning after: 2 consecutive failures
critical after: 5 consecutive failures
```

Der externe Probe läuft unabhängig vom überwachten Dienst bzw. perspektivisch unabhängig vom Zielhost.

## Fehlerfolgen

### Liveness fehlgeschlagen

Nach drei aufeinanderfolgenden Fehlern markiert Docker den Container als `unhealthy`.

Wichtig:

- `restart: unless-stopped` reagiert nicht auf den Docker-Healthstatus,
- die Plattform startet einen `unhealthy`-Container nicht automatisch neu,
- Healthstatus und Restart-Zähler werden alarmiert bzw. diagnostiziert,
- ein Neustart ist eine bewusste Betriebs- oder spätere Automationsentscheidung.

Damit werden Restart-Loops vermieden, wenn die eigentliche Ursache beispielsweise Storage, Datenbank oder Konfiguration ist.

### Readiness fehlgeschlagen

Traefik nimmt einen Backend-Server mit fehlgeschlagenem aktiven Healthcheck aus der Load-Balancer-Rotation.

Bei nur einer Instanz bedeutet das:

- der Dienst ist nicht bereit,
- Traefik darf keine normalen Requests mehr an diese Instanz senden,
- der öffentliche Dienst liefert währenddessen einen Fehlerzustand statt Traffic an ein bekannt defektes Backend.

Sobald der Readiness-Endpunkt wieder erfolgreich ist, darf die Instanz wieder in die Rotation aufgenommen werden.

Readiness-Fehler führen nicht automatisch zu Container-Neustarts.

### Externer Probe fehlgeschlagen

- 2 aufeinanderfolgende Fehlschläge: Warning/P2-Bewertung,
- 5 aufeinanderfolgende Fehlschläge: Critical/P1-Bewertung bei produktionskritischem Dienst,
- Eskalationsklasse kann servicebezogen herabgestuft werden, wenn der Dienst nicht geschäftskritisch ist.

## Dependency Checks

Abhängigkeiten werden nicht pauschal in jeden Healthcheck aufgenommen.

### Liveness

Keine Remote-Abhängigkeiten. Ein Datenbank- oder API-Ausfall darf nicht automatisch den lokalen Prozess als tot deklarieren.

### Readiness

Nur Abhängigkeiten, ohne die der aktuelle Request-Pfad nicht korrekt bedient werden kann.

### Separates Dependency Monitoring

Abhängigkeiten, die wichtig sind, aber keinen unmittelbaren Traffic-Stop rechtfertigen, erhalten eigene Metriken/Alerts.

Beispiele:

- externe API langsam,
- SMTP nicht erreichbar,
- Hintergrund-Queue wächst,
- optionaler Reporting-Dienst gestört.

## HTTP-Endpunkte

Für HTTP-Services werden getrennte Endpunkte bevorzugt:

```text
/live
/ready
```

Wenn eine Anwendung technisch nur einen gemeinsamen `/health`-Endpunkt bereitstellt, darf dieser vorübergehend für Readiness und externe Probes verwendet werden. Der Compose-Liveness-Check muss trotzdem lokal und ohne unnötige Remote-Abhängigkeiten bleiben.

Health-Endpunkte:

- liefern keine Secrets,
- liefern keine Kundendaten,
- sind schnell und deterministisch,
- verändern keinen Anwendungszustand,
- antworten bei Erfolg mit HTTP 200.

## Datenbanken, Worker und interne Dienste

Nicht jeder Service hat einen HTTP-Readiness-Endpunkt.

### Worker

- Liveness prüft, ob der Worker-Prozess läuft und lokal arbeitsfähig ist.
- Queue-/Broker-Erreichbarkeit kann Readiness-ähnlich überwacht werden, ist aber kein Traefik-Routing-Signal.
- Queue-Stau und Jobfehler werden separat alarmiert.

### Datenbanken

- Liveness prüft den lokalen Datenbankprozess mit dem nativen Werkzeug.
- Verbindungsannahme und transaktionsnahe Prüfungen werden separat überwacht.
- Datenbanken werden nicht an das Edge-Netz angeschlossen.

## Service-Template

Das Standard-Service-Template verwendet:

- Compose-Liveness: 30s / 5s / 3,
- Traefik-Readiness: 10s / 3s / HTTP 200,
- externen HTTPS-Probe: 30s / 5s.

Der Readiness-Pfad wird als `READINESS_PATH` beim Rendering angegeben.

## Tests

Die Plattform testet drei Dinge:

1. Compose-Manifeste enthalten aktive Liveness-Checks.
2. Das Service-Template rendert Readiness-Konfiguration in die Traefik-Route.
3. Der Traefik-Integrationstest setzt den Testdienst gezielt auf HTTP 500 und prüft, dass der Backend-Server aus der Rotation fällt und nach Recovery wieder erreichbar wird.

## Odoo-Ausblick

Für Odoo werden die konkreten Endpunkte beim Odoo-Service-Deployment festgelegt.

Dabei gilt:

- Liveness soll nicht wegen eines kurzzeitigen externen SMTP/API-Ausfalls fehlschlagen,
- Readiness darf die für HTTP-Anfragen zwingende Datenbankfunktion berücksichtigen,
- Worker-/Cron-Zustände werden getrennt vom Web-Readiness-Signal betrachtet.

## Referenzen

- `docs/08-monitoring.md`
- `docs/48-docker-compose-standards.md`
- `docs/53-standard-service-template.md`
- `configuration/healthcheck-policy.json`
