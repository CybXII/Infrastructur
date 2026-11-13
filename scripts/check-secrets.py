#!/usr/bin/env python3
"""Detect likely secrets without printing detected values."""

from __future__ import annotations

import argparse
import math
import pathlib
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass


HIGH_CONFIDENCE_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,255}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,255}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("stripe-live-key", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
)

GENERIC_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?:^|[\s,{])
    (?:
        password|passwd|pwd|
        api[_-]?key|
        access[_-]?token|
        auth[_-]?token|
        client[_-]?secret|
        webhook[_-]?secret
    )
    \s*[:=]\s*
    ["']?([^"'\s,#}\]]+)
    """
)

CONFIG_SUFFIXES = {
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".py",
    ".sh",
    ".js",
    ".ts",
}

SKIP_PATHS = {
    "scripts/check-secrets.py",
}

PLACEHOLDER_FRAGMENTS = (
    "change_me",
    "changeme",
    "placeholder",
    "example",
    "dummy",
    "redacted",
    "not-set",
    "not_set",
    "provider-policy",
    "secret_from_approved_source",
)


@dataclass(frozen=True)
class Finding:
    scope: str
    location: str
    rule: str


def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def is_config_like(path: str) -> bool:
    name = pathlib.PurePosixPath(path).name
    if name == ".env" or name.startswith(".env."):
        return True
    return pathlib.PurePosixPath(path).suffix.lower() in CONFIG_SUFFIXES


def looks_like_placeholder(value: str) -> bool:
    stripped = value.strip().strip("'\"")
    normalized = stripped.lower()

    if not normalized:
        return True
    if normalized.startswith(("$", "${", "{{", "<", "/run/secrets/")):
        return True
    if normalized in {"true", "false", "null", "none"}:
        return True
    if any(fragment in normalized for fragment in PLACEHOLDER_FRAGMENTS):
        return True
    if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", stripped):
        return True
    return False


def scan_line(path: str, line: str) -> list[str]:
    rules: list[str] = []

    for rule, pattern in HIGH_CONFIDENCE_PATTERNS:
        if pattern.search(line):
            rules.append(rule)

    if is_config_like(path):
        for match in GENERIC_ASSIGNMENT.finditer(line):
            value = match.group(1)
            if looks_like_placeholder(value):
                continue
            if len(value) >= 12 and (len(value) >= 20 or shannon_entropy(value) >= 3.0):
                rules.append("sensitive-assignment")

    return rules


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def scan_tree() -> list[Finding]:
    findings: list[Finding] = []

    for path in tracked_files():
        if path in SKIP_PATHS:
            continue

        file_path = pathlib.Path(path)
        try:
            data = file_path.read_bytes()
        except OSError:
            continue

        if len(data) > 2 * 1024 * 1024 or b"\0" in data:
            continue

        text = data.decode("utf-8", errors="replace")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule in scan_line(path, line):
                findings.append(Finding("tree", f"{path}:{line_number}", rule))

    return findings


def scan_history() -> list[Finding]:
    findings: list[Finding] = []
    process = subprocess.Popen(
        [
            "git",
            "log",
            "--all",
            "-p",
            "--no-ext-diff",
            "--unified=0",
            "--format=@@MERCHFACTORY_COMMIT %H",
            "--",
            ".",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert process.stdout is not None

    commit = "unknown"
    path = "unknown"

    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")

        if line.startswith("@@MERCHFACTORY_COMMIT "):
            commit = line.split(" ", 1)[1]
            continue

        if line.startswith("+++ b/"):
            path = line[6:]
            continue

        if path in SKIP_PATHS:
            continue

        if not line.startswith("+") or line.startswith("+++"):
            continue

        added_line = line[1:]
        for rule in scan_line(path, added_line):
            findings.append(Finding("history", f"{commit[:12]}:{path}", rule))

        if len(findings) >= 100:
            break

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"git log fehlgeschlagen: {stderr.strip()}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prüft Repository und Git-Historie auf wahrscheinliche Secrets."
    )
    parser.add_argument("--tree", action="store_true", help="aktuellen Git-Tree prüfen")
    parser.add_argument("--history", action="store_true", help="erreichbare Git-Historie prüfen")
    args = parser.parse_args()

    if not args.tree and not args.history:
        parser.error("mindestens --tree oder --history angeben")

    findings: list[Finding] = []
    if args.tree:
        findings.extend(scan_tree())
    if args.history:
        findings.extend(scan_history())

    unique = sorted(set(findings), key=lambda item: (item.scope, item.location, item.rule))

    if unique:
        for finding in unique[:100]:
            print(
                f"SECRET-CHECK: Regel {finding.rule} in "
                f"{finding.scope} bei {finding.location}",
                file=sys.stderr,
            )
        if len(unique) > 100:
            print(
                f"SECRET-CHECK: weitere {len(unique) - 100} Treffer ausgeblendet.",
                file=sys.stderr,
            )
        print(
            "SECRET-CHECK: potentielle Secrets gefunden. Werte werden absichtlich nicht ausgegeben.",
            file=sys.stderr,
        )
        return 1

    print("SECRET-CHECK: keine potentiellen Secrets gefunden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
