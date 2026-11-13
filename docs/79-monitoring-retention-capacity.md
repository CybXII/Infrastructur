# #96 – Retention, Speicherkapazität und Datenschutz

## Scope

Dieses Dokument finalisiert die **bestehende Development-Baseline** für Speicher- und Löschregeln. Es richtet **keine neue Plattform, keine Kundenzentralisierung und keinen neuen Storage-Dienst** ein. Der VPS bleibt Development. Für Staging/Production gelten zunächst nur Zielklassen, noch **keine technisch durchgesetzten Retention-Zusagen**.

Maschinenlesbare Quellen: `configuration/monitoring-stack.json`, `configuration/logging-policy.json`. Die tatsächlichen Laufzeitflags stehen in Prometheus-Compose und `monitoring/loki/loki.yaml`.

## Was derzeit wirklich erzwungen wird

| Datenklasse / Speicher | Aktueller Development-Vertrag | Was tatsächlich begrenzt? |
|---|---|---|
| Prometheus Rohmetriken | 30 Tage **und** 8 GiB | Prometheus löscht anhand der zuerst greifenden Zeit-/Größen-Retention; WAL/Head und Dateisystem-Overhead können über den Zielwert hinausgehen |
| Loki Container-/Hostlogs | 168h = 7 Tage | Loki Compactor, mit 2h verzögerter Dateilöschung; **4 GiB ist nur ein Kapazitätsziel, kein hartes Quota** |
| Docker lokale Logbuffer | `local`, 20 MiB × 5 pro Container | Docker-Logrotation; ungefähr 100 MiB unkomprimierte Obergrenze je Container |
| journald | 30 Tage, 512 MiB SystemMaxUse, 1 GiB SystemKeepFree | systemd-journald, die jeweils zuerst wirksame Grenze |
| Alloy State/Positionsdaten | kleiner persistenter Betriebszustand | keine eigene Langzeitarchivierung; Laufzeit-/Plattenverbrauch prüfen |

**Wichtige Unterscheidung:** Eine Zeit-Retention garantiert keine Löschung exakt zum Ablaufzeitpunkt. Compaction, Löschverzögerungen und offene Datenblöcke sind zu berücksichtigen. Kein `rm -rf` an laufenden Datenbanken oder Monitoring-Volumes als automatischer Platzgewinn.

## Klassifizierungsrichtlinien (Zielwerte, nicht pauschal durch Loki durchgesetzt)

Bereits in `configuration/logging-policy.json` festgelegt:

| Klasse | Zielwert |
|---|---:|
| DEBUG | 7 Tage |
| INFO / regulärer Betrieb | 30 Tage |
| ERROR / Diagnose | 90 Tage |
| Security und Audit | 365 Tage |
| Deployment- und Backup-Nachweise | 365 Tage |

**Laufzeitrealität:** Die aktuelle einzelne Development-Loki-Instanz löscht **alle** darin gespeicherten Logs nach 7 Tagen – unabhängig von Severity. Es existiert **keine** automatische separate 30-/90-/365-Tage-Archivierung. Für Production müssen die rechtlich begründeten Aufbewahrungsfälle, Zugriff, die technische Trennung und ein geschützter Ablageort vorab gesondert beschlossen und implementiert werden. Monitoring-Metriken sind kein Ersatz für revisionssichere Audits. Die in `docs/08-monitoring.md` erwünschten 12 Monate verdichtete Metriken werden aktuell nicht erzeugt; hierfür ist noch keine zusätzliche Plattform freigegeben.

Datensparsamkeit: keine Secrets, Kundendaten, Bestell-/Tracking-IDs, Auth-Header oder Druck-/Produktionsdaten in Labels oder Lognachrichten ohne ausdrücklichen Bedarf. Löschung bei Zweckwegfall und Löschfristen gehören in das konkrete Kunden-/Datenschutzkonzept; pauschale 365 Tage sind **keine** allgemeine DSGVO-Freigabe. Rechtsgrundlage und Löschpflicht sind kundenspezifisch zu prüfen.

## Kapazitätsmodell – nur Beispiele, keine Messung

**Prometheus:** Näherung für den reinen Sample-Payload:

`GiB = aktive Zeitreihen × (86400 / Scrape-Sekunden) × 30 Tage × Byte je Sample / 1024³`

Beispiel 5.000 aktive Reihen, alle 30s, 2 Byte/Sample → **0,80 GiB Sampledaten in 30 Tagen**. 10.000 Reihen → ca. 1,61 GiB. **Das ist keine vollständige TSDB-Größe:** Head, WAL, Indizes, Label-Kardinalität, Neustarts, Block-Overhead und Recording Rules erhöhen die tatsächliche Speicherung. Die 8-GiB-Retention kann bei hoher Kardinalität deutlich früher als nach 30 Tagen greifen.

