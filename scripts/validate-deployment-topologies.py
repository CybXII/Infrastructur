#!/usr/bin/env python3
"""Validate the supported deployment topology profiles."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_POLICY = REPO_ROOT / "configuration" / "deployment-topologies.json"

ENVIRONMENTS = {"development", "staging", "production"}
HOST_ROLES = {
    "host_baseline",
    "edge",
    "application",
    "database",
    "monitoring_server",
    "monitoring_agent",
    "backup_agent",
}
REQUIRED_PROFILES = {
    "development-only": 1,
    "compact": 1,
    "standard": 2,
    "split-production": 3,
}
REQUIRED_ENVIRONMENT_ROLES = {"edge", "application", "database"}
REQUIRED_ISOLATION_DIMENSIONS = {
    "compose_project",
    "network",
    "persistent_storage",
    "runtime_secrets",
    "database_credentials",
}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Deployment-Topologie kann nicht gelesen werden: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Deployment-Topologie muss ein JSON-Objekt sein.")
    return document


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if document.get("version") != 1:
        errors.append("version muss 1 sein.")

    if set(document.get("environments") or []) != ENVIRONMENTS:
        errors.append("environments muss development, staging und production enthalten.")

    if set(document.get("host_roles") or []) != HOST_ROLES:
        errors.append("host_roles entspricht nicht dem verbindlichen Rollenmodell.")

    rules = document.get("rules")
    if not isinstance(rules, dict):
        errors.append("rules fehlt oder ist ungültig.")
        rules = {}

    for key in (
        "environment_and_host_topology_are_independent",
        "environment_isolation_required_on_shared_hosts",
        "application_database_endpoint_indirection_required",
        "monitoring_agent_required_on_every_managed_host",
        "monitoring_server_singleton_per_topology",
        "production_database_split_is_optional",
    ):
        if rules.get(key) is not True:
            errors.append(f"rules.{key} muss true sein.")

    if rules.get("public_database_exposure_allowed") is not False:
        errors.append("rules.public_database_exposure_allowed muss false sein.")

    isolation = set(rules.get("isolation_dimensions") or [])
    if not REQUIRED_ISOLATION_DIMENSIONS.issubset(isolation):
        errors.append("Pflicht-Isolationsdimensionen fehlen.")

    profiles = document.get("profiles")
    if not isinstance(profiles, dict):
        errors.append("profiles fehlt oder ist ungültig.")
        profiles = {}

    for profile_name, expected_hosts in REQUIRED_PROFILES.items():
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            errors.append(f"Pflichtprofil {profile_name} fehlt.")
            continue

        placements = profile.get("placements")
        if not isinstance(placements, dict) or not placements:
            errors.append(f"{profile_name}: placements fehlt oder ist leer.")
            continue

        if profile.get("host_count") != expected_hosts:
            errors.append(f"{profile_name}: host_count muss {expected_hosts} sein.")
        if len(placements) != expected_hosts:
            errors.append(f"{profile_name}: Anzahl placements muss host_count entsprechen.")

        active = set(profile.get("active_environments") or [])
        if not active or not active.issubset(ENVIRONMENTS):
            errors.append(f"{profile_name}: active_environments ist ungültig.")
            active = set()

        monitoring_servers = 0
        environment_roles = {environment: set() for environment in active}

        for placement_name, placement in placements.items():
            if not isinstance(placement, dict):
                errors.append(f"{profile_name}/{placement_name}: Placement muss Objekt sein.")
                continue

            roles = set(placement.get("roles") or [])
            placement_envs = set(placement.get("environments") or [])

            unknown_roles = roles - HOST_ROLES
            if unknown_roles:
                errors.append(
                    f"{profile_name}/{placement_name}: unbekannte Rollen: "
                    + ", ".join(sorted(unknown_roles))
                )

            if "host_baseline" not in roles:
                errors.append(f"{profile_name}/{placement_name}: host_baseline fehlt.")
            if "monitoring_agent" not in roles:
                errors.append(f"{profile_name}/{placement_name}: monitoring_agent fehlt.")
            if "monitoring_server" in roles:
                monitoring_servers += 1

            if not placement_envs or not placement_envs.issubset(active):
                errors.append(
                    f"{profile_name}/{placement_name}: environments muss Teil von active_environments sein."
                )

            for environment in placement_envs:
                environment_roles.setdefault(environment, set()).update(roles)

        if monitoring_servers != 1:
            errors.append(f"{profile_name}: genau ein monitoring_server Placement ist erforderlich.")

        for environment in active:
            missing_roles = REQUIRED_ENVIRONMENT_ROLES - environment_roles.get(environment, set())
            if missing_roles:
                errors.append(
                    f"{profile_name}/{environment}: Rollen fehlen: "
                    + ", ".join(sorted(missing_roles))
                )

    current = document.get("current_profile")
    if current not in profiles:
        errors.append("current_profile muss auf ein vorhandenes Profil zeigen.")
    if current != "development-only":
        errors.append("current_profile muss in der aktuellen Aufbauphase development-only sein.")

    compact = profiles.get("compact") or {}
    compact_placements = compact.get("placements") or {}
    if len(compact_placements) == 1:
        only = next(iter(compact_placements.values()))
        if set(only.get("environments") or []) != ENVIRONMENTS:
            errors.append("compact muss alle drei Umgebungen auf dem Einzelhost zulassen.")

    standard = profiles.get("standard") or {}
    prod_colocated = False
    for placement in (standard.get("placements") or {}).values():
        if "production" in set(placement.get("environments") or []):
            roles = set(placement.get("roles") or [])
            if {"application", "database"}.issubset(roles):
                prod_colocated = True
    if not prod_colocated:
        errors.append("standard muss Production Application und Database gemeinsam platzieren.")

    split = profiles.get("split-production") or {}
    split_prod_placements = [
        set(placement.get("roles") or [])
        for placement in (split.get("placements") or {}).values()
        if "production" in set(placement.get("environments") or [])
    ]
    if not any("application" in roles and "database" not in roles for roles in split_prod_placements):
        errors.append("split-production benötigt einen separaten Production Application Host.")
    if not any("database" in roles and "application" not in roles for roles in split_prod_placements):
        errors.append("split-production benötigt einen separaten Production Database Host.")

    return errors


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_POLICY
    document = load_json(path)
    errors = validate(document)
    if errors:
        for error in errors:
            print(f"FEHLER: {error}", file=sys.stderr)
        return 1

    print(
        "Deployment-Topologien gültig: development-only, compact, standard "
        "und split-production erfüllen Rollen-, Isolations- und Placement-Regeln."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
