"""Read and atomically write Markdown documents with YAML frontmatter."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .errors import WheroToolError


@dataclass(frozen=True)
class MarkdownDocument:
    fields: dict[str, Any]
    body: str
    has_frontmatter: bool


def read_markdown(path: Path) -> MarkdownDocument:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise WheroToolError(f"cannot read Markdown file {path}: {exc}") from exc

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return MarkdownDocument({}, text, False)

    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        raise WheroToolError(f"unterminated YAML frontmatter in {path}")
    raw = "".join(lines[1:closing])
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise WheroToolError(f"invalid YAML frontmatter in {path}: {exc}") from exc
    if loaded is None:
        fields: dict[str, Any] = {}
    elif isinstance(loaded, dict) and all(isinstance(key, str) for key in loaded):
        fields = dict(loaded)
    else:
        raise WheroToolError(f"YAML frontmatter must be a mapping in {path}")
    return MarkdownDocument(fields, "".join(lines[closing + 1 :]), True)


def read_frontmatter(path: Path) -> dict[str, Any]:
    return read_markdown(path).fields


def read_flat_frontmatter(path: Path) -> dict[str, str]:
    """Read top-level scalar-looking fields without requiring source YAML validity."""
    try:
        with path.open(encoding="utf-8") as stream:
            first = stream.readline()
            if first.strip() != "---":
                return {}
            fields: dict[str, str] = {}
            characters = len(first)
            for line_number, line in enumerate(stream, start=2):
                characters += len(line)
                if line_number > 256 or characters > 65536:
                    return {}
                stripped = line.strip()
                if stripped == "---":
                    return fields
                if not stripped or stripped.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
    except (OSError, UnicodeError) as exc:
        raise WheroToolError(f"cannot read Markdown frontmatter from {path}: {exc}") from exc
    return {}


def frontmatter_is_true(fields: Mapping[str, Any], key: str) -> bool:
    value = fields.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.split("#", 1)[0].strip().lower() == "true"
    return False


def scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def render_markdown(fields: Mapping[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(
        dict(fields),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip()
    normalized_body = body if body.startswith("\n") else f"\n{body}"
    return f"---\n{frontmatter}\n---\n{normalized_body}"


def write_markdown_atomic(
    path: Path,
    fields: Mapping[str, Any],
    body: str,
    *,
    overwrite: bool = False,
) -> None:
    if not overwrite and os.path.lexists(path):
        raise WheroToolError(f"refusing to overwrite existing path: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise WheroToolError(f"cannot create directory {path.parent}: {exc}") from exc

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary.write(render_markdown(fields, body))
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    except OSError as exc:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        raise WheroToolError(f"cannot write Markdown file {path}: {exc}") from exc