**Loki:** Bei hypothetischen 100 MiB täglichem **tatsächlichen** Datenzuwachs ergibt die siebentägige Speicherperiode etwa 700 MiB (0,68 GiB) **vor Index-, Compactor- und Lösch-Overhead**. Bei einem 4-GiB-Ziel entsprechen 4 GiB / 7 Tage ca. **585 MiB pro Tag als theoretisches Maximum ohne Overhead**. Im Betrieb muss erheblich darunter geplant werden. Die Größen sind *Budgetannahmen*, keine Benchmarks.

**Lokale Logs:** 10 Container × 100 MiB lokale Buffer → nominell bis zu 1.000 MiB unkomprimiert, plus journald maximal ca. 512 MiB und zusätzlichen System-/Anwendungsdaten. Diese Puffer gehören zum Hostbudget, **nicht** zum Loki-Quotaversprechen.

## Abfrage der echten Werte (read-only, Development)

Auf dem Development-VPS ausschließlich lesend und vor einer Produktionsentscheidung erfassen:

```bash
sudo du -sh /srv/merchfactory/persistent/monitoring/{prometheus,loki}
df -h /srv/merchfactory/persistent/monitoring
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
sudo journalctl --disk-usage
sudo docker info --format '{{.LoggingDriver}}'
```

Prometheus zusätzlich intern abfragen: `prometheus_tsdb_head_series`, `prometheus_tsdb_head_chunks`, `prometheus_tsdb_storage_blocks_bytes`, `prometheus_tsdb_wal_storage_size_bytes` (nur soweit die eingesetzte Version diese Metriken tatsächlich anbietet). Keine öffentlichen Admin-Endpunkte dafür öffnen. Loki: Ingestionsrate, realen belegten Speicher, Compactor-Zustand und Löschverzögerung getrennt erfassen. Unbekannte Metriknamen nicht als bestätigte Nachweise verbuchen.

**Messprotokoll für #96:** Zeitpunkt, freier Host-Speicher, Prometheus-/Loki-`du`, Datenalter, Serienanzahl, tägliches Wachstum über mindestens 24 Stunden, Peak-Wachstum, Aufbewahrungs-/Lösch-Nachweis und Berechnung des prognostizierten freien Speicherfensters. Bis diese Werte vorliegen, sind die obigen Zahlen **Modellannahmen**.

## Reproduzierbare Live-Messungen (Development, #96)

Die CI kann die Retention-Konfiguration prüfen, aber **keine** tatsächliche
Speicherentwicklung auf dem VPS belegen. Für die Abnahme verwenden wir
`scripts/audit-monitoring-capacity-dev.py`. Das Werkzeug:

- liest nur die zwei bereits konfigurierten Persistenzordner
  `/srv/merchfactory/persistent/monitoring/prometheus` und `loki`;
- misst belegte Dateisystemblöcke (analog `du`, mit Hardlink-Deduplikation)
  und das Dateisystembudget via `statvfs`;
- schreibt JSON-Messpunkte mit Zeitpunkt, Speicherwerten, Gerätezuordnung
  und den aktuell im Repository definierten Retention-Zielen;
- vergleicht nur zwei kompatible Messpunkte im Abstand von **mindestens
  24 Stunden**; Änderungen des Datenträgers oder Budgets stoppen den Vergleich;
- berechnet beobachtete **Nettoänderungen** und bedingte lineare
  Restlaufzeiten bis zu den 75-/85-%-Host-Schwellen.

Das Skript löscht **nichts**, führt keine Docker-Änderungen aus,
benötigt keine zusätzlichen Python-Pakete und überschreibt bestehende
Snapshots nicht. Die JSON-Dateien werden mit Dateimodus 0600 angelegt.
Sie enthalten Kapazitäts-/Pfadmetadaten; deshalb nicht in Git committen
oder ohne Review veröffentlichen.

Aus einem Checkout des Infrastructure-Repositories auf dem Development-VPS
zwei Messpunkte erfassen, beispielhaft (Dateinamen eindeutig wählen):

```bash
cd /pfad/zum/Infrastructure-Checkout

# T0: sofort
sudo python3 scripts/audit-monitoring-capacity-dev.py capture \
  --output /tmp/mf-monitoring-capacity-t0.json

# T1: mindestens 24 Stunden später
sudo python3 scripts/audit-monitoring-capacity-dev.py capture \
  --output /tmp/mf-monitoring-capacity-t1.json

# Rein lesender Vergleich, auf demselben Host oder offline möglich
python3 scripts/audit-monitoring-capacity-dev.py compare \
  --before /tmp/mf-monitoring-capacity-t0.json \
  --after /tmp/mf-monitoring-capacity-t1.json
```

**Interpretation:** Die Größe von Dateien zeigt weder das tatsächliche
Log-Ingestionsvolumen noch die Prometheus-Serienanzahl. Vor allem können
Compaction, Retention und Bereinigungen einen realen Ingestionspeak trotz
geringer Nettozunahme maskieren. Der Vergleich zeigt nur eine
lineare Wenn-dann-Extrapolation der beobachteten Nettoänderung.
`days_to_budget_if_net_growth_persists` ist ausdrücklich **kein**
Retention-Ablauf und **keine** garantierte Speicher-/Kostenprognose.
Die 4 GiB von Loki sind weiterhin ein weiches Ziel.

