"""Discover index-declared preserved files and directories."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_flat_frontmatter, read_frontmatter
from .model import INDEX_FILENAME, LOG_FILENAME, STATUS_FILENAME, WIKI_META_FILENAME
from .paths import parse_relative_path, path_from_root


PRESERVED_FIELD = "whero_preserved_paths"
PRESERVED_KEY_RE = re.compile(rf"^{PRESERVED_FIELD}\s*:")
RESERVED_FRAMEWORK_NAMES = {
    INDEX_FILENAME,
    LOG_FILENAME,
    STATUS_FILENAME,
    WIKI_META_FILENAME,
}


@dataclass(frozen=True)
class PreservedPath:
    path: PurePosixPath
    root: Path
    index: Path


def _declares_preserved(index: Path) -> bool:
    """Avoid parsing collected index files unless they declare the Whero key."""
    try:
        with index.open(encoding="utf-8") as stream:
            if stream.readline().strip() != "---":
                return False
            for line_number, line in enumerate(stream, start=2):
                if line_number > 256:
                    return False
                if line.strip() == "---":
                    return False
                if PRESERVED_KEY_RE.match(line):
                    return True
    except (OSError, UnicodeError):
        return False
    return False


def _is_partial_root(root: Path) -> bool:
    status = root / STATUS_FILENAME
    if not status.is_file():
        return False
    try:
        return frontmatter_is_true(
            read_flat_frontmatter(status),
            "whero_partial_disclosure",
        )
    except WheroToolError:
        return False


def _valid_nested_wiki(path: Path) -> bool:
    meta = path / WIKI_META_FILENAME
    if not meta.is_file():
        return False
    try:
        fields = read_flat_frontmatter(meta)
    except WheroToolError:
        return False
    return all(
        frontmatter_is_true(fields, key)
        for key in ("whero_wiki", "whero_maintenance", "whero_scope_required")
    )


def path_is_within(relative: PurePosixPath, boundary: PurePosixPath) -> bool:
    return relative.parts[: len(boundary.parts)] == boundary.parts


def preserved_for_path(
    relative: PurePosixPath,
    preserved: list[PreservedPath],
) -> PreservedPath | None:
    matches = [entry for entry in preserved if path_is_within(relative, entry.path)]
    return max(matches, key=lambda entry: len(entry.path.parts), default=None)


def discover_preserved_paths(
    root: Path,
    *,
    excluded_roots: set[PurePosixPath] | None = None,
) -> tuple[list[PreservedPath], list[str]]:
    """Read preserved declarations without entering existing ownership mounts."""
    root = root.resolve(strict=False)
    excluded_roots = excluded_roots or set()
    entries: list[PreservedPath] = []
    problems: list[str] = []
    disclosed_directory_links: list[Path] = []
    partial = _is_partial_root(root)

    def scan_index(current: Path, filenames: list[str]) -> None:
        index = current / INDEX_FILENAME
        if INDEX_FILENAME not in filenames or not _declares_preserved(index):
            return
        relative_current = PurePosixPath(*current.relative_to(root).parts)
        try:
            fields = read_frontmatter(index)
        except WheroToolError as exc:
            problems.append(str(exc))
            return
        raw_paths = fields.get(PRESERVED_FIELD)
        if not frontmatter_is_true(fields, "whero_maintenance") or not frontmatter_is_true(
            fields, "whero_scope_required"
        ):
            problems.append(
                f"{PRESERVED_FIELD} requires a maintained, scope-required index: {index}"
            )
            return
        if not isinstance(raw_paths, list):
            problems.append(f"{PRESERVED_FIELD} must be a YAML list: {index}")
            return
        for raw_path in raw_paths:
            if not isinstance(raw_path, str):
                problems.append(f"{PRESERVED_FIELD} entries must be strings: {index}")
                continue
            try:
                declared = parse_relative_path(
                    raw_path,
                    label=f"preserved path in {index}",
                )
            except WheroToolError as exc:
                problems.append(str(exc))
                continue
            relative = (
                relative_current / declared if relative_current.parts else declared
            )
            if relative.name in RESERVED_FRAMEWORK_NAMES:
                problems.append(f"framework files cannot be declared preserved: {relative}")
                continue
            containing_mount = next(
                (
                    mount
                    for mount in excluded_roots
                    if path_is_within(relative, mount) and relative != mount
                ),
                None,
            )
            if containing_mount is not None:
                problems.append(
                    "preserved paths cannot enter an existing mount boundary: "
                    f"{relative} is inside {containing_mount}"
                )
                continue
            entries.append(PreservedPath(relative, path_from_root(root, relative), index))

    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(root).parts)
        scan_index(current, filenames)
        blocked_roots = excluded_roots | {entry.path for entry in entries}
        retained: list[str] = []
        for name in dirnames:
            child_path = current / name
            child = (
                relative_current / name
                if relative_current.parts
                else PurePosixPath(name)
            )
            if name == ".git" or any(
                path_is_within(child, boundary) for boundary in blocked_roots
            ):
                continue
            if child_path.is_symlink() and partial:
                disclosed_directory_links.append(child_path)
                continue
            retained.append(name)
        dirnames[:] = retained

    for disclosed_root in disclosed_directory_links:
        for directory, dirnames, filenames in os.walk(disclosed_root, followlinks=False):
            current = Path(directory)
            relative_current = PurePosixPath(*current.relative_to(root).parts)
            scan_index(current, filenames)
            blocked_roots = excluded_roots | {entry.path for entry in entries}
            retained = []
            for name in dirnames:
                child_path = current / name
                child = (
                    relative_current / name
                    if relative_current.parts
                    else PurePosixPath(name)
                )
                if (
                    child_path.is_symlink()
                    or (child_path / ".git").exists()
                    or _valid_nested_wiki(child_path)
                    or any(path_is_within(child, boundary) for boundary in blocked_roots)
                ):
                    continue
                retained.append(name)
            dirnames[:] = retained

    collapsed: list[PreservedPath] = []
    for entry in sorted(entries, key=lambda item: (len(item.path.parts), str(item.path))):
        parent = preserved_for_path(entry.path, collapsed)
        if parent is not None:
            problems.append(
                f"preserved paths must not overlap: {entry.path} is inside {parent.path}"
            )
            continue
        collapsed.append(entry)
    return collapsed, problems
