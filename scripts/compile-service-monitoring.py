#!/usr/bin/env python3
"""Compile app-owned monitoring manifests to Prometheus file_sd JSON.

Offline compiler: does not write system directories, reload Prometheus or deploy.
Only an already authorized infrastructure deployment process may publish output.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import pathlib
import re
import tempfile
from urllib.parse import urlsplit

SERVICE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
HOST = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$")
KEYS = {"schema_version", "service", "environment", "http", "tls", "dns", "labels"}
ENVIRONMENTS = {"development", "production"}


def valid_hostname(value: str) -> str:
    if not isinstance(value, str) or not HOST.fullmatch(value) or value != value.lower():
        raise ValueError("target must be a lowercase public DNS hostname")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise ValueError("IP literals are not allowed")


def compile_manifest(doc: dict) -> dict:
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise ValueError("manifest fields do not match schema v1")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1 or not isinstance(doc["environment"], str) or doc["environment"] not in ENVIRONMENTS:
        raise ValueError("unsupported schema or environment")
    service = doc["service"]
    if not isinstance(service, str) or not SERVICE.fullmatch(service):
        raise ValueError("invalid service identifier")

    labels = doc["labels"]
    if labels != {"component": "service-probe"}:
        raise ValueError("unsupported additional labels")

    # Fail closed for malformed collection types; never iterate strings or dicts.
    for kind in ("http", "tls", "dns"):
        if not isinstance(doc[kind], list):
            raise ValueError(f"{kind} checks must be a list")

    out = {"http": [], "tls": []}
    seen = set()
    for item in doc["http"]:
        if not isinstance(item, dict) or set(item) != {"url", "expected_status"}:
            raise ValueError("invalid http check")
        url = item["url"]
        if not isinstance(url, str):
            raise ValueError("invalid http url")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port not in (None, 443)
                or parsed.netloc not in {parsed.hostname or "", f"{parsed.hostname}:443"}
                or any(char in url for char in ("\\r", "\\n", "\\t", "\\\\"))):
            raise ValueError("only public HTTPS URLs on port 443 are allowed")
        valid_hostname(parsed.hostname or "")
        if type(item["expected_status"]) is not int or item["expected_status"] != 200:
            raise ValueError("schema v1 supports HTTP 200 only")
        if url in seen:
            raise ValueError("duplicate http target")
        seen.add(url)
        out["http"].append(url)

    seen.clear()
    for item in doc["tls"]:
        if not isinstance(item, dict) or set(item) != {"target"}:
            raise ValueError("invalid tls check")
        host, sep, port = item["target"].rpartition(":")
        if not sep or port != "443":
            raise ValueError("TLS target must have port 443")
        valid_hostname(host)
        if item["target"] in seen:
            raise ValueError("duplicate tls target")
        seen.add(item["target"])
        out["tls"].append(item["target"])

    seen.clear()
    for item in doc["dns"]:
        if not isinstance(item, dict) or set(item) != {"name", "type"}:
            raise ValueError("invalid dns check")
        name = valid_hostname(item["name"])
        if item["type"] != "A" or name in seen:
            raise ValueError("invalid or duplicate DNS A record check")
        seen.add(name)

    if not out["http"] or not out["tls"] or not doc["dns"]:
        raise ValueError("schema v1 requires HTTP, TLS and DNS checks")
    if any(len(v) > 10 for v in (out["http"], out["tls"], doc["dns"])):
        raise ValueError("too many probe targets")
    group = {"service": service, "environment": doc["environment"], "component": "service-probe"}
    return {
        "service": service,
        "environment": doc["environment"],
        "files": {
            "http": [{"targets": out["http"], "labels": group}],
            "tls": [{"targets": out["tls"], "labels": group}],
        },
        "dns_names": [x["name"] for x in doc["dns"]],
    }


def write_atomic(path: pathlib.Path, payload: object) -> None:
    # This tool runs in a caller-owned staging directory; never write to the live TSDB.
    if path.is_symlink():
        raise ValueError("refusing symlink target")
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    handle, tmp = tempfile.mkstemp(prefix=".monitoring-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=pathlib.Path)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    args = parser.parse_args()
    doc = json.loads(args.manifest.read_text(encoding="utf-8"))
    compiled = compile_manifest(doc)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = compiled["environment"] + "--" + compiled["service"]
    for kind, data in compiled["files"].items():
        folder = output / kind
        folder.mkdir(exist_ok=True)
        write_atomic(folder / (prefix + ".json"), data)
    # DNS needs validated, platform-generated modules (query_name) before being
    # enabled. Persist as staging metadata only; do not silently fake DNS checks.
    write_atomic(output / (prefix + ".dns.json"), compiled["dns_names"])
    print(f"Validated staging targets for {prefix}; DNS registration pending")


if __name__ == "__main__":
    main()
