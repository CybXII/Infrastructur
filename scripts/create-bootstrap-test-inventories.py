#!/usr/bin/env python3
"""Create ephemeral JSON inventories for the fresh-host bootstrap test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SUPPORTED_PUBLIC_KEY_TYPES = {
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "ssh-ed25519",
    "ssh-rsa",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Temporäre Inventare für einen Fresh-Host-Test erstellen."
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--initial-user", required=True)
    parser.add_argument("--managed-user", required=True)
    parser.add_argument("--public-key-file", required=True, type=Path)
    parser.add_argument("--initial-output", required=True, type=Path)
    parser.add_argument("--managed-output", required=True, type=Path)
    parser.add_argument(
        "--runner-host",
        action="store_true",
        help=(
            "Ordnet bootstrap-test zusätzlich der Gruppe runner_hosts zu. "
            "Damit kann derselbe verwaltete Development-Host die "
            "GitHub-Runner-Plattform betreiben."
        ),
    )
    parser.add_argument(
        "--app-deployment-host",
        action="store_true",
        help=(
            "Ordnet bootstrap-test der Gruppe app_deployment_hosts zu. "
            "Der Host verwaltet dann den Benutzer deploy sowie die "
            "anwendungsspezifischen Deployment- und Backup-Pfade."
        ),
    )
    parser.add_argument(
        "--edge-host",
        action="store_true",
        help=(
            "Ordnet bootstrap-test der Gruppe edge_hosts zu und aktiviert "
            "das Firewall-Profil load_balancer für HTTP/HTTPS."
        ),
    )
    parser.add_argument(
        "--additional-ssh-user",
        action="append",
        default=[],
        help=(
            "Zusätzlicher Benutzer für die SSH-AllowUsers-Liste. "
            "Kann mehrfach angegeben werden."
        ),
    )
    return parser.parse_args()


def read_public_key(path: Path) -> str:
    public_key = path.read_text(encoding="utf-8").strip()
    fields = public_key.split()
    if len(fields) < 2 or fields[0] not in SUPPORTED_PUBLIC_KEY_TYPES:
        raise ValueError("Die abgeleitete SSH-Public-Key-Datei ist ungültig.")
    return public_key


def build_inventory(
    host: str,
    connection_user: str,
    initial_user: str,
    managed_user: str,
    managed_public_key: str,
    runner_host: bool = False,
    app_deployment_host: bool = False,
    edge_host: bool = False,
    additional_ssh_users: list[str] | None = None,
) -> dict:
    allowed_ssh_users = [managed_user]
    if app_deployment_host and "deploy" not in allowed_ssh_users:
        allowed_ssh_users.append("deploy")
    for user in additional_ssh_users or []:
        if user and user not in allowed_ssh_users:
            allowed_ssh_users.append(user)

    firewall_ports = ["22/tcp"]
    firewall_roles = ["base"]
    if edge_host:
        firewall_ports.extend(["80/tcp", "443/tcp"])
        firewall_roles.append("load_balancer")

    host_variables = {
        "ansible_host": host,
        "ansible_user": connection_user,
        "ansible_port": 22,
        "ansible_python_interpreter": "/usr/bin/python3",
        "bootstrap_initial_user": initial_user,
        "bootstrap_managed_user": managed_user,
        "bootstrap_expected_firewall_zone": "public",
        "bootstrap_expected_firewall_ports": firewall_ports,
        "bootstrap_expected_firewall_services": ["dhcpv6-client"],
        "firewall_server_roles": firewall_roles,
        "user_management_groups": [
            {"name": "merchfactory-admins", "system": False},
        ],
        "user_management_users": [
            {
                "name": managed_user,
                "primary_group": "merchfactory-admins",
                "groups": ["wheel"],
                "shell": "/bin/bash",
                "create_home": True,
                "password_lock": True,
                "authorized_keys": [managed_public_key],
                "authorized_keys_exclusive": True,
                "sudo": True,
                "sudo_nopasswd": True,
                "sudo_commands": ["ALL"],
            }
        ],
        "bootstrap_expected_ssh_users": allowed_ssh_users,
        "ssh_hardening_allow_users": allowed_ssh_users,
    }

    if edge_host and app_deployment_host:
        host_variables["traefik_edge_dynamic_config_writers"] = ["deploy"]

    children = {
        "bootstrap_targets": {
            "hosts": {"bootstrap-test": host_variables}
        }
    }

    if app_deployment_host:
        children["app_deployment_hosts"] = {
            "hosts": {"bootstrap-test": {}}
        }

    if edge_host:
        children["edge_hosts"] = {
            "hosts": {"bootstrap-test": {}}
        }

    if runner_host:
        children["runner_hosts"] = {
            "hosts": {"bootstrap-test": {}}
        }

    return {"all": {"children": children}}


def write_inventory(path: Path, inventory: dict) -> None:
    path.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    try:
        managed_public_key = read_public_key(args.public_key_file)

        initial_inventory = build_inventory(
            args.host,
            args.initial_user,
            args.initial_user,
            args.managed_user,
            managed_public_key,
            runner_host=args.runner_host,
            app_deployment_host=args.app_deployment_host,
            edge_host=args.edge_host,
            additional_ssh_users=args.additional_ssh_user,
        )
        managed_inventory = build_inventory(
            args.host,
            args.managed_user,
            args.initial_user,
            args.managed_user,
            managed_public_key,
            runner_host=args.runner_host,
            app_deployment_host=args.app_deployment_host,
            edge_host=args.edge_host,
            additional_ssh_users=args.additional_ssh_user,
        )
    except (OSError, ValueError) as exc:
        print(f"configuration_invalid: {exc}")
        return 2

    write_inventory(args.initial_output, initial_inventory)
    write_inventory(args.managed_output, managed_inventory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
