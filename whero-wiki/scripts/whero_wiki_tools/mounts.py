"""Discover nested Whero Wikis and Git submodules as ownership boundaries."""

from __future__ import annotations

import configparser
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_frontmatter
from .git import sanitize_remote_url
from .model import (
    INDEX_FILENAME,
    is_view_required,
    is_view_root,
    validate_wiki_root,
)
from .paths import is_within, parse_relative_path, path_from_root
from .preserved import PreservedPath, discover_preserved_paths, path_is_within


@dataclass(frozen=True)
class WikiMount:
    path: PurePosixPath
    root: Path
    kind: str
    submodule: bool = False
    git_commit: str | None = None
    git_url: str | None = None
    projection: str = "mount"
    content: str = "ordinary"
    locator_kind: str | None = None
    locator_path: str | None = None
    expected_type: str | None = None
    index: Path | None = None


EXTERNAL_REFERENCES_FIELD = "whero_external_references"
EXTERNAL_REFERENCES_RE = re.compile(rf"^{EXTERNAL_REFERENCES_FIELD}\s*:")


def _valid_wiki_meta(path: Path) -> bool:
    try:
        validate_wiki_root(path, allow_symlink_meta=is_view_root(path))
    except WheroToolError:
        return False
    return True


def _is_view(path: Path) -> bool:
    try:
        return is_view_root(path)
    except WheroToolError:
        return False


def _declares_external_references(index: Path) -> bool:
    try:
        with index.open(encoding="utf-8") as stream:
            if stream.readline().strip() != "---":
                return False
            for line_number, line in enumerate(stream, start=2):
                if line_number > 256 or line.strip() == "---":
                    return False
                if EXTERNAL_REFERENCES_RE.match(line):
                    return True
    except (OSError, UnicodeError):
        return False
    return False


def _locator_text(locator: dict[str, Any], key: str) -> str | None:
    value = locator.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def discover_declared_references(
    root: Path,
    *,
    excluded_roots: set[PurePosixPath] | None = None,
) -> tuple[list[WikiMount], list[str]]:
    root = root.resolve(strict=False)
    excluded_roots = excluded_roots or set()
    references: list[WikiMount] = []
    problems: list[str] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(root).parts)
        dirnames[:] = [
            name
            for name in dirnames
            if name != ".git"
            and not any(
                path_is_within(
                    relative_current / name
                    if relative_current.parts
                    else PurePosixPath(name),
                    boundary,
                )
                for boundary in excluded_roots
            )
        ]
        index = current / INDEX_FILENAME
        if INDEX_FILENAME not in filenames or not _declares_external_references(index):
            continue
        try:
            fields = read_frontmatter(index)
        except WheroToolError as exc:
            problems.append(str(exc))
            continue
        if not frontmatter_is_true(fields, "whero_maintenance") or not is_view_required(
            fields
        ):
            problems.append(
                f"{EXTERNAL_REFERENCES_FIELD} requires a maintained, "
                f"View-required index: {index}"
            )
            continue
        raw_references = fields.get(EXTERNAL_REFERENCES_FIELD)
        if not isinstance(raw_references, list):
            problems.append(f"{EXTERNAL_REFERENCES_FIELD} must be a YAML list: {index}")
            continue
        for offset, raw in enumerate(raw_references):
            label = f"{EXTERNAL_REFERENCES_FIELD}[{offset}] in {index}"
            if not isinstance(raw, dict):
                problems.append(f"{label} must be a mapping")
                continue
            unknown = set(raw) - {"path", "projection", "content", "locator"}
            if unknown:
                problems.append(
                    f"{label} contains reserved fields: {', '.join(sorted(unknown))}"
                )
                continue
            if not isinstance(raw.get("path"), str):
                problems.append(f"{label} path must be a string")
                continue
            try:
                declared = parse_relative_path(raw["path"], label=label)
            except WheroToolError as exc:
                problems.append(str(exc))
                continue
            relative = relative_current / declared if relative_current.parts else declared
            projection = raw.get("projection")
            content = raw.get("content")
            locator = raw.get("locator")
            if projection not in ("mount", "view"):
                problems.append(f"{label} projection must be mount or view")
                continue
            if content not in ("ordinary", "whero-wiki", "view"):
                problems.append(
                    f"{label} content must be ordinary, whero-wiki, or view"
                )
                continue
            if projection == "view" and content == "ordinary":
                problems.append(f"{label} cannot project ordinary content as a View")
                continue
            if not isinstance(locator, dict):
                problems.append(f"{label} locator must be a mapping")
                continue
            locator_kind = locator.get("kind")
            if locator_kind not in ("filesystem", "git", "git-submodule"):
                problems.append(
                    f"{label} locator kind must be filesystem, git, or git-submodule"
                )
                continue
            allowed_locator_fields = {
                "filesystem": {"kind", "path", "type"},
                "git": {"kind", "url", "revision"},
                "git-submodule": {"kind"},
            }[locator_kind]
            unknown_locator = set(locator) - allowed_locator_fields
            if unknown_locator:
                problems.append(
                    f"{label} locator contains reserved fields: "
                    f"{', '.join(sorted(unknown_locator))}"
                )
                continue
            locator_path = _locator_text(locator, "path")
            expected_type = _locator_text(locator, "type")
            git_url = sanitize_remote_url(_locator_text(locator, "url") or "")
            git_commit = _locator_text(locator, "revision")
            if locator_kind == "filesystem":
                if locator_path is None:
                    problems.append(f"{label} filesystem locator requires path")
                    continue
                if expected_type not in ("file", "directory"):
                    problems.append(
                        f"{label} filesystem locator type must be file or directory"
                    )
                    continue
            if locator_kind == "git" and git_url is None:
                problems.append(f"{label} git locator requires a valid URL")
                continue
            if locator_kind == "git" and git_commit is not None and not re.fullmatch(
                r"[0-9a-fA-F]{40}", git_commit
            ):
                problems.append(f"{label} revision must be a full Git commit ID")
                continue
            references.append(
                WikiMount(
                    relative,
                    path_from_root(root, relative),
                    "declared-view" if projection == "view" else "declared-mount",
                    locator_kind == "git-submodule",
                    git_commit,
                    git_url,
                    projection,
                    content,
                    locator_kind,
                    locator_path,
                    expected_type,
                    index,
                )
            )
    return references, problems


