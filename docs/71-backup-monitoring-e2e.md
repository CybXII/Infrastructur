# Backup Monitoring E2E (Development)

The manual test and weekly timer are **opt-in**; a matching push to `development` automatically deploys and starts a one-off development test. It writes only `merchfactory-backup-e2e-test.prom` with the fixed labels `service="monitoring-e2e-test"` and `backup="synthetic-fixture"`.

## Prerequisite

Verify that the live Node Exporter has the textfile collector enabled and that `/var/lib/merchfactory/node_exporter/textfile` is the configured directory. A successful monitoring-core deploy alone does **not** verify the host agent was reconfigured. Verify that Prometheus scrapes the `node-exporter` target successfully.

The host role grants the Node Exporter traverse-only ACL on `/var/lib/merchfactory`, while the fixture writer assigns group `merchfactory-backup-metrics` to each atomic replacement file. Verify `node_textfile_scrape_error 0` after publishing; do not loosen directory permissions.

## Manual controlled test

Run on the development host from the checked-out release:

```bash
METRICS=/var/lib/merchfactory/node_exporter/textfile
sudo python3 tests/integration/backup-monitoring-e2e.py success --directory "$METRICS" --environment development
sudo python3 tests/integration/backup-monitoring-e2e.py failure --directory "$METRICS" --environment development
```

Wait at least 5 minutes plus scrape/evaluation and Alertmanager group delay. Verify `BackupJobFailed` is FIRING in Prometheus and Discord receives FIRING. Then publish `success` and verify RESOLVED.

```bash
sudo python3 tests/integration/backup-monitoring-e2e.py success --directory "$METRICS" --environment development
sudo python3 tests/integration/backup-monitoring-e2e.py stale --directory "$METRICS" --environment development
```

Wait at least 15 minutes plus scrape/evaluation and grouping delay; verify `BackupTooOld` FIRING. Restore `success` and verify RESOLVED.

Always clean up:

```bash
sudo python3 tests/integration/backup-monitoring-e2e.py cleanup --directory "$METRICS" --environment development
```

**Important:** Deleting the test series makes the alert disappear but is not a substitute for observing the RESOLVED notification. Do not run this on production. Never edit existing `.prom` files.

## Automated Prometheus-state verification (development only)

The runner sequentially exercises `BackupJobFailed`, `BackupTooOld`,
`RestoreTestFailed`, and `RestoreTestTooOld`. It polls Prometheus for
FIRING and subsequent clearing of each synthetic alert, then deletes its
dedicated fixture in a `finally` block. Allow over one hour for the
`RestoreTestTooOld` rule's `for: 1h` interval, plus evaluation delays.

Run on the development host **only** with the real Node Exporter textfile directory. The runner queries Prometheus through `docker exec` inside the `merchfactory-development-prometheus` container; no public or host-bound Prometheus port is required.

```bash
sudo python3 tests/integration/run-backup-monitoring-e2e.py \
  --environment development \
  --directory /var/lib/merchfactory/node_exporter/textfile \
  --prometheus-url docker-prometheus
```

This command is **not** a production test. The runner verifies Prometheus state, not independent Discord receipt. Do not point the runner at a production metrics directory. The development-only systemd wrapper submits a completion report to Alertmanager.

## Local execution without long GitHub Actions jobs

The repository includes `scripts/install-backup-monitoring-e2e-dev.sh`
and systemd service/timer units under `templates/systemd/`.
The workflow `.github/workflows/deploy-development-backup-e2e.yml` runs on matching pushes to `development` (and on explicit dispatch). It installs the scripts and units, verifies installed files and deployed commit, then starts the systemd service asynchronously using `systemctl start --no-block`. A green GitHub job confirms installation/start, **not** test completion. The optional weekly timer is installed but **not enabled** automatically.
Installation requires an explicit development environment argument:

```bash
sudo bash scripts/install-backup-monitoring-e2e-dev.sh --environment=development
sudo systemctl start merchfactory-backup-monitoring-e2e.service
sudo journalctl -u merchfactory-backup-monitoring-e2e.service -f
```

The service uses `flock` to avoid overlapping systemd runs. The Python runner refuses to overwrite an existing synthetic fixture. The complete suite takes roughly 95 minutes plus alert evaluation delays; systemd allows 120 minutes. No containers are stopped or restarted. The wrapper publishes a final `BackupMonitoringE2EReport` via the internal Alertmanager API; Alertmanager routes the report to Discord. The `SUCCESS` report means all four Prometheus FIRING/clearing transitions passed; receipt of each individual Discord notification remains a separate observation.

**Preflight:** verify the internal Prometheus container is running and the Node Exporter textfile directory exists. No host-bound Prometheus port is required. The fixture must not exist at the start of the run.

After the first successful supervised run, optionally enable a **weekly**
timer:

```bash
sudo systemctl enable --now merchfactory-backup-monitoring-e2e.timer
systemctl list-timers merchfactory-backup-monitoring-e2e.timer
```

Stop future runs with `sudo systemctl disable --now
merchfactory-backup-monitoring-e2e.timer`.

The timer is opt-in, not a deployment side effect. Do not install on production. The runner verifies Prometheus state; the notifier submits its completion alert to Alertmanager but does not independently verify Discord receipt.

## Verified development evidence (2026-10-14)

- PR #319 was merged to `development` (merge commit `24b04b7e54a98d27010afce4325feee682f705c5`).
- A supervised pre-merge run and the automatically started post-merge deployment run each completed with a Discord `Backup Monitoring E2E (Development) – SUCCESS` report.
- The post-merge report was observed at 11:54 CEST; it confirmed all four synthetic Prometheus alert transitions.
- This validates **synthetic monitoring and reporting**, not execution or restoration of a real backup. The backup engine and isolated restore validation remain separate work under ADR-0007 and the backup/restore roadmap.

## Issue #94 acceptance scope

The versioned `monitoring/grafana/dashboards/backup-overview.json` includes panels for backup status, restore-test status, backup duration (`merchfactory_backup_duration_seconds`), backup size (`merchfactory_backup_size_bytes`) and age of last successful backup. Dashboard configuration is verified in the repository; rendering with real job metrics and live operational completeness require a separate runtime check. The synthetic fixture must not be interpreted as a real backup or restore.
