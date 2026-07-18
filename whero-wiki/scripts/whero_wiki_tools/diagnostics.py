"""Structured validator diagnostics with compact text and JSON output."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    path: str | None = None


class Diagnostics:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.items: list[Diagnostic] = []

    def add(
        self,
        severity: str,
        code: str,
        message: str,
        path: Path | str | None = None,
    ) -> None:
        rendered_path: str | None
        if isinstance(path, Path):
            try:
                rendered_path = path.relative_to(self.root).as_posix()
            except ValueError:
                rendered_path = str(path)
        else:
            rendered_path = path
        self.items.append(Diagnostic(severity, code, message, rendered_path))

    def error(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("error", code, message, path)

    def warning(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("warning", code, message, path)

    def notice(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.add("notice", code, message, path)

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.items)

    def render_text(self) -> str:
        lines = []
        for item in self.items:
            location = f" {item.path}:" if item.path else ""
            lines.append(f"{item.severity.upper()} {item.code}{location} {item.message}")
        return "\n".join(lines)

    def render_json(self) -> str:
        counts = {
            severity: sum(item.severity == severity for item in self.items)
            for severity in ("error", "warning", "notice")
        }
        return json.dumps(
            {
                "diagnostics": [asdict(item) for item in self.items],
                "counts": counts,
            },
            indent=2,
            ensure_ascii=True,
        )

