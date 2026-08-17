"""Workflow failures converted to the public CLI error envelope."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class CommandFailure(RuntimeError):
    """A domain-level command failure with its documented diagnostic fields."""

    def __init__(
        self,
        *,
        code: str,
        summary: str,
        details: Mapping[str, Any],
        subject: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary
        self.details = dict(details)
        self.subject = dict(subject) if subject is not None else None
