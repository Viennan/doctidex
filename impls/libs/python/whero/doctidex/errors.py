from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DoctidexError(Exception):
    message: str
    operation: str = "operation"
    affected: list[str] = field(default_factory=list)
    result: str = "No changes were made."
    actions: list[str] = field(default_factory=list)
    requires_user: str | None = None
    code: str = "doctidex_error"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def as_result(self, root: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "blocked",
            "operation": self.operation,
            "root": root,
            "affected": self.affected,
            "changed": [],
            "result": self.result,
            "findings": [
                {
                    "severity": "error",
                    "code": self.code,
                    "message": self.message,
                    "actions": self.actions,
                }
            ],
            "requires_user": self.requires_user,
        }
        if self.details:
            payload["details"] = self.details
        return payload
