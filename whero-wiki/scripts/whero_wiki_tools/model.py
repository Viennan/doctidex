"""Whero Wiki identity, file classes, and curated collection discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_frontmatter, scalar_text
from .paths import parse_relative_path, path_from_root


WIKI_META_FILENAME = "whero-wiki-meta.md"
STATUS_FILENAME = "partial-disclosure.md"
INDEX_FILENAME = "index.md"
LOG_FILENAME = "log.md"


@dataclass(frozen=True)
class CuratedCollection:
    scope_name: str
    scope_root: Path
    root: Path
    relative_root: PurePosixPath
    top_index: Path
    collection_index: Path


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
    required = ("whero_wiki", "whero_maintenance", "whero_scope_required")
    missing = [key for key in required if not frontmatter_is_true(fields, key)]
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
    if not frontmatter_is_true(fields, "whero_scope_required"):
        raise WheroToolError(f"framework file must set whero_scope_required: true: {path}")
    return fields


def discover_curated_collections(root: Path) -> tuple[list[CuratedCollection], list[str]]:
    collections: list[CuratedCollection] = []
    problems: list[str] = []
    for scope_root in sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        top_index = scope_root / INDEX_FILENAME
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
        relative_root = PurePosixPath(scope_root.name, *curated_name.parts)
        curated_root = path_from_root(root, relative_root)
        collection_index = curated_root / INDEX_FILENAME
        collections.append(
            CuratedCollection(
                scope_root.name,
                scope_root,
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
