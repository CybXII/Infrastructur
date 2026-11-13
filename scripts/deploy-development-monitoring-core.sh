#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "Verwendung: $0 <release-root> <source-revision>" >&2
  exit 2
fi

release_root="$(readlink -m -- "$1")"
source_revision="$2"

if [[ "$release_root" != /srv/merchfactory/releases/development-monitoring/* ]]; then
  echo "Unerwarteter Monitoring-Release-Pfad: $release_root" >&2
  exit 2
fi

cd "$release_root"

monitoring_network="merchfactory-monitoring"
alerting_egress_network="merchfactory-alerting-egress"
release_base="/srv/merchfactory/releases/development-monitoring"
current_link="$release_base/current"
prometheus_state="/srv/merchfactory/deployments/development-prometheus"
loki_state="/srv/merchfactory/deployments/development-loki"
grafana_state="/srv/merchfactory/deployments/development-grafana"
alertmanager_state="/srv/merchfactory/deployments/development-alertmanager"
blackbox_state="/srv/merchfactory/deployments/development-blackbox"
grafana_secret="/srv/merchfactory/secrets/development/grafana-admin-password"
alertmanager_discord_webhook="/srv/merchfactory/secrets/alertmanager/discord-webhook-url"

prometheus_compose="$release_root/deployment/monitoring/prometheus/compose.yaml"
loki_compose="$release_root/deployment/monitoring/loki/compose.yaml"
grafana_compose="$release_root/deployment/monitoring/grafana/compose.yaml"
alertmanager_compose="$release_root/deployment/monitoring/alertmanager/compose.yaml"
blackbox_compose="$release_root/deployment/monitoring/blackbox/compose.staging.yaml"
controller="$release_root/deployment/service-release.py"
verifier="$release_root/scripts/verify-monitoring-service.py"

for required in   "$prometheus_compose"   "$loki_compose"   "$grafana_compose"   "$alertmanager_compose"   "$blackbox_compose"   "$controller"   "$verifier"   "$release_root/configuration/container-image-policy.json"   "$release_root/configuration/deployment-policy.json"
do
  test -f "$required"
done

bash platform/network/scripts/prepare-monitoring-network.sh "$monitoring_network" >/dev/null
bash platform/network/scripts/prepare-alerting-egress-network.sh "$alerting_egress_network" >/dev/null
bash platform/storage/scripts/prepare-persistent-directory.sh   /srv/merchfactory/persistent/monitoring/prometheus 65534 65534 0750 >/dev/null
bash platform/storage/scripts/prepare-persistent-directory.sh   /srv/merchfactory/persistent/monitoring/loki 10001 10001 0750 >/dev/null
bash platform/storage/scripts/prepare-persistent-directory.sh   /srv/merchfactory/persistent/monitoring/grafana 472 472 0750 >/dev/null
bash platform/storage/scripts/prepare-persistent-directory.sh   /srv/merchfactory/persistent/monitoring/alertmanager 65534 65534 0750 >/dev/null
install -d -o root -g root -m 0700 "$(dirname "$grafana_secret")"
if [[ ! -s "$grafana_secret" ]]; then umask 077; openssl rand -base64 36 > "$grafana_secret"; fi
chown root:472 "$grafana_secret"; chmod 0640 "$grafana_secret"; export GRAFANA_ADMIN_PASSWORD_FILE="$grafana_secret"

test -s "$alertmanager_discord_webhook"
test "$(stat -c '%u:%g' "$alertmanager_discord_webhook")" = "65534:65534"
test "$(stat -c '%a' "$alertmanager_discord_webhook")" = "400"
export ALERTMANAGER_DISCORD_WEBHOOK_FILE="$alertmanager_discord_webhook"
export MERCHFACTORY_ALERTING_EGRESS_NETWORK="$alerting_egress_network"

# App targets have a platform-owned persistent location, separate from immutable
# infrastructure releases. App deploy credentials must not write here.
service_targets="/srv/merchfactory/monitoring/targets"
install -d -o root -g root -m 0755 "${service_targets}" "${service_targets}/http" "${service_targets}/tls"
# No application-controlled probes until end-to-end authorization and egress acceptance.
if find "${service_targets}/http" "${service_targets}/tls" -maxdepth 1 -type f -name "*.json" | grep -q .; then
  echo "Blackbox staging blocks any active service probe targets" >&2
  exit 1
fi
# Refuse to reuse the Compose project while an earlier manual egress smoke is active.
for container_id in $(docker ps -q --filter "label=com.docker.compose.project=merchfactory-development-blackbox"); do
  if docker inspect "$container_id" --format '{{json .NetworkSettings.Networks}}' | grep -q '"merchfactory-probe-egress"'; then
    echo "Stop egress-enabled Blackbox smoke container before staged deployment" >&2
    exit 1
  fi
done
export PROMETHEUS_SERVICE_TARGETS_DIR="${service_targets}"
install -d -o root -g root -m 0750 "$prometheus_state" "$loki_state" "$grafana_state" "$alertmanager_state" "$blackbox_state" "$release_base"

target_image() {
  local compose_file="$1"
  local service="$2"
  docker compose -f "$compose_file" config --format json     | python3 -c "import json,sys; print(json.load(sys.stdin)['services']['$service']['image'])"
}

prometheus_image="$(target_image "$prometheus_compose" prometheus)"
loki_image="$(target_image "$loki_compose" loki)"
grafana_image="$(target_image "$grafana_compose" grafana)"
alertmanager_image="$(target_image "$alertmanager_compose" alertmanager)"
blackbox_image="$(target_image "$blackbox_compose" blackbox-exporter)"

previous_release=""
if [[ -L "$current_link" ]]; then
  previous_release="$(readlink -f "$current_link" || true)"
fi

state_backup="$(mktemp -d /var/tmp/merchfactory-monitoring-state.XXXXXX)"
cleanup_backup() {
  rm -rf "$state_backup"
}
trap cleanup_backup EXIT

for service in alertmanager prometheus loki grafana blackbox; do
  state_var="${service}_state"
  state_dir="${!state_var}"
  if [[ -d "$state_dir" ]]; then
    cp -a "$state_dir" "$state_backup/$service"
  fi
done

restore_previous_release() {
  local exit_code="$?"
  trap - ERR

  echo "MONITORING-ROLLBACK: Monitoring-Core-Deployment fehlgeschlagen." >&2

  for service in alertmanager prometheus loki grafana blackbox; do
    state_var="${service}_state"
    state_dir="${!state_var}"
    rm -rf "$state_dir"
    if [[ -d "$state_backup/$service" ]]; then
      cp -a "$state_backup/$service" "$state_dir"
    else
      install -d -o root -g root -m 0750 "$state_dir"
    fi
  done

  if [[ -n "$previous_release" && -d "$previous_release" ]]; then
    echo "MONITORING-ROLLBACK: stelle vorherigen Release $previous_release wieder her." >&2
    if [[ -f "$previous_release/deployment/monitoring/blackbox/compose.staging.yaml" && -f "$blackbox_state/release.env" ]]; then
      docker compose --env-file "$blackbox_state/release.env" -p merchfactory-development-blackbox -f "$previous_release/deployment/monitoring/blackbox/compose.staging.yaml" up -d --no-build --pull never blackbox-exporter
    else
      docker compose -p merchfactory-development-blackbox -f "$blackbox_compose" down --remove-orphans >/dev/null 2>&1 || true
    fi

    if [[ -f "$alertmanager_state/release.env" ]]; then
      docker compose --env-file "$alertmanager_state/release.env" -p merchfactory-development-alertmanager -f "$previous_release/deployment/monitoring/alertmanager/compose.yaml" up -d --no-build --pull never alertmanager
    fi

    if [[ -f "$prometheus_state/release.env" ]]; then
      docker compose         --env-file "$prometheus_state/release.env"         -p merchfactory-development-prometheus         -f "$previous_release/deployment/monitoring/prometheus/compose.yaml"         up -d --no-build --pull never prometheus
    fi

    if [[ -f "$loki_state/release.env" ]]; then
      docker compose         --env-file "$loki_state/release.env"         -p merchfactory-development-loki         -f "$previous_release/deployment/monitoring/loki/compose.yaml"         up -d --no-build --pull never loki
    fi
    if [[ -f "$grafana_state/release.env" ]]; then
      docker compose --env-file "$grafana_state/release.env" -p merchfactory-development-grafana -f "$previous_release/deployment/monitoring/grafana/compose.yaml" up -d --no-build --pull never grafana
    fi
  else
    docker compose -p merchfactory-development-blackbox -f "$blackbox_compose" down --remove-orphans >/dev/null 2>&1 || true
    docker compose -p merchfactory-development-alertmanager -f "$alertmanager_compose" down --remove-orphans >/dev/null 2>&1 || true
    docker compose       -p merchfactory-development-prometheus       -f "$prometheus_compose"       down --remove-orphans >/dev/null 2>&1 || true
    docker compose       -p merchfactory-development-loki       -f "$loki_compose"       down --remove-orphans >/dev/null 2>&1 || true
    docker compose -p merchfactory-development-grafana -f "$grafana_compose" down --remove-orphans >/dev/null 2>&1 || true
  fi

  exit "$exit_code"
}
trap restore_previous_release ERR

# Staging exporter runs exclusively on the internal monitoring network.
# This release explicitly does not enable external probes or unrestricted egress.
python3 "$controller" deploy   --compose-file "$blackbox_compose"   --project-name merchfactory-development-blackbox   --service blackbox-exporter   --state-file "$blackbox_state/state.json"   --release-env "$blackbox_state/release.env"   --image-env-key BLACKBOX_IMAGE_REFERENCE   --target-image "$blackbox_image"   --environment development   --data-change none   --rollback-mode automatic   --source-revision "$source_revision"   --release-reference "github:$source_revision"   --verify-exec "$verifier"   --verify-arg "$monitoring_network"   --verify-arg "9115"   --verify-arg "/-/healthy"

python3 "$controller" deploy   --compose-file "$alertmanager_compose"   --project-name merchfactory-development-alertmanager   --service alertmanager   --state-file "$alertmanager_state/state.json"   --release-env "$alertmanager_state/release.env"   --image-env-key ALERTMANAGER_IMAGE_REFERENCE   --target-image "$alertmanager_image"   --environment development   --data-change none   --rollback-mode automatic   --source-revision "$source_revision"   --release-reference "github:$source_revision"   --verify-exec "$verifier"   --verify-arg "$monitoring_network"   --verify-arg "9093"   --verify-arg "/-/ready"   --verify-arg "200"   --verify-arg "$alerting_egress_network"

python3 "$controller" deploy   --compose-file "$prometheus_compose"   --project-name merchfactory-development-prometheus   --service prometheus   --state-file "$prometheus_state/state.json"   --release-env "$prometheus_state/release.env"   --image-env-key PROMETHEUS_IMAGE_REFERENCE   --target-image "$prometheus_image"   --environment development   --data-change none   --rollback-mode automatic   --source-revision "$source_revision"   --release-reference "github:$source_revision"   --verify-exec "$verifier"   --verify-arg "$monitoring_network"   --verify-arg "9090"   --verify-arg "/-/ready"

python3 "$controller" deploy   --compose-file "$loki_compose"   --project-name merchfactory-development-loki   --service loki   --state-file "$loki_state/state.json"   --release-env "$loki_state/release.env"   --image-env-key LOKI_IMAGE_REFERENCE   --target-image "$loki_image"   --environment development   --data-change none   --rollback-mode automatic   --source-revision "$source_revision"   --release-reference "github:$source_revision"   --verify-exec "$verifier"   --verify-arg "$monitoring_network"   --verify-arg "3100"   --verify-arg "/ready"

python3 "$controller" deploy   --compose-file "$grafana_compose"   --project-name merchfactory-development-grafana   --service grafana   --state-file "$grafana_state/state.json"   --release-env "$grafana_state/release.env"   --image-env-key GRAFANA_IMAGE_REFERENCE   --target-image "$grafana_image"   --environment development   --data-change none   --rollback-mode automatic   --source-revision "$source_revision"   --release-reference "github:$source_revision"   --verify-exec "$verifier"   --verify-arg "$monitoring_network"   --verify-arg "3000"   --verify-arg "/login"   --verify-arg "200,401"

new_link="${current_link}.new"
rm -f "$new_link"
ln -s "$release_root" "$new_link"
mv -Tf "$new_link" "$current_link"

trap - ERR

python3 "$controller" status --state-file "$blackbox_state/state.json"
python3 "$controller" status --state-file "$alertmanager_state/state.json"
python3 "$controller" status --state-file "$prometheus_state/state.json"
python3 "$controller" status --state-file "$loki_state/state.json"
python3 "$controller" status --state-file "$grafana_state/state.json"
echo "MONITORING-DEPLOYMENT: Blackbox (ohne Egress oder aktive Targets), Alertmanager, Prometheus, Loki und privates Grafana für development ausgerollt."
