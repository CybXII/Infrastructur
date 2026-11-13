# Unterstützte Betriebssysteme für den Server-Bootstrap

## Zweck

Dieses Dokument legt fest, auf welchen Betriebssystemen der Server-Bootstrap aus Epic #51 entwickelt, getestet und unterstützt wird. Die Festlegung verhindert unklare Kompatibilitätsversprechen und bildet die Grundlage für Rollen, Paketverwaltung, Hardening, CI-Tests und Betriebsdokumentation.

## Verbindliche Entscheidung

### Primär unterstütztes Zielsystem

- **AlmaLinux OS 9**
- Architektur: **x86_64**
- Installationsprofil: minimale Serverinstallation ohne grafische Oberfläche
- Paketverwaltung: `dnf`
- Firewall: `firewalld`
- Init- und Servicemanagement: `systemd`
- SELinux: aktiviert und im Modus `enforcing`
- Python auf dem Zielsystem: `/usr/bin/python3`

Neue Bootstrap-Funktionen müssen zuerst für AlmaLinux OS 9 implementiert und dort vollständig getestet werden.

### Optional kompatibles Zielsystem

- **Rocky Linux 9**
- Architektur: **x86_64**
- gleicher technischer Baseline-Stack wie beim primären Zielsystem

Rocky Linux 9 gilt als kompatibles Sekundärziel. Änderungen dürfen dort eingesetzt werden, sobald die zugehörigen Bootstrap-Rollen erfolgreich getestet wurden. Ein fehlender Rocky-Test blockiert die Entwicklung nicht, blockiert aber eine ausdrückliche Kompatibilitätsfreigabe für die betroffene Änderung.

## Derzeit nicht unterstützt

Folgende Systeme gehören nicht zum Supportumfang von v0.4:

- AlmaLinux OS 8 oder älter
- Rocky Linux 8 oder älter
- CentOS Stream
- Red Hat Enterprise Linux mit kostenpflichtigen oder kundenspezifischen Repository-Anforderungen
- Ubuntu und Debian
- Fedora
- openSUSE und SUSE Linux Enterprise
- Arch Linux und Derivate
- Container-Images als vollständiger Serverersatz
- nicht-x86_64-basierte Architekturen, insbesondere `aarch64`, `ppc64le` und `s390x`

Nicht unterstützt bedeutet, dass keine vollständige Funktions-, Sicherheits- oder Idempotenzgarantie besteht. Beiträge für weitere Plattformen benötigen eine eigene Architekturentscheidung, Testmatrix und dauerhaft verfügbare Testumgebung.

## Versions- und Supportgrenzen

### Major-Version

Der Bootstrap unterstützt ausschließlich die Major-Version 9 der freigegebenen Enterprise-Linux-Derivate. Eine neue Major-Version wird nicht automatisch unterstützt, selbst wenn einzelne Rollen technisch funktionieren.

Die Freigabe einer neuen Major-Version erfordert mindestens:

1. Prüfung der Paketnamen und Repository-Quellen,
2. Prüfung von Python- und Ansible-Kompatibilität,
3. Prüfung von `firewalld`, SELinux und `systemd`,
4. vollständigen Bootstrap-Test auf einem frischen Server,
5. Idempotenztest mit mindestens zwei aufeinanderfolgenden Läufen,
6. dokumentierte Upgrade- und Rollback-Bewertung.

### Minor-Version

Unterstützt wird jeweils die aktuell vom Hersteller bereitgestellte Minor-Version innerhalb der freigegebenen Major-Version 9. Systeme müssen vor einem Bootstrap-Lauf auf einem aktuellen Sicherheits- und Paketstand sein oder durch den Bootstrap kontrolliert dorthin aktualisiert werden.

Ein festes Pinning auf eine veraltete Minor-Version ist nicht vorgesehen, da Enterprise-Linux-Derivate ihre Minor-Releases innerhalb einer Major-Version fortschreiben.

### Lebenszyklus

AlmaLinux OS 9 ist laut Hersteller bis zum 31. Mai 2027 aktiv unterstützt und erhält Sicherheitsupdates bis zum 31. Mai 2032. Die Supportentscheidung für v0.4 orientiert sich daher an der Major-Version 9 und nicht an einer einzelnen Minor-Version.

Vor Ablauf des aktiven Supports muss entschieden werden, ob:

- die Plattform auf AlmaLinux OS 10 angehoben wird,
- AlmaLinux OS 9 nur noch im Wartungsmodus betrieben wird,
- oder ein anderes primäres Zielsystem festgelegt wird.

## Voraussetzungen für verwaltete Server

Jeder Zielserver muss vor dem eigentlichen Bootstrap mindestens folgende Voraussetzungen erfüllen:

