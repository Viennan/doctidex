from __future__ import annotations

from dataclasses import dataclass

import regex


@dataclass(frozen=True, slots=True)
class RegexCompileError(ValueError):
    message: str
    position: int | None = None

    def __str__(self) -> str:
        return f"{self.message} at character {self.position}" if self.position is not None else self.message


class DoctidexPattern:
    """Pinned regex VERSION1 semantics for doctidex filter conditions."""

    def __init__(self, pattern: str) -> None:
        try:
            self._compiled = regex.compile(pattern, regex.VERSION1 | regex.UNICODE)
        except regex.error as exc:
            raise RegexCompileError(str(exc), getattr(exc, "pos", None)) from exc

    def search(self, value: str) -> bool:
        return self._compiled.search(value) is not None
