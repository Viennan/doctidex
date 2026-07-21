"""Whero Wiki identity, file classes, and curated collection discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_frontmatter, scalar_text
from .paths import parse_relative_path, path_from_root


WIKI_META_FILENAME = "whero-wiki-meta.md"
STATUS_FILENAME = "whero-wiki-view.md"
INDEX_FILENAME = "index.md"
LOG_FILENAME = "log.md"
FORMAT_VERSION = "0.0.2"
CURATED_FORMAT_VERSION = "0.0.2"
VIEW_REQUIRED_FIELD = "whero_view_required"
VIEW_FIELD = "whero_view"


@dataclass(frozen=True)
class CuratedCollection:
    section_name: str
    section_root: Path
    root: Path
    relative_root: PurePosixPath
    top_index: Path
    collection_index: Path


def is_view_required(fields: dict[str, Any]) -> bool:
    return frontmatter_is_true(fields, VIEW_REQUIRED_FIELD)


def is_view_metadata(fields: dict[str, Any]) -> bool:
    return frontmatter_is_true(fields, VIEW_FIELD)


def view_status_path(root: Path) -> Path | None:
    status = root / STATUS_FILENAME
    return status if os.path.lexists(status) else None


def is_view_root(root: Path) -> bool:
    status = view_status_path(root)
    if status is None:
        return False
    fields = read_frontmatter(status)
    if not is_view_metadata(fields):
        return False
    if scalar_text(fields.get("type")) != "Whero Wiki View":
        raise WheroToolError(f"invalid View type in {status}")
    if scalar_text(fields.get("format_version")) != FORMAT_VERSION:
        raise WheroToolError(f"invalid View format_version in {status}")
    if not frontmatter_is_true(fields, "whero_maintenance") or not frontmatter_is_true(
        fields, VIEW_REQUIRED_FIELD
    ):
        raise WheroToolError(f"invalid View framework flags in {status}")
    for key in ("requested_selections", "effective_roots"):
        if not isinstance(fields.get(key), list):
            raise WheroToolError(f"View metadata requires {key}: {status}")
    return True


def validate_wiki_root(raw_root: Path, *, allow_symlink_meta: bool = False) -> Path:
    try:
        root = raw_root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise WheroToolError(f"cannot resolve Wiki root {raw_root}: {exc}") from exc
    if not root.is_dir():
        raise WheroToolError(f"Wiki root is not a directory: {root}")
    meta = root / WIKI_META_FILENAME
    if not meta.is_file() or (meta.is_symlink() and not allow_symlink_meta):
        raise WheroToolError(
            f"source is not a Whero Wiki: missing regular {WIKI_META_FILENAME}"
        )
    fields = read_frontmatter(meta)
    if scalar_text(fields.get("type")) != "Whero Wiki":
        raise WheroToolError(
            f"invalid {WIKI_META_FILENAME}: type must be 'Whero Wiki'"
        )
    version = scalar_text(fields.get("format_version"))
    if version != FORMAT_VERSION:
        raise WheroToolError(
            f"invalid {WIKI_META_FILENAME}: unsupported format_version {version!r}"
        )
    required = ("whero_wiki", "whero_maintenance")
    missing = [key for key in required if not frontmatter_is_true(fields, key)]
    if not is_view_required(fields):
        missing.append(VIEW_REQUIRED_FIELD)
    if missing:
        raise WheroToolError(
            f"invalid {WIKI_META_FILENAME}: expected true for " + ", ".join(missing)
        )
    return root


def require_framework_file(
    path: Path,
    *,
    allow_symlink: bool = False,
) -> dict[str, Any]:
    if not path.is_file() or (path.is_symlink() and not allow_symlink):
        raise WheroToolError(f"missing regular framework file: {path}")
    fields = read_frontmatter(path)
    if not frontmatter_is_true(fields, "whero_maintenance"):
        raise WheroToolError(f"framework file must set whero_maintenance: true: {path}")
    if not is_view_required(fields):
        raise WheroToolError(
            f"framework file must set {VIEW_REQUIRED_FIELD}: true: {path}"
        )
    return fields


def discover_curated_collections(
    root: Path,
    *,
    excluded_roots: set[PurePosixPath] | None = None,
) -> tuple[list[CuratedCollection], list[str]]:
    collections: list[CuratedCollection] = []
    problems: list[str] = []
    excluded_roots = excluded_roots or set()
    for section_root in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        relative_section = PurePosixPath(section_root.name)
        if any(
            relative_section.parts[: len(excluded.parts)] == excluded.parts
            for excluded in excluded_roots
        ):
            continue
        top_index = section_root / INDEX_FILENAME
        if not top_index.is_file():
            continue
        try:
            fields = read_frontmatter(top_index)
        except WheroToolError as exc:
            problems.append(str(exc))
            continue
        raw_curated = fields.get("whero_curated_path")
        if raw_curated is None:
            continue
        try:
            curated_name = parse_relative_path(
                scalar_text(raw_curated),
                label=f"whero_curated_path in {top_index}",
                single_component=True,
            )
        except WheroToolError as exc:
            problems.append(str(exc))
            continue
        relative_root = PurePosixPath(section_root.name, *curated_name.parts)
        if any(
            relative_root.parts[: len(excluded.parts)] == excluded.parts
            for excluded in excluded_roots
        ):
            continue
        curated_root = path_from_root(root, relative_root)
        collection_index = curated_root / INDEX_FILENAME
        collections.append(
            CuratedCollection(
                section_root.name,
                section_root,
                curated_root,
                relative_root,
                top_index,
                collection_index,
            )
        )
    return collections, problems


def path_is_in_collection(
    relative: PurePosixPath,
    collection: CuratedCollection,
) -> bool:
    prefix = collection.relative_root.parts
    return relative.parts[: len(prefix)] == prefix
