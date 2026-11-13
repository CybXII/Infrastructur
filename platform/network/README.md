# Plattform-Netzwerke

Dieser Bereich enthält die hostweiten Docker-Netzwerkbausteine der Merchfactory Container Platform.

## Shared Edge Network

`bash platform/network/scripts/prepare-edge-network.sh` erstellt bzw. validiert das gemeinsame externe Edge-Netz für Traefik und ingress-fähige Dienste.

Standardname:

```text
merchfactory-edge
```

Das Skript ist idempotent. Existiert das Netz bereits, werden Treiber, Internal-Status und die erwarteten Plattform-Labels geprüft. Ein widersprüchlich vorkonfiguriertes Netz führt zu einem kontrollierten Fehler statt zu einer stillen Übernahme.

Details zum Sicherheits- und Kommunikationsmodell stehen in `docs/49-docker-network-model.md`.

## Shared Monitoring Network

`bash platform/network/scripts/prepare-monitoring-network.sh` erstellt bzw. validiert das gemeinsame interne Core-Netz für zentrale Monitoring-Komponenten.

Standardname:

```text
merchfactory-monitoring
```

Eigenschaften:

- Docker bridge,
- `internal=true`,
- Subnetz `172.30.250.0/24`,
- Host-Gateway `172.30.250.1`,
- Linux-Bridge `mf-monitoring0`,
- `com.merchfactory.network.class=monitoring`,
- `com.merchfactory.managed=true`.

Das feste Gateway ist Teil des Host-Agent-Sicherheitsmodells. Node Exporter bindet ausschließlich an `172.30.250.1:9100`; Prometheus erreicht ihn aus dem internen Monitoring-Netz. Port 9100 wird nicht als öffentlicher Hostport bzw. firewalld-Port freigegeben.

Die Werte können für isolierte Testumgebungen über `MERCHFACTORY_MONITORING_SUBNET`, `MERCHFACTORY_MONITORING_GATEWAY` und `MERCHFACTORY_MONITORING_BRIDGE` überschrieben werden. Produktionsabweichungen benötigen einen bewussten Architektur-/Policy-Change.

Prometheus nutzt dieses Netz ab Issue #85. Grafana, Loki, Alertmanager und Blackbox Exporter werden in ihren jeweiligen v0.6-Arbeitspaketen daran angebunden.

Das Netz ist bewusst vom öffentlichen `merchfactory-edge` getrennt.
