#!/usr/bin/env bash
set -Eeuo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$repo_root/deployment/monitoring/grafana/compose.yaml"
network="merchfactory-monitoring"; project="merchfactory-grafana-integration"; workspace="$(mktemp -d)"
cleanup(){ docker compose -p "$project" -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true; docker network rm "$network" >/dev/null 2>&1 || true; sudo rm -rf "$workspace"; }
trap cleanup EXIT
install -d -m 0777 "$workspace/data"; printf '%s\n' integration-only-password > "$workspace/password"; chmod 0640 "$workspace/password"; sudo chown root:472 "$workspace/password"
docker network create --internal --subnet 172.30.250.0/24 --gateway 172.30.250.1 "$network" >/dev/null
export GRAFANA_DATA_DIR="$workspace/data" GRAFANA_ADMIN_PASSWORD_FILE="$workspace/password"
docker compose -p "$project" -f "$compose_file" up -d --pull always grafana
id="$(docker compose -p "$project" -f "$compose_file" ps -q grafana)"; test -n "$id"
ip="$(docker inspect "$id" --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')"
for _ in {1..60}; do curl --max-time 3 -sS -o /dev/null "http://$ip:3000/login" && break; sleep 1; done
if ! curl --max-time 3 -sS -o /dev/null "http://$ip:3000/login"; then
  docker inspect "$id" --format '{{json .State}}' >&2 || true
  docker compose -p "$project" -f "$compose_file" logs grafana >&2 || true
  exit 1
fi
cookie_jar="$workspace/grafana-cookie"
echo "Grafana: Login-Session prüfen"
curl --max-time 3 -fsS -c "$cookie_jar" -H "Content-Type: application/json" \
  --data '{"user":"admin","password":"integration-only-password"}' "http://$ip:3000/login" \
  | grep -q '"message":"Logged in"'
echo "Grafana: Health-API mit Session prüfen"
curl --max-time 3 -fsS -b "$cookie_jar" "http://$ip:3000/api/health" | grep -q '"database": "ok"'
echo "Grafana: Prometheus-Datasource prüfen"
curl --max-time 3 -fsS -b "$cookie_jar" "http://$ip:3000/api/datasources/uid/prometheus" | grep -q '"uid":"prometheus"'
echo "Grafana: Loki-Datasource prüfen"
curl --max-time 3 -fsS -b "$cookie_jar" "http://$ip:3000/api/datasources/uid/loki" | grep -q '"uid":"loki"'
echo "Grafana: Server-Overview-Dashboard prüfen"
dashboard_json="$(curl --max-time 3 -fsS -b "$cookie_jar" "http://$ip:3000/api/dashboards/uid/merchfactory-server-overview")"
DASHBOARD_JSON="$dashboard_json" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["DASHBOARD_JSON"])
dashboard = payload["dashboard"]
if dashboard["uid"] != "merchfactory-server-overview":
    raise SystemExit("Grafana hat das Server-Overview-Dashboard nicht mit der erwarteten UID provisioniert.")
if dashboard["title"] != "Server Overview":
    raise SystemExit("Grafana hat einen unerwarteten Dashboard-Titel geliefert.")
if len(dashboard.get("panels") or []) != 9:
    raise SystemExit("Das Server-Overview-Dashboard enthält nicht die erwarteten neun Panels.")
PY
echo "Grafana: Server-Overview-Dashboard vorhanden"
port_bindings="$(docker inspect "$id" --format '{{json .HostConfig.PortBindings}}')"
echo "Grafana: PortBindings=$port_bindings"
[[ "$port_bindings" == null || "$port_bindings" == "{}" ]]
container_user="$(docker inspect "$id" --format '{{.Config.User}}')"
echo "Grafana: Container-User=$container_user"
test "$container_user" = 472:472
echo "Grafana: Container-IP=$ip"
test "$ip" = 172.30.250.20
echo "Grafana ist authentifiziert, provisioniert und ausschließlich intern erreichbar."
