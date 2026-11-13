#!/usr/bin/env python3
"""Evaluate public probe destinations before publication (no live network changes).

Hostname allowlisting is necessary but not sufficient. This module rejects
non-public DNS answers, including mixed public/private responses. Runtime egress
filtering and pinned DNS resolution remain necessary to prevent rebinding.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


def public_addresses(hostname: str, resolver=socket.getaddrinfo) -> tuple[str, ...]:
    """Fail closed if any returned A/AAAA address is not globally routable."""
    if not isinstance(hostname, str) or not hostname:
        raise ValueError("missing hostname")
    try:
        records = resolver(hostname, None, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ValueError(f"DNS resolution failed for {hostname}") from exc
    result = set()
    for record in records:
        if len(record) < 5 or not record[4]:
            raise ValueError("malformed DNS record")
        address = record[4][0]
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise PermissionError(f"non-public DNS result for {hostname}: {ip}")
        result.add(str(ip))
    if not result:
        raise ValueError(f"no DNS results for {hostname}")
    return tuple(sorted(result))


def validate_public_targets(manifest: dict, resolver=socket.getaddrinfo) -> dict[str, tuple[str, ...]]:
    """Resolve all registered HTTP, TLS and DNS hosts; never trust only the URL."""
    hosts = set()
    for item in manifest["http"]:
        hosts.add(urlsplit(item["url"]).hostname)
    for item in manifest["tls"]:
        hosts.add(item["target"].rsplit(":", 1)[0])
    for item in manifest["dns"]:
        hosts.add(item["name"])
    return {host: public_addresses(host, resolver=resolver) for host in sorted(hosts)}
