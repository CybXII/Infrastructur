#!/usr/bin/env python3
"""Static security and deployment contract for Discord alert delivery."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class AlertmanagerDiscordTests(unittest.TestCase):
    def test_alertmanager_routes_all_severities_to_discord_and_resolves(self) -> None:
        config = (REPO_ROOT / "monitoring/alertmanager/alertmanager.yml").read_text(
            encoding="utf-8"
        )

        for receiver in (
            "discord-default",
            "discord-critical",
            "discord-warning",
            "discord-info",
        ):
            self.assertIn(f"receiver: {receiver}", config)
            self.assertIn(f"name: {receiver}", config)

        self.assertEqual(config.count("send_resolved: true"), 4)
        self.assertEqual(
            config.count("webhook_url_file: /run/secrets/discord-webhook-url"),
            4,
        )
        self.assertNotIn("webhook_url:", config)
        self.assertNotIn("discord.com", config)

        for label in ("environment", "host", "instance", "service", "severity"):
            self.assertIn(label, config)

        self.assertIn("FIRING", config)
        self.assertIn("RESOLVED", config)
        self.assertEqual(config.count("{{ with index .Alerts 0 }}"), 4)
        self.assertEqual(config.count(".Annotations.summary"), 4)
        self.assertEqual(config.count(".Annotations.description"), 4)
        self.assertNotIn(".CommonAnnotations.summary", config)
        self.assertNotIn(".CommonAnnotations.description", config)

    def test_high_routes_to_critical_receiver_and_inhibits_lower_alerts(self) -> None:
        config = (REPO_ROOT / "monitoring/alertmanager/alertmanager.yml").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(config.count('severity=~"critical|high"'), 2)
        self.assertNotIn('severity="critical"', config)
        self.assertIn(
            "| {{ .CommonLabels.severity }} | {{ .CommonLabels.alertname }}",
            config,
        )
        self.assertEqual(config.count("{{ if .Labels.test_run }}"), 4)
        # Each optional label appears once in the condition and once in the value.
        # Instance also appears in the host fallback (three references per receiver).
        for label, expected in (("instance", 12), ("mountpoint", 8), ("device", 8)):
            self.assertEqual(config.count(".Labels." + label), expected)
        integration = (
            REPO_ROOT / "tests/integration/test-alertmanager-deployment.sh"
        ).read_text(encoding="utf-8")
        for severity, receiver in (
            ("high", "discord-critical"),
            ("critical", "discord-critical"),
            ("warning", "discord-warning"),
            ("info", "discord-info"),
            ("unknown", "discord-default"),
        ):
            self.assertIn(f'"{severity} {receiver}"', integration)
        # Integration script passes the receiver and severity as separate,
        # dynamically expanded arguments to the real amtool CLI.
        self.assertIn('--verify.receivers="$receiver"', integration)
        self.assertIn('severity="$severity"', integration)
        self.assertIn('read -r severity receiver <<< "$entry"', integration)

    def test_integration_probe_reads_only_the_monitoring_network_ip(self) -> None:
        test_script = (
            REPO_ROOT / "tests/integration/test-alertmanager-deployment.sh"
        ).read_text(encoding="utf-8")

        self.assertNotIn(
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            test_script,
        )
        self.assertIn("NetworkSettings.Networks", test_script)
        self.assertIn("monitoring_ip", test_script)
        self.assertIn("egress_ip", test_script)
        self.assertIn(
            'network="alertmanager-monitoring-${GITHUB_RUN_ID:-local}-$$"',
            test_script,
        )
        self.assertIn(
            'egress_network="alertmanager-egress-${GITHUB_RUN_ID:-local}-$$"',
            test_script,
        )

    def test_compose_mounts_secret_read_only_and_adds_only_outbound_network(self) -> None:
        compose = (REPO_ROOT / "deployment/monitoring/alertmanager/compose.yaml").read_text(
            encoding="utf-8"
        )

        self.assertIn("ALERTMANAGER_DISCORD_WEBHOOK_FILE", compose)
        self.assertIn("target: /run/secrets/discord-webhook-url", compose)
        self.assertIn("read_only: true", compose)
        self.assertIn("alerting_egress:", compose)
        self.assertIn("merchfactory-alerting-egress", compose)
        self.assertNotIn("ports:", compose)
        self.assertNotIn("DISCORD_WEBHOOK_URL", compose)

    def test_egress_network_is_dedicated_and_not_internal(self) -> None:
        script_path = (
            REPO_ROOT / "platform/network/scripts/prepare-alerting-egress-network.sh"
        )
        self.assertTrue(script_path.is_file())
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("merchfactory-alerting-egress", script)
        self.assertIn("mf-alert-egress", script)
        self.assertIn('expected_class="alerting-egress"', script)
        self.assertNotIn("--internal", script)

    def test_deployment_requires_preinstalled_secret_and_prepares_egress(self) -> None:
        deploy = (REPO_ROOT / "scripts/deploy-development-monitoring-core.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "/srv/merchfactory/secrets/alertmanager/discord-webhook-url", deploy
        )
        self.assertIn("test -s", deploy)
        self.assertIn("prepare-alerting-egress-network.sh", deploy)
        self.assertIn("ALERTMANAGER_DISCORD_WEBHOOK_FILE", deploy)

    def test_development_smoke_script_is_packaged_into_release(self) -> None:
        workflow = (
            REPO_ROOT / ".github/workflows/deploy-development-monitoring.yml"
        ).read_text(encoding="utf-8")
        script = "scripts/test-development-alert-routing.sh"
        self.assertIn("            " + script, workflow)
        self.assertTrue((REPO_ROOT / script).is_file())
        docs = (REPO_ROOT / "docs/81-alerting-e2e-acceptance.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/srv/merchfactory/releases/development-monitoring/", docs)
        self.assertIn('test -f "$SMOKE"', docs)

    def test_workflow_installs_repository_secret_via_stdin(self) -> None:
        workflow = (
            REPO_ROOT / ".github/workflows/deploy-development-monitoring.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("secrets.DISCORD_WEBHOOK_URL", workflow)
        self.assertIn("platform/secrets/scripts/install-secret-file.sh", workflow)
        self.assertIn("printf '%s' \"$DISCORD_WEBHOOK_URL\"", workflow)
        self.assertIn("alertmanager discord-webhook-url 65534 65534 0400", workflow)
        self.assertEqual(workflow.count("prepare-alerting-egress-network"), 2)
        self.assertNotIn("echo \"$DISCORD_WEBHOOK_URL\"", workflow)
        self.assertNotIn("    environment: development", workflow)


class AlertmanagerSmokeCliTests(unittest.TestCase):
    """Run the real Bash CLI with a fake Docker command; never contact Discord."""

    def run_smoke(self, *arguments):
        script = REPO_ROOT / "scripts/test-development-alert-routing.sh"
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            docker = home / "docker"
            event_file = home / "docker-events.jsonl"
            docker.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "args = sys.argv[1:]\n"
                "if args[0] == 'ps':\n"
                "    print('mock-alertmanager')\n"
                "elif args[0] == 'exec':\n"
                "    with open(os.environ['MOCK_DOCKER_EVENTS'], 'a') as out:\n"
                "        out.write(json.dumps(args) + '\\n')\n"
                "else:\n"
                "    sys.exit(71)\n",
                encoding="utf-8",
            )
            docker.chmod(0o755)
            env = dict(os.environ)
            env["PATH"] = str(home) + os.pathsep + env["PATH"]
            env["MOCK_DOCKER_EVENTS"] = str(event_file)
            run = subprocess.run(
                ["bash", str(script), *arguments],
                capture_output=True, text=True, env=env, check=False,
            )
            events = [
                json.loads(line)
                for line in (event_file.read_text().splitlines() if event_file.exists() else [])
            ]
        return run, events

    def test_plan_warning_checks_correct_receiver_without_sending(self):
        run, events = self.run_smoke("--plan", "warning")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Read-only plan OK: warning -> discord-warning", run.stdout)
        self.assertEqual(len(events), 1)
        self.assertIn("--verify.receivers=discord-warning", events[0])
        self.assertIn("severity=warning", events[0])
        self.assertNotIn("alert", events[0])

    def test_apply_requires_explicit_development_confirmation(self):
        for argv in (("--apply", "warning"), ("--apply",), ("--plan", "warning", "extra")):
            with self.subTest(args=argv):
                run, events = self.run_smoke(*argv)
                self.assertEqual(run.returncode, 2)
                self.assertFalse(events)

    def test_apply_quotes_utf8_matchers_annotations_and_preserves_labels(self):
        run, events = self.run_smoke("--apply", "--confirm-development", "warning")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(events), 2)
        self.assertIn("--verify.receivers=discord-warning", events[0])
        self.assertIn("alert", events[1])
        self.assertIn("severity=warning", events[1])
        self.assertIn("service=monitoring-e2e-test", events[1])
        self.assertTrue(any(arg.startswith("test_run=issue98-") for arg in events[1]))
        self.assertIn(
            '--annotation=summary="Manual Development routing smoke (#98)"',
            events[1],
        )
        self.assertIn(
            '--annotation=description="Synthetic test alert; no actual incident."',
            events[1],
        )
        self.assertIn("Alert submitted.", run.stdout)

    def test_plan_info_and_default_are_explicit(self):
        info, events = self.run_smoke("--plan", "info")
        self.assertEqual(info.returncode, 0, info.stderr)
        self.assertIn("--verify.receivers=discord-info", events[0])
        default, events = self.run_smoke("--plan")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("--verify.receivers=discord-critical", events[0])


if __name__ == "__main__":
    unittest.main()
