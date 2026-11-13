#!/usr/bin/env python3
"""Validate the machine-readable v0.5 container platform evidence matrix."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = REPO_ROOT / "configuration" / "platform-validation.json"

MANDATORY_CAPABILITIES = {
    "routing",
    "tls",
    "isolation",
    "persistence",
    "rollback",
    "cleanup",
}

MANDATORY_FAILURE_MODES = {
    "backend-not-ready",
    "acme-renewal-error",
    "network-isolation-drift",
    "container-memory-exhaustion",
    "container-pid-exhaustion",
    "log-flood",
    "failed-release",
    "container-recreate",
    "secret-path-traversal",
    "cleanup-unstable-release-state",
    "cleanup-rollback-artifact-protection",
}


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Validation-Matrix kann nicht gelesen werden: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("Validation-Matrix muss ein JSON-Objekt sein.")
    return document


def workflow_has_job(path: pathlib.Path, job_id: str) -> bool:
    content = path.read_text(encoding="utf-8")
    return bool(
        re.search(
            rf"(?m)^  {re.escape(job_id)}:\s*$",
            content,
        )
    )


def validate(document: dict[str, Any], root: pathlib.Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []

    if document.get("version") != 1:
        errors.append("version muss 1 sein.")
    if document.get("release") != "v0.5":
        errors.append("release muss v0.5 sein.")
    if document.get("epic") != 67:
        errors.append("epic muss #67 sein.")
    if document.get("validation_issue") != 81:
        errors.append("validation_issue muss #81 sein.")

    release = document.get("monitoring_release") or {}
    if release.get("decision") != "approved":
        errors.append("Monitoring-Release muss explizit approved sein.")
    if not str(release.get("does_not_mean") or "").strip():
        errors.append("Monitoring-Release muss seine Scope-Grenze dokumentieren.")

    capabilities = document.get("required_capabilities")
    if not isinstance(capabilities, dict):
        errors.append("required_capabilities fehlt oder ist ungültig.")
        capabilities = {}

    missing = MANDATORY_CAPABILITIES - set(capabilities)
    if missing:
        errors.append(
            "Pflichtfähigkeiten fehlen: " + ", ".join(sorted(missing))
        )

    for capability, definition in capabilities.items():
        if not isinstance(definition, dict):
            errors.append(f"{capability}: Definition muss Objekt sein.")
            continue

        evidence = definition.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{capability}: mindestens ein Evidenz-Eintrag erforderlich.")
            continue

        valid_runtime_evidence = 0
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"{capability}[{index}]: Evidenz muss Objekt sein.")
                continue

            workflow_rel = item.get("workflow")
            job_id = item.get("job_id")
            test_rel = item.get("test")

            if not workflow_rel or not job_id or not test_rel:
                errors.append(
                    f"{capability}[{index}]: workflow, job_id und test sind Pflicht."
                )
                continue

            workflow = root / str(workflow_rel)
            test_path = root / str(test_rel)

            if not workflow.is_file():
                errors.append(f"{capability}: Workflow fehlt: {workflow_rel}")
            elif not workflow_has_job(workflow, str(job_id)):
                errors.append(
                    f"{capability}: Job {job_id!r} fehlt in {workflow_rel}."
                )

            if not test_path.is_file():
                errors.append(f"{capability}: Evidenzdatei fehlt: {test_rel}")
            else:
                valid_runtime_evidence += 1

        if definition.get("runtime_required") is True and valid_runtime_evidence < 1:
            errors.append(f"{capability}: Runtime-Evidenz fehlt.")

    failure_modes = document.get("failure_modes")
    if not isinstance(failure_modes, list):
        errors.append("failure_modes fehlt oder ist ungültig.")
        failure_modes = []

    ids: set[str] = set()
    for item in failure_modes:
        if not isinstance(item, dict):
            errors.append("failure_modes: Eintrag muss Objekt sein.")
            continue
        mode_id = str(item.get("id") or "")
        if not mode_id:
            errors.append("failure_modes: id fehlt.")
            continue
        if mode_id in ids:
            errors.append(f"failure_modes: doppelte id {mode_id}.")
        ids.add(mode_id)

        if not str(item.get("expected_behavior") or "").strip():
            errors.append(f"{mode_id}: expected_behavior fehlt.")

        evidence_rel = item.get("evidence")
        if not evidence_rel or not (root / str(evidence_rel)).is_file():
            errors.append(f"{mode_id}: Evidenzdatei fehlt: {evidence_rel}")

    missing_failure_modes = MANDATORY_FAILURE_MODES - ids
    if missing_failure_modes:
        errors.append(
            "Pflicht-Fehlerfälle fehlen: "
            + ", ".join(sorted(missing_failure_modes))
        )

    limitations = document.get("ci_limitations")
    if not isinstance(limitations, list) or len(limitations) < 2:
        errors.append("CI-Grenzen müssen explizit dokumentiert sein.")

    open_items = document.get("known_open_items")
    if not isinstance(open_items, list):
        errors.append("known_open_items fehlt oder ist ungültig.")
        open_items = []

    by_issue = {
        item.get("issue"): item
        for item in open_items
        if isinstance(item, dict)
    }
    if 231 in by_issue:
        errors.append("#231 darf nach Umsetzung nicht mehr als offener v0.5-Punkt geführt werden.")

    completed_items = document.get("completed_items")
    if not isinstance(completed_items, list):
        errors.append("completed_items fehlt oder ist ungültig.")
        completed_items = []

    completed_by_issue = {
        item.get("issue"): item
        for item in completed_items
        if isinstance(item, dict)
    }
    cleanup = completed_by_issue.get(231)
    if not cleanup:
        errors.append("#231 muss als abgeschlossenes v0.5-Follow-up dokumentiert sein.")
    else:
        if cleanup.get("status") != "completed":
            errors.append("#231 muss status=completed besitzen.")
        evidence_rel = cleanup.get("evidence")
        if not evidence_rel or not (root / str(evidence_rel)).is_file():
            errors.append(f"#231 Evidenzdatei fehlt: {evidence_rel}")

    if open_items:
        errors.append(
            "Für den v0.5-Abschluss dürfen keine known_open_items verbleiben."
        )

    review = completed_by_issue.get(82)
    if not review:
        errors.append("#82 muss als abgeschlossenes v0.5-Review dokumentiert sein.")
    else:
        if review.get("status") != "completed":
            errors.append("#82 muss status=completed besitzen.")
        evidence_rel = review.get("evidence")
        if not evidence_rel or not (root / str(evidence_rel)).is_file():
            errors.append(f"#82 Evidenzdatei fehlt: {evidence_rel}")

    closure = document.get("release_closure")
    if not isinstance(closure, dict):
        errors.append("release_closure fehlt oder ist ungültig.")
    else:
        if closure.get("decision") != "approved":
            errors.append("v0.5 Release-Abschluss muss approved sein.")
        if closure.get("review_issue") != 82:
            errors.append("release_closure.review_issue muss #82 sein.")
        if closure.get("epic") != 67:
            errors.append("release_closure.epic muss #67 sein.")
        if closure.get("open_blockers") != 0:
            errors.append("v0.5 darf keine offenen Abschlussblocker enthalten.")
        if closure.get("next_epic") != 83:
            errors.append("release_closure.next_epic muss #83 sein.")
        if closure.get("first_next_issue") != 84:
            errors.append("release_closure.first_next_issue muss #84 sein.")
        review_evidence = closure.get("review_evidence")
        if not review_evidence or not (root / str(review_evidence)).is_file():
            errors.append(
                f"Release-Abschlussreview fehlt: {review_evidence}"
            )

    return errors


def main() -> int:
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MATRIX
    document = load_json(path)
    errors = validate(document)

    if errors:
        for error in errors:
            print(f"FEHLER: {error}", file=sys.stderr)
        return 1

    print(
        "v0.5 Containerplattform abgeschlossen: "
        "Pflichtfähigkeiten, Fehlerfälle und Release-Gate sind vollständig validiert."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