- erreichbare SSH-Verbindung,
- administrativer Benutzer mit kontrolliertem `sudo`-Zugriff,
- interaktive POSIX-Shell,
- funktionsfähiges Python 3 unter `/usr/bin/python3`,
- funktionierende DNS-Auflösung,
- korrekte Systemzeit oder erreichbare NTP-Quelle,
- Zugriff auf die freigegebenen Paket-Repositories,
- keine nicht dokumentierten Drittanbieter-Repositories,
- ausreichend freier Speicher für Pakete, Container-Runtime und temporäre Dateien.

Ansible benötigt auf verwalteten Linux-Systemen kein lokal installiertes Ansible, aber eine SSH-Verbindung, eine POSIX-Shell und Python zur Ausführung der übertragenen Module.

## Erkennungs- und Abbruchlogik

Der Bootstrap muss das Zielsystem zu Beginn über `/etc/os-release` erkennen und mindestens folgende Werte validieren:

```text
ID=almalinux
VERSION_ID=9.x
```

oder für das optionale Zielsystem:

```text
ID=rocky
VERSION_ID=9.x
```

Die Prüfung muss auf der Major-Version basieren. Abweichende oder nicht erkennbare Systeme führen vor schreibenden Änderungen zu einem kontrollierten Abbruch.

Der Fehler muss mindestens enthalten:

- erkannten Wert von `ID`,
- erkannte `VERSION_ID`,
- unterstützte Zielsysteme,
- Hinweis auf dieses Dokument,
- eindeutigen nicht erfolgreichen Exit-Status.

Eine Umgehung der Betriebssystemprüfung darf nur als ausdrücklich dokumentierte Entwicklungsoption existieren und nicht standardmäßig aktiv sein.

## Testmatrix

| Zielsystem | Architektur | Status | Bootstrap-Test | Idempotenztest | Release-blockierend |
|---|---|---|---|---|---|
| AlmaLinux OS 9, aktuelle Minor-Version | x86_64 | primär unterstützt | verpflichtend | verpflichtend | ja |
| Rocky Linux 9, aktuelle Minor-Version | x86_64 | optional kompatibel | empfohlen vor Kompatibilitätsfreigabe | empfohlen | nein für AlmaLinux, ja für Rocky-Freigabe |
| AlmaLinux OS 10 | x86_64 | nicht unterstützt | negativer Erkennungstest | nicht erforderlich | nein |
| Ubuntu 24.04 LTS | x86_64 | nicht unterstützt | negativer Erkennungstest | nicht erforderlich | nein |
| unbekanntes oder manipuliertes `/etc/os-release` | beliebig | nicht unterstützt | verpflichtender Abbruchtest | nicht erforderlich | ja |

## Mindestprüfungen pro Bootstrap-Release

Für das primär unterstützte Zielsystem sind mindestens folgende Prüfungen erforderlich:

1. Installation auf einem frischen Minimal-System,
2. erfolgreicher vollständiger Bootstrap-Lauf,
3. zweiter Lauf ohne fachlich unnötige Änderungen,
4. Prüfung von SSH-Zugang und Sudo-Rechten,
5. Prüfung von Firewall und Fail2ban,
6. Prüfung von SELinux im Modus `enforcing`,
7. Prüfung der Paket- und Updateverwaltung,
8. Prüfung von Zeitzone, Locale und NTP,
9. Prüfung der Verzeichnis- und Storage-Vorbereitung,
10. Prüfung der Docker-Installation,
11. kontrollierter Abbruch auf einem nicht unterstützten System.

## Änderungsprozess

Änderungen an dieser Supportmatrix benötigen:

- ein eigenes Issue oder eine nachvollziehbare Erweiterung eines Bootstrap-Issues,
- eine dokumentierte technische Begründung,
- angepasste Erkennungslogik,
- angepasste CI- und Integrationstests,
- aktualisierte Betriebs- und Bootstrap-Dokumentation,
- bei grundlegenden Änderungen eine ADR.

## Entscheidung für v0.4

Für v0.4 wird bewusst eine enge Plattformbasis gewählt:

- **AlmaLinux OS 9 auf x86_64 ist verbindlich unterstützt.**
- **Rocky Linux 9 auf x86_64 ist optional kompatibel.**
- **Debian-/Ubuntu-basierte Systeme werden erst nach einer separaten Architektur- und Implementierungsentscheidung aufgenommen.**

Diese Begrenzung reduziert unterschiedliche Paket-, Firewall-, SELinux-, Repository- und Servicepfade und ermöglicht einen reproduzierbaren, sicher testbaren und idempotenten Bootstrap.
