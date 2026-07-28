from __future__ import annotations

import json
from typing import Any


def render_human(payload: dict[str, Any]) -> str:
    if payload.get("status") == "blocked":
        finding = (payload.get("findings") or [{}])[0]
        lines = [
            f"Cannot continue: {payload.get('operation', 'operation')}",
            f"Reason: {finding.get('message', 'The operation is blocked.')}",
            f"Still available: {payload.get('result', 'No result was changed.')}",
            f"Changes made: {', '.join(payload.get('changed', [])) or 'none'}",
            "Next actions:",
        ]
        actions = finding.get("actions", [])
        lines.extend(f"{index}. {action}" for index, action in enumerate(actions, 1))
        lines.append(f"Need from user: {payload.get('requires_user') or 'none'}")
        return "\n".join(lines)

    preferred = [
        "status",
        "operation",
        "root",
        "result",
        "protocol_structure",
        "semantic_review",
        "plugin_readiness",
        "mount_state",
        "mount_path",
        "source",
        "declared_revision",
        "effective_commit",
        "readable",
        "maintenance_root",
        "base_commit",
        "target_branch",
        "root_relation",
        "maintenance_reuse",
        "changed",
        "planned_changes",
        "findings",
        "semantic_candidates",
        "items",
        "collection",
        "next_actions",
    ]
    lines: list[str] = []
    emitted: set[str] = set()
    for key in preferred:
        if key not in payload or payload[key] in (None, [], {}):
            continue
        lines.append(f"{_label(key)}: {_format(payload[key])}")
        emitted.add(key)
    for key in sorted(payload):
        if key in emitted or key in {"details"} or payload[key] in (None, [], {}):
            continue
        lines.append(f"{_label(key)}: {_format(payload[key])}")
    return "\n".join(lines)


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _format(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def _label(value: str) -> str:
    return value.replace("_", " ").capitalize()