def git_root(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve(strict=False)


def parse_gitmodules(repository_root: Path) -> dict[PurePosixPath, str | None]:
    gitmodules = repository_root / ".gitmodules"
    if not gitmodules.is_file():
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(gitmodules, encoding="utf-8")
    except (configparser.Error, OSError, UnicodeError):
        return {}
    mounts: dict[PurePosixPath, str | None] = {}
    for section in parser.sections():
        if not section.startswith('submodule "'):
            continue
        raw_path = parser.get(section, "path", fallback="").strip()
        if not raw_path:
            continue
        path = PurePosixPath(raw_path)
        if path.is_absolute() or ".." in path.parts:
            continue
        mounts[path] = parser.get(section, "url", fallback=None)
    return mounts


def _gitlink_commit(repository_root: Path, path: PurePosixPath) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--stage", "--", path.as_posix()],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        metadata = line.split("\t", 1)[0].split()
        if len(metadata) >= 2 and metadata[0] == "160000":
            return metadata[1]
    return None


def _discover_mounts_raw(root: Path) -> list[WikiMount]:
    root = root.resolve(strict=False)
    repository_root = git_root(root)
    submodules: dict[PurePosixPath, tuple[str | None, str | None]] = {}
    if repository_root and is_within(root, repository_root):
        root_relative = root.relative_to(repository_root)
        for repository_path, url in parse_gitmodules(repository_root).items():
            try:
                relative = repository_path.relative_to(PurePosixPath(*root_relative.parts))
            except ValueError:
                continue
            if not relative.parts:
                continue
            submodules[relative] = (
                _gitlink_commit(repository_root, repository_path),
                url,
            )

    mounts: list[WikiMount] = []
    for directory, dirnames, _ in os.walk(root, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(root).parts)
        retained: list[str] = []
        for name in dirnames:
            child = current / name
            relative = relative_current / name if relative_current.parts else PurePosixPath(name)
            submodule = relative in submodules
            wiki = _valid_wiki_meta(child)
            view = wiki and _is_view(child)
            if submodule or wiki:
                commit, url = submodules.get(relative, (None, None))
                kind = "view" if view else "whero-wiki" if wiki else "submodule"
                content = "view" if view else "whero-wiki" if wiki else "ordinary"
                mounts.append(
                    WikiMount(
                        relative,
                        child,
                        kind,
                        submodule,
                        commit,
                        sanitize_remote_url(url or ""),
                        "mount",
                        content,
                        "git-submodule" if submodule else None,
                    )
                )
                continue
            if name != ".git":
                retained.append(name)
        dirnames[:] = retained
    return sorted(mounts, key=lambda mount: mount.path.as_posix())


def discover_boundaries(
    root: Path,
) -> tuple[list[WikiMount], list[PreservedPath], list[str]]:
    raw_mounts = _discover_mounts_raw(root)
    declared, problems = discover_declared_references(
        root,
        excluded_roots={mount.path for mount in raw_mounts},
    )
    by_path: dict[PurePosixPath, WikiMount] = {mount.path: mount for mount in raw_mounts}
    for reference in declared:
        existing = by_path.get(reference.path)
        if existing is not None:
            if existing.index is not None:
                problems.append(
                    f"external reference {reference.path} is declared more than once"
                )
                continue
            reference = WikiMount(
                reference.path,
                reference.root,
                reference.kind,
                reference.submodule or existing.submodule,
                reference.git_commit or existing.git_commit,
                reference.git_url or existing.git_url,
                reference.projection,
                reference.content,
                reference.locator_kind or existing.locator_kind,
                reference.locator_path,
                reference.expected_type,
                reference.index,
            )
        by_path[reference.path] = reference
    merged = sorted(by_path.values(), key=lambda mount: mount.path.as_posix())
    collapsed: list[WikiMount] = []
    for mount in merged:
        parent = mount_for_path(mount.path, collapsed)
        if parent is not None:
            if mount.index is not None and parent.index is not None:
                problems.append(
                    f"external reference {mount.path} overlaps ancestor {parent.path}"
                )
            continue
        collapsed.append(mount)
    preserved, preserved_problems = discover_preserved_paths(
        root,
        excluded_roots={mount.path for mount in collapsed},
    )
    problems.extend(preserved_problems)
    mounts = [
        mount
        for mount in collapsed
        if not any(path_is_within(mount.path, entry.path) for entry in preserved)
    ]
    return mounts, preserved, problems


def discover_mounts(root: Path) -> list[WikiMount]:
    mounts, _, _ = discover_boundaries(root)
    return mounts


def require_owned_write_path(root: Path, path: Path) -> None:
    """Reject writes that enter an outer Wiki ownership boundary."""
    root = root.resolve(strict=True)
    logical = Path(os.path.abspath(path))
    try:
        relative = PurePosixPath(*logical.relative_to(root).parts)
    except ValueError as exc:
        raise WheroToolError(f"write path is outside the Wiki root: {path}") from exc
    resolved_parent = logical.parent.resolve(strict=False)
    if not is_within(resolved_parent, root):
        raise WheroToolError(f"write path resolves outside the Wiki root: {path}")

    mounts, preserved, problems = discover_boundaries(root)
    if problems:
        raise WheroToolError(problems[0])
    mount = mount_for_path(relative, mounts)
    if mount is not None:
        raise WheroToolError(
            f"write path enters mounted ownership boundary {mount.path}: {relative}"
        )
    preserved_entry = next(
        (entry for entry in preserved if path_is_within(relative, entry.path)),
        None,
    )
    if preserved_entry is not None:
        raise WheroToolError(
            f"write path enters preserved boundary {preserved_entry.path}: {relative}"
        )


def mount_for_path(
    relative: PurePosixPath,
    mounts: list[WikiMount],
) -> WikiMount | None:
    matches = [
        mount
        for mount in mounts
        if relative.parts[: len(mount.path.parts)] == mount.path.parts
    ]
    return max(matches, key=lambda mount: len(mount.path.parts), default=None)


def walk_owned_files(root: Path) -> Iterator[Path]:
    """Yield files owned by this Wiki without entering declared boundaries."""
    mounts, preserved, _ = discover_boundaries(root)
    excluded_paths = {mount.path for mount in mounts} | {
        entry.path for entry in preserved
    }
    view_context = _is_view(root)
    disclosed_directory_links: list[Path] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(root).parts)
        for name in dirnames:
            child = current / name
            relative = (
                relative_current / name
                if relative_current.parts
                else PurePosixPath(name)
            )
            if child.is_symlink() and relative not in excluded_paths and view_context:
                disclosed_directory_links.append(child)
        dirnames[:] = [
            name
            for name in dirnames
            if name != ".git"
            and (
                relative_current / name if relative_current.parts else PurePosixPath(name)
            )
            not in excluded_paths
        ]
        for name in filenames:
            relative = (
                relative_current / name
                if relative_current.parts
                else PurePosixPath(name)
            )
            if not any(path_is_within(relative, boundary) for boundary in excluded_paths):
                yield current / name

    for disclosed_root in disclosed_directory_links:
        for directory, dirnames, filenames in os.walk(
            disclosed_root,
            followlinks=False,
        ):
            current = Path(directory)
            relative_current = PurePosixPath(*current.relative_to(root).parts)
            dirnames[:] = [
                name
                for name in dirnames
                if not (current / name).is_symlink()
                and not _valid_wiki_meta(current / name)
                and not ((current / name) / ".git").exists()
                and not any(
                    path_is_within(
                        relative_current / name
                        if relative_current.parts
                        else PurePosixPath(name),
                        boundary,
                    )
                    for boundary in excluded_paths
                )
            ]
            for name in filenames:
                relative = (
                    relative_current / name
                    if relative_current.parts
                    else PurePosixPath(name)
                )
                if not any(
                    path_is_within(relative, boundary) for boundary in excluded_paths
                ):
                    yield current / name
