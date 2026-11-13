# ADR-0007: Backup Strategy

- Status: proposed
- Datum: 2026-07-23
- Entscheider: Merchfactory Infrastructure Team

## Kontext

Die Plattform muss Datenverlust, Fehlkonfigurationen und vollständigen Serverausfall beherrschen. Backups ohne getesteten Restore erfüllen dieses Ziel nicht.

## Entscheidung

Wir verfolgen eine mehrstufige Backup-Strategie mit lokaler, verschlüsselter und offsite gespeicherter Sicherung für kritische Daten.

Datenbanken, persistente Volumes, nicht aus Git reproduzierbare Konfigurationen und geschäftskritische Secrets werden nach einer dokumentierten Backup-Matrix gesichert. Aufbewahrung, Verschlüsselung, Integritätsprüfung, Monitoring und Restore-Verfahren sind verpflichtende Bestandteile.

Ein Backup gilt erst als belastbar, wenn eine Wiederherstellung auf einem isolierten Ziel erfolgreich getestet wurde.

## Konsequenzen

### Positiv

- Schutz gegen logische Fehler, Hostverlust und lokale Speicherschäden.
- Wiederherstellbarkeit wird messbar und regelmäßig geprüft.
- RPO und RTO können technisch validiert werden.

### Negativ

- Zusätzlicher Speicher-, Betriebs- und Testaufwand.
- Schlüsselverwaltung und Offsite-Zugriff müssen besonders geschützt werden.

## Betrachtete Alternativen

### Ausschließlich Provider-Snapshots

- Vorteil: einfache und schnelle Gesamtsicherung.
- Nachteil: Providerabhängigkeit, begrenzte Granularität und unzureichende Trennung.
- Grund der Ablehnung: kein vollständiger Schutz gegen Provider- oder Credential-Ausfälle.

### Backups ohne regelmäßige Restore-Tests

- Vorteil: geringerer laufender Aufwand.
- Nachteil: unklare tatsächliche Wiederherstellbarkeit.
- Grund der Ablehnung: ein nicht getestetes Backup ist kein verlässlicher Recovery-Nachweis.

## Referenzen

- Issue #4
- Epic #2
- `docs/01-architecture.md`