Für #96 **zusätzlich** separat nachweisen: tatsächliche
`prometheus_tsdb_head_series` (falls verfügbar), Loki-Ingestion/Peaks,
ältesten und jüngsten nachweislich abfragbaren Datenzeitpunkt sowie
die zeitverzögerte Löschung in Loki/TSDB. Dateizeitstempel oder die
`du`-Differenz reichen als Löschbeleg **nicht** aus. Laufende
Retention-Konfiguration/Containerflags lesen und mit dem Repository
abgleichen. Für eine belastbare Wachstumsaussage mehrere Tagesintervalle
erfassen, nicht nur einen einzelnen Tag.

### Grafana-Sichtprüfung nach PR #335

Grafana ausschließlich per bestehendem privaten SSH-Tunnel öffnen
(`localhost:3000`, sofern lokal frei). Im provisionierten
**Server Overview** die Panels `Container CPU`, `Container RAM`
und `Container-Neustarts (15m)` für 24 Stunden und 7 Tage prüfen.
Seit PR #335 gruppieren deren PromQL-Abfragen nach **Host +
Compose-Projekt + Dienst**. Ehemalige ephemere Job-Container dürfen
nicht mehr für jeden kurzlebigen Containernamen eigene gleich
beschriftete Legendenzeilen erzeugen. Die Aggregation ersetzt
keinen Docker-Bestandscheck und belegt keine Log-Retention.

## Warn-/Eingriffsregeln

`configuration/logging-policy.json` legt **75 % Warnung / 85 % kritisch** als Ziel fest. Die Node-Exporter-Regeln wurden im #96-PR zweistufig modelliert: **75 % Belegung (25 % frei)**: `HostFilesystemSpaceLow` mit Severity `warning` (15 Minuten); **85 % Belegung (15 % frei)**: `HostFilesystemSpaceCritical` mit Severity `high` (5 Minuten). Synthetische Promtool-Regeltests sind ergänzt. Echte Discord-Zustellung und Eskalation bleiben Teil von #98.

Bei 75 % Belegung: Wachstum und Top-Verbraucher prüfen, Kardinalität und Logspitzen reduzieren, Kapazität/Retention auf Basis genehmigter Datenklassen anpassen. Bei 85 %: hoher Handlungsbedarf; keine automatischen manuellen Datenlöschungen und keine Änderungen von Kundenretention ohne Freigabe. Inode-Sättigung, Collector-Fehler und verschwundene Metriken sind zusätzlich zu prüfen.

## Kosten / Kundenbetrieb

Monitoring-Storage, Offsite-Audit-Archivierung und Retention sind je Kundenumgebung zu dimensionieren. Die Baseline beansprucht als **Planungspuffer** Prometheus 8 GiB + Loki 4 GiB + Docker/journald mindestens ca. 1,5 GiB im 10-Container-Beispiel = **mindestens rund 13,5 GiB**, plus separate Reserve für OS, Images, Datenbanken, temporäre Dateien, WAL/Indizes, Deployments und Backups. **Keine Festplattenfreigabe** allein aufgrund dieser Summe.

Vor produktiver Nutzung: Kosten je GiB-Monat und Offsite, Verschlüsselung, Rollen/ACL, Löschpfade, Auftragsverarbeitung und Restore-Verhalten klären. Keine Kundendaten in zentrale Betreiberlösungen aggregieren; eine spätere Übersicht ist nur als [#325](https://github.com/Merchfactory/Infrastructure/issues/325) geparkt.

## Prüfung und Definition of Done

Statischer Vertragsabgleich und modellbasierte Budget-Szenarien:

```bash
python3 scripts/validate-monitoring-retention.py
python3 -m unittest discover -s tests/unit -p 'test_monitoring_retention_capacity.py'
```

- [x] Aufbewahrungsziele und **tatsächlich durchgesetzte** Development-Retention getrennt dokumentiert.
- [x] Reproduzierbares Wachstums-/Kapazitätsmodell und Unsicherheiten dokumentiert.
- [x] Datenschutz-/Kosten- und Kundenabgrenzung dokumentiert.
- [x] Read-only Live-Messskript und reproduzierbarer 24h-Vergleich im Repository.
- [ ] Development-VPS: zwei reale Messpunkte (≥24h), Wachstumsbewertung und Retention-/Lösch-Nachweis.
- [x] 75-/85-%-Kapazitätsalarme konfiguriert und Promtool-Szenarien definiert (CI-Nachweis noch ausstehend).
- [ ] Reale Alertmanager-/Discord-Zustellung für beide Schwellen im Development-Kontext nachweisen (#98).
- [ ] Staging-/Production-Retention nur nach eigenem Design-/Datenschutzreview festlegen.

**#96 wird erst nach den für seinen Entwicklungsstand erforderlichen Live-Nachweisen geschlossen.** Parallel laufende #95-Deployments werden von diesem reinen Draft nicht verändert.
