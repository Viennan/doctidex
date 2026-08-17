from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from whero.doctidex.results import envelope, finding


@dataclass(slots=True)
class DoctidexError(Exception):
    message: str
    operation: str = "operation"
    affected: list[str] = field(default_factory=list)
    result: str = "No changes were made."
    actions: list[str] = field(default_factory=list)
    requires_user: str | None = None
    code: str = "doctidex_error"
    domain: str = "command"
    path: str | None = None
    network: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message

    def as_result(self, root: str | None = None) -> dict[str, Any]:
        payload = envelope(
            self.operation,
            status="blocked",
            result=self.result,
            root=root,
            network=self.network,
            findings=[
                finding(
                    self.domain,
                    "error",
                    self.code,
                    self.message,
                    path=self.path,
                    actions=self.actions,
                )
            ],
            affected=self.affected,
            requires_user=self.requires_user,
        )
        if self.details:
            payload["details"] = self.details
        payload.update(self.fields)
        return payload
