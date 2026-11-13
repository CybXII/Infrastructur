# Examples

## Zweck

Dieses Verzeichnis enthält sichere, vereinfachte Referenzbeispiele für die Nutzung der Repository-Struktur.

## Struktur

```text
examples/
  services/
    example-service/
    reference-http-service/
```

`services/example-service/` bildet eine abstrakte vollständige Referenz für einen Infrastruktur-Service ab.

`services/reference-http-service/` ist dagegen eine **tatsächlich ausführbare** Referenzbereitstellung mit gepinntem, real verfügbarem Image. Sie wird in CI gemeinsam mit Traefik gestartet und auf TLS, Routing, Health, Logging und Persistenz geprüft.

## Nutzung

`examples/services/example-service/` bleibt eine lesbare Referenz dafür, wie einzelne Plattformregeln zusammenspielen. Für die tatsächliche Anlage neuer containerisierter Dienste wird jedoch das renderbare Standard-Service-Template unter `templates/services/container-service/` verwendet.

Einstieg:

```bash
python3 scripts/render-service-template.py --output <ziel> --set ...
```

Details und alle erforderlichen Platzhalter stehen in `docs/53-standard-service-template.md`.

Für neue eigene Services bleibt das renderbare Standard-Service-Template der Ausgangspunkt. Der ausführbare Reference HTTP Service dient zusätzlich als nachweisbare Plattformreferenz und Integrationsbeispiel.

Beide Beispiele verwenden ausschließlich nicht produktive Domains/Werte und dürfen nicht ungeprüft als Produktionskonfiguration übernommen werden.

## Abgrenzung

Beispiele dürfen keine produktiven Domains, IP-Adressen, Schlüssel, Zugangsdaten oder Kundendaten enthalten. Verbindliche produktive Konfiguration gehört in die jeweiligen Fachverzeichnisse.

## Referenzen

- `docs/09-repository-structure.md`
- `docs/10-development-guidelines.md`
- `templates/README.md`
- `tests/README.md`
