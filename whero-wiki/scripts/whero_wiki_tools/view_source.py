"""Source Wiki discovery and framework-file classification for Views."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import WheroToolError
from .frontmatter import (
    frontmatter_is_true,
    read_flat_frontmatter,
    read_frontmatter,
    scalar_text,
)
from .model import STATUS_FILENAME, is_view_required, is_view_root, validate_wiki_root
from .view_errors import fail


def read_view_frontmatter(path: Path) -> dict[str, Any]:
    try:
        return read_frontmatter(path)
    except WheroToolError as exc:
        fail(str(exc))


def decode_frontmatter_string(value: Any) -> str:
    return scalar_text(value)


def validate_wiki_meta(source: Path) -> None:
    try:
        validate_wiki_root(source, allow_symlink_meta=is_view_root(source))
    except WheroToolError as exc:
        fail(str(exc))


def is_view_required_file(path: Path) -> bool:
    if path.name == STATUS_FILENAME:
        return False
    if path.suffix.lower() != ".md" or not path.is_file():
        return False
    try:
        fields = read_flat_frontmatter(path)
    except WheroToolError as exc:
        fail(str(exc))
    if not is_view_required(fields):
        return False
    if not frontmatter_is_true(fields, "whero_maintenance"):
        fail(f"View-required file must set whero_maintenance: true: {path}")
    return True


def source_files(
    source: Path,
    excluded_roots: set[PurePosixPath] | None = None,
) -> set[PurePosixPath]:
    files: set[PurePosixPath] = set()
    excluded_roots = excluded_roots or set()
    for directory, dirnames, filenames in os.walk(source, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(source).parts)
        retained: list[str] = []
        for name in dirnames:
            relative = (
                relative_current / name
                if relative_current.parts
                else PurePosixPath(name)
            )
            if name == ".git" or any(
                relative.parts[: len(root.parts)] == root.parts
                for root in excluded_roots
            ):
                continue
            if (current / name).is_symlink():
                files.add(relative)
                continue
            retained.append(name)
        dirnames[:] = retained
        for name in filenames:
            candidate = current / name
            if candidate.name == STATUS_FILENAME:
                continue
            if not candidate.is_file():
                continue
            files.add(PurePosixPath(*candidate.relative_to(source).parts))
    return files
