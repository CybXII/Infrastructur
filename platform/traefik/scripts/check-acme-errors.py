#!/usr/bin/env python3
"""Erkennt ACME-Ausstellungs- und Erneuerungsfehler in Traefik-Logs."""

from __future__ import annotations

import re
import sys

PATTERNS = [
    re.compile(r"unable to obtain acme certificate", re.IGNORECASE),
    re.compile(r"unable to generate a certificate", re.IGNORECASE),
    re.compile(r"acme.*(?:renew|renewal).*(?:error|fail)", re.IGNORECASE),
    re.compile(r"(?:error|fail).*acme.*(?:renew|renewal)", re.IGNORECASE),
    re.compile(r"acme: error", re.IGNORECASE),
    re.compile(r"certificate.*renewal.*failed", re.IGNORECASE),
]


def main() -> int:
    matches: list[str] = []

    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if any(pattern.search(line) for pattern in PATTERNS):
            matches.append(line)

    if matches:
        print("ACME-Fehler erkannt:", file=sys.stderr)
        for line in matches:
            print(f"  {line}", file=sys.stderr)
        return 1

    print("Keine ACME-Ausstellungs- oder Erneuerungsfehler erkannt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
