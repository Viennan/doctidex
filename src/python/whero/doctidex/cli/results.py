"""Machine-readable result envelopes for the CLI foundation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def success(*, command: str, repos_path: str | None = None, **fields: Any) -> dict[str, Any]:
    """Build the common successful command result."""

    result: dict[str, Any] = {"status": "ok", "message": {}}
    if repos_path is not None:
        result["context"] = {"command": command, "repos-path": repos_path}
    result.update(fields)
    return result


def error(
    *,
    command: str,
    code: str,
    summary: str,
    details: Mapping[str, Any],
    repos_path: str | None = None,
    subject: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the common structured command error result."""

    context: dict[str, Any] = {"command": command}
    if repos_path is not None:
        context["repos-path"] = repos_path

    message: dict[str, Any] = {
        "code": code,
        "summary": summary,
        "context": context,
        "details": dict(details),
    }
    if subject is not None:
        message["subject"] = dict(subject)
    return {"status": "error", "message": message}


def argument_error(
    *,
    command: str,
    received: Sequence[str],
    constraint: str,
    parameter: str | None = None,
    repos_path: str | None = None,
) -> dict[str, Any]:
    """Build an ``argument.invalid`` result without exposing parser internals."""

    return error(
        command=command,
        code="argument.invalid",
        summary="The command arguments do not satisfy the documented command contract.",
        details={
            "parameter": parameter,
            "received": list(received),
            "constraint": constraint,
        },
        repos_path=repos_path,
    )
