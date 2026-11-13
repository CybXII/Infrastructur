# Vision

## Zweck

Dieses Repository schafft eine sichere, reproduzierbare und zentral verwaltete Infrastrukturgrundlage für die Merchfactory.

Das zentrale Ziel ist, produktive Systeme nach einem Ausfall nicht manuell über Tage neu aufbauen zu müssen. Stattdessen soll eine vollständige, getestete und dokumentierte Betriebsumgebung auf einem neuen VPS oder intern gehosteten Server innerhalb weniger Minuten wiederhergestellt werden können.

## Leitbild

Die Infrastruktur wird als versioniertes Produkt behandelt.

Serverkonfigurationen, Sicherheitsstandards, Container-Definitionen, Netzwerkstrukturen, Deployment-Abläufe, Monitoring und Wiederherstellungsprozesse werden zentral im Repository beschrieben und automatisiert ausgeführt.

Ein einzelner Server ist dadurch austauschbar. Der produktive Zustand soll nicht dauerhaft an eine bestimmte Maschine gebunden sein, sondern aus Code, Konfiguration, Images und gesicherten Daten reproduzierbar entstehen.

## Geschäftlicher Nutzen

Für die Merchfactory entsteht dadurch eine belastbare Betriebsgrundlage:

- geringere Ausfallzeiten
- schneller Wiederanlauf produktiver Systeme
- einheitliche Sicherheitsstandards
- nachvollziehbare Änderungen
- reproduzierbare Serverzustände
- kontrollierte Deployments
- dokumentierte Backup- und Restore-Verfahren
- geringere Abhängigkeit von Einzelpersonen und manuellem Wissen

Das Projekt soll zugleich so allgemein und professionell aufgebaut werden, dass dieser Infrastrukturstandard später auch anderen Unternehmen der Textilveredelungs- und Merchandising-Branche angeboten werden kann.

Damit entsteht nicht nur eine interne Absicherung, sondern ein wiederverwendbares technisches Fundament für weitere Betriebe, die auf einer sicheren und automatisierbaren Plattform aufbauen möchten.

## Zielzustand

Ein neuer oder ersetzter Server soll über einen kontrollierten Workflow automatisiert vorbereitet werden können.

Der angestrebte Ablauf ist:

```text
GitHub Repository
        ↓
Zielserver über GitHub Environment auswählen
        ↓
Infrastruktur automatisiert bereitstellen
        ↓
Anwendungs-Images deployen
        ↓
Backups wiederherstellen
        ↓
Healthchecks ausführen
        ↓
Produktiven Betrieb freigeben
```

Der Wiederaufbau muss unabhängig davon funktionieren, ob das Zielsystem ein externer VPS, ein dedizierter Server oder intern gehostete Hardware ist.

## Technische Leitprinzipien

### 1. Reproduzierbarkeit

Jeder unterstützte Serverzustand muss aus versionierten Definitionen reproduzierbar sein.

### 2. Automatisierung

Manuelle Einzelschritte werden auf ein notwendiges Minimum reduziert. Wiederkehrende Tätigkeiten werden durch Skripte, Workflows und deklarative Konfigurationen umgesetzt.

### 3. Idempotenz

Installations- und Update-Prozesse müssen mehrfach ausführbar sein, ohne einen bestehenden Serverzustand zu beschädigen.

### 4. Austauschbare Server

Ein Server ist kein unersetzbares Einzelstück. Anwendungen und Infrastruktur sollen auf einem Ersatzsystem erneut bereitgestellt werden können.

### 5. Trennung von Code, Konfiguration und Daten

- Code und Infrastrukturdefinitionen liegen im Repository.
- Nicht sensible Konfigurationen werden versioniert.
- Secrets werden außerhalb des Repositorys verwaltet.
- Produktive Daten werden über definierte Backups gesichert und wiederhergestellt.

### 6. Sicherheit als Standard

Sicherheitsmaßnahmen werden nicht nachträglich ergänzt, sondern sind Bestandteil jeder Serverbereitstellung.

### 7. Nachvollziehbarkeit

Änderungen erfolgen versioniert, überprüfbar und möglichst über Pull Requests.

### 8. Wiederherstellung ist Teil des Betriebs

Backups allein gelten nicht als ausreichende Absicherung. Restore- und Disaster-Recovery-Abläufe müssen dokumentiert, automatisiert und regelmäßig getestet werden.

### 9. Plattformunabhängigkeit

Die Infrastruktur darf nicht ausschließlich auf Odoo zugeschnitten sein. Odoo ist die erste zentrale Anwendung, aber die Plattform soll auch n8n, interne APIs, Importdienste, PDF-Services, Monitoring und weitere Anwendungen tragen können.

### 10. Wiederverwendbarkeit

Der Merchfactory-Standard soll modular genug sein, um später auf weitere Unternehmen und getrennte Zielumgebungen übertragen zu werden.

## Erfolgskriterien

Das Projekt ist erfolgreich, wenn folgende Bedingungen erfüllt sind:

- Ein neuer unterstützter Server kann ohne manuelle Grundinstallation provisioniert werden.
- Ein dokumentierter und getesteter Wiederherstellungsprozess existiert.
- Infrastruktur und Anwendungen können über zentrale Workflows ausgerollt werden.
- Sicherheits- und Betriebsstandards sind auf allen verwalteten Servern einheitlich.
- Der tatsächliche Wiederanlauf wird regelmäßig getestet.
- Die Wiederherstellungszeit wird gemessen und schrittweise reduziert.
- Die Lösung kann später für weitere Standorte, Server und Unternehmen wiederverwendet werden.

## Abgrenzung

Dieses Repository ersetzt keine Datensicherungen und keine fachlichen Notfallpläne.

Es bildet jedoch die technische Grundlage, um Infrastruktur, Anwendungen und gesicherte Daten kontrolliert zu einer neuen produktiven Umgebung zusammenzuführen.

## Langfristige Perspektive

Aus dem Repository soll schrittweise eine interne Infrastrukturplattform entstehen.

Diese Plattform schützt zunächst die Merchfactory vor langen Ausfallzeiten. Langfristig kann daraus ein standardisiertes Angebot für Unternehmen derselben Branche entstehen, das sichere Grundinfrastruktur, automatisierte Deployments, Monitoring, Backups und Disaster Recovery miteinander verbindet.
