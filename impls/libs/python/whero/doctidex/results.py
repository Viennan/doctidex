from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterable
from typing import Any

SCHEMA_VERSION = "1.0"


def finding(
    domain: str,
    severity: str,
    code: str,
    message: str,
    *,
    path: str | None = None,
    actions: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "domain": domain,
        "severity": severity,
        "code": code,
        "message": message,
        "path": path,
        "actions": list(actions),
    }


def envelope(
    operation: str,
    *,
    status: str = "ok",
    result: str,
    root: str | None = None,
    changed: Iterable[str] = (),
    network: bool = False,
    findings: Iterable[dict[str, Any]] = (),
    next_actions: Iterable[str] = (),
    affected: Iterable[str] = (),
    requires_user: str | None = None,
    collection: dict[str, Any] | None = None,
    **fields: Any,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": operation,
        "status": status,
        "result": result,
        "root": root,
        "changed": list(changed),
        "network": network,
        "findings": list(findings),
        "next_actions": list(next_actions),
        "affected": list(affected),
        "requires_user": requires_user,
        "collection": collection,
        **fields,
    }


def query_identity(operation: str, **parts: Any) -> str:
    encoded = json.dumps(
        {"operation": operation, **parts}, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def encode_cursor(identity: str, state: str, offsets: dict[str, int]) -> str:
    raw = json.dumps(
        {"identity": identity, "state": state, "offsets": offsets},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(token: str, identity: str, state: str) -> dict[str, int]:
    try:
        padding = "=" * (-len(token) % 4)
        value = json.loads(base64.urlsafe_b64decode(token + padding))
        offsets = value["offsets"]
        if value["identity"] != identity or value["state"] != state or not isinstance(offsets, dict):
            raise ValueError
        parsed = {str(key): int(offset) for key, offset in offsets.items()}
        if any(offset < 0 for offset in parsed.values()):
            raise ValueError
        return parsed
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("cursor_invalid") from exc


def paginate_lists(
    values: dict[str, list[Any]],
    *,
    limit: int,
    identity: str,
    state: str,
    cursor: str | None,
) -> tuple[dict[str, list[Any]], dict[str, Any]]:
    offsets = {name: 0 for name in values}
    if cursor:
        decoded = decode_cursor(cursor, identity, state)
        if set(decoded) != set(values):
            raise ValueError("cursor_invalid")
        offsets = decoded

    pages: dict[str, list[Any]] = {}
    lists: dict[str, dict[str, Any]] = {}
    next_offsets: dict[str, int] = {}
    truncated = False
    for name, items in values.items():
        start = offsets[name]
        if start > len(items):
            raise ValueError("cursor_invalid")
        page = items[start : start + limit]
        end = start + len(page)
        more = end < len(items)
        pages[name] = page
        lists[name] = {"total": len(items), "returned": len(page), "truncated": more}
        next_offsets[name] = end
        truncated = truncated or more

    collection = {
        "limit": limit,
        "lists": lists,
        "truncated": truncated,
        "next_cursor": encode_cursor(identity, state, next_offsets) if truncated else None,
    }
    return pages, collection
