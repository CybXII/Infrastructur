#!/usr/bin/env python3
"""Drift tests for exclusive firewall port management."""

from __future__ import annotations

import pathlib
import unittest

try:
    import jinja2
    import yaml
except ImportError:
    jinja2 = None
    yaml = None


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULTS = (
    REPO_ROOT / "ansible" / "roles" / "firewall" / "defaults" / "main.yml"
).read_text(encoding="utf-8")
TASKS = (
    REPO_ROOT / "ansible" / "roles" / "firewall" / "tasks" / "main.yml"
).read_text(encoding="utf-8")
VERIFY = (
    REPO_ROOT / "tests" / "integration" / "test-bootstrap-fresh-host-verify.yaml"
).read_text(encoding="utf-8")


class FirewallPolicyTests(unittest.TestCase):
    def test_services_and_ports_are_exclusive_by_default(self) -> None:
        self.assertIn("firewall_manage_services_exclusively: true", DEFAULTS)
        self.assertIn("firewall_manage_ports_exclusively: true", DEFAULTS)

    def test_stale_direct_ports_are_removed(self) -> None:
        for fragment in (
            "Aktuell permanente Firewall-Ports lesen",
            "firewall_stale_ports",
            "difference(firewall_effective_ports)",
            "Nicht deklarierte Firewall-Ports entfernen",
            'state: disabled',
            'permanent: true',
            'immediate: true',
        ):
            self.assertIn(fragment, TASKS)

    def test_required_ports_are_opened_before_stale_ports_are_removed(self) -> None:
        required = TASKS.index("Erforderliche Ports vor Default-Deny freigeben")
        stale = TASKS.index("Nicht deklarierte Firewall-Ports entfernen")
        self.assertLess(required, stale)

    def test_ssh_is_part_of_effective_port_set(self) -> None:
        self.assertIn(
            "([firewall_ssh_port | string ~ '/tcp'] if firewall_require_ssh_access | bool else [])",
            TASKS,
        )
        self.assertIn(
            "SSH-Port in effektiver Firewall-Konfiguration bestätigen",
            TASKS,
        )

    def test_exclusive_port_management_is_type_checked(self) -> None:
        self.assertIn(
            "firewall_manage_ports_exclusively | type_debug == 'bool'",
            TASKS,
        )

    def test_verification_reports_actual_and_expected_ports(self) -> None:
        self.assertIn("Ist={{ fresh_host_verification_firewall_ports", VERIFY)
        self.assertIn("Soll={{ bootstrap_expected_firewall_ports", VERIFY)


@unittest.skipIf(jinja2 is None or yaml is None, "Synthetic task checks require existing Jinja2/PyYAML environment")
class FirewallTaskRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tasks = yaml.safe_load(TASKS)
        self.context = yaml.safe_load(DEFAULTS)
        self.context["firewall_ssh_port"] = 2222
        self.env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        self.env.filters["bool"] = bool
        self.env.filters["difference"] = lambda current, expected: [
            item for item in current if item not in expected
        ]

    def evaluate(self, value):
        if isinstance(value, str) and value.strip().startswith("{{"):
            return self.env.compile_expression(value.strip()[2:-2].strip())(**self.context)
        return value

    def effective_ports(self, roles):
        self.context["firewall_server_roles"] = roles
        # Execute only the role's pure set_fact calculations, preserving facts
        # across invocations as Ansible does; no host commands/modules execute.
        for task in self.tasks:
            facts = task.get("ansible.builtin.set_fact", {})
            if not set(facts).intersection({"firewall_role_ports", "firewall_effective_ports"}):
                continue
            items = self.evaluate(task["loop"]) if "loop" in task else [None]
            for item in items:
                self.context["item"] = item
                self.context.update({key: self.evaluate(value) for key, value in facts.items()})
        return self.context["firewall_effective_ports"]

    def test_role_change_removes_previous_profile_ports_and_keeps_ssh(self) -> None:
        self.assertEqual(set(self.effective_ports(["load_balancer"])), {"80/tcp", "443/tcp", "2222/tcp"})
        self.assertEqual(set(self.effective_ports(["base"])), {"2222/tcp"})
        # The actual stale-port expression must select the retired profile ports.
        self.context["firewall_current_ports"] = {"stdout": "80/tcp 443/tcp 2222/tcp"}
        stale = next(task["ansible.builtin.set_fact"]["firewall_stale_ports"]
                     for task in self.tasks if "firewall_stale_ports" in task.get("ansible.builtin.set_fact", {}))
        self.assertEqual(set(self.evaluate(stale)), {"80/tcp", "443/tcp"})

    def test_empty_and_repeated_profiles_do_not_retain_old_ports(self) -> None:
        first = self.effective_ports(["load_balancer"])
        self.assertEqual(self.effective_ports(["load_balancer"]), first)
        self.assertEqual(self.effective_ports([]), ["2222/tcp"])
        self.context["firewall_require_ssh_access"] = False
        self.assertEqual(self.effective_ports([]), [])

    def test_required_ports_are_active_before_any_service_or_port_removal(self) -> None:
        openings = []
        removals = []
        for index, task in enumerate(self.tasks):
            module = task.get("ansible.posix.firewalld", {})
            if module.get("port") and module.get("state") == "enabled":
                openings.append(index)
                self.assertEqual(task["loop"], "{{ firewall_effective_ports }}")
                self.assertIs(module["permanent"], True)
                self.assertIs(module["immediate"], True)
            if module.get("state") == "disabled" and ("port" in module or "service" in module):
                removals.append(index)
        self.assertTrue(openings)
        self.assertTrue(removals)
        self.assertLess(max(openings), min(removals))


if __name__ == "__main__":
    unittest.main()
