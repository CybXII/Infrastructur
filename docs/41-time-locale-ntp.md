# Zeitzone, Locale und NTP

## Zweck

Die Rolle `system_time` stellt auf unterstützten AlmaLinux-9- und Rocky-Linux-9-Systemen einen reproduzierbaren Zeit- und Sprachezustand her. Einheitliche Zeitquellen sind für Logs, TLS-Zertifikatsprüfung, geplante Wartungsfenster und die spätere Auswertung verteilter Systeme wichtig.

## Standardwerte

- Zeitzone: `Europe/Berlin`
- Locale: `en_US.UTF-8`
- NTP-Dienst: `chronyd`
- NTP-Quellen: `0.pool.ntp.org` bis `3.pool.ntp.org`
- `makestep`: Abweichungen über 1 Sekunde dürfen während der ersten drei Updates korrigiert werden.
- Hardwareuhr wird über `rtcsync` an die Systemzeit gekoppelt.

Die Zeitzone `Europe/Berlin` sorgt dafür, dass Wartungsfenster und Betriebszeiten in lokaler deutscher Zeit inklusive Sommer-/Winterzeit ausgewertet werden. Die englische UTF-8-Locale hält Kommandoausgaben und Log-Kontext für Automation konsistent.

## NTP-Konfiguration

Die Rolle installiert `chrony`, verwaltet `/etc/chrony.conf` vollständig und aktiviert `chronyd` dauerhaft. Standardmäßig werden vier öffentliche NTP-Pools verwendet:

```yaml
system_ntp_sources:
  - "pool 0.pool.ntp.org iburst"
  - "pool 1.pool.ntp.org iburst"
  - "pool 2.pool.ntp.org iburst"
  - "pool 3.pool.ntp.org iburst"
```

Für interne oder providerseitige NTP-Quellen kann diese Liste im Inventory überschrieben werden.

## Zeitsynchronisation prüfen

Nach einer Konfigurationsänderung wird `chronyd` neu gestartet. Anschließend wartet die Rolle mit `chronyc waitsync` auf einen synchronisierten Zustand und prüft zusätzlich:

```bash
chronyc tracking
timedatectl show --property=Timezone --value
cat /etc/locale.conf
```

Der Bootstrap bricht ab, wenn Chrony weiterhin `Not synchronised` meldet oder Zeitzone bzw. Locale vom Sollzustand abweichen.

## Zusammenhang mit Logging und TLS

Korrekte Systemzeit ist Voraussetzung dafür, dass:

- Logeinträge serverübergreifend zeitlich vergleichbar sind,
- GitHub-/Deployment-Abläufe Zeitstempel konsistent auswerten können,
- TLS-Zertifikate nicht aufgrund einer falschen lokalen Uhr als noch nicht gültig oder bereits abgelaufen bewertet werden,
- `dnf-automatic`-Wartungsfenster zur erwarteten lokalen Zeit laufen.

Die Rolle ersetzt keine zentrale Logplattform und keine PKI-Konfiguration. Sie stellt nur die dafür notwendige konsistente Zeitbasis bereit.

## Variablen

```yaml
system_timezone: Europe/Berlin
system_locale: en_US.UTF-8
system_ntp_sources:
  - "pool 0.pool.ntp.org iburst"
  - "pool 1.pool.ntp.org iburst"
  - "pool 2.pool.ntp.org iburst"
  - "pool 3.pool.ntp.org iburst"
```

Für einen internen NTP-Dienst kann beispielsweise konfiguriert werden:

```yaml
system_ntp_sources:
  - "server 10.20.0.10 iburst"
  - "server 10.20.0.11 iburst"
```

## Idempotenz

Zeitzone und Locale werden nur geändert, wenn der aktuelle Zustand abweicht. Paketinstallation, Template und Dienstzustand werden deklarativ verwaltet. Bei unveränderter Konfiguration darf ein erneuter Bootstrap keine fachlich unnötigen Änderungen erzeugen.

## Fehlerverhalten

Der Lauf bricht kontrolliert ab, wenn:

- die Konfigurationsvariablen ungültig sind,
- Locale- oder Chrony-Pakete nicht installiert werden können,
- `chronyd` nicht startet,
- innerhalb der definierten Wartezeit keine Zeitsynchronisation erreicht wird,
- Zeitzone oder Locale nach Anwendung nicht dem Sollzustand entsprechen.

## Rollback

Ein Rollback erfolgt über den vorherigen Repository-Stand und erneute Ausführung des Bootstrap-Playbooks. Bei einer Änderung der Zeitquelle muss vorher sichergestellt sein, dass die alternative Quelle aus dem Zielnetz erreichbar ist.

## Abgrenzung

Nicht Bestandteil dieses Tasks sind:

- eigener NTP-Server,
- DNS-Konfiguration,
- zentrale Logaggregation,
- Zertifikatsausstellung oder PKI,
- Monitoring/Alarmierung bei später auftretendem Zeitdrift.
