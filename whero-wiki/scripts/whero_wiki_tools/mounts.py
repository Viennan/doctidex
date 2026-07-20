"""Discover nested Whero Wikis and Git submodules as ownership boundaries."""

from __future__ import annotations

import configparser
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_flat_frontmatter
from .model import STATUS_FILENAME, WIKI_META_FILENAME
from .paths import is_within
from .preserved import PreservedPath, discover_preserved_paths, path_is_within


@dataclass(frozen=True)
class WikiMount:
    path: PurePosixPath
    root: Path
    kind: str
    submodule: bool = False
    git_commit: str | None = None
    git_url: str | None = None


def _valid_wiki_meta(path: Path) -> bool:
    meta = path / WIKI_META_FILENAME
    if not meta.is_file():
        return False
    try:
        fields = read_flat_frontmatter(meta)
    except ValueError:
        return False
    return all(
        frontmatter_is_true(fields, key)
        for key in ("whero_wiki", "whero_maintenance", "whero_scope_required")
    )


def _is_partial(path: Path) -> bool:
    status = path / STATUS_FILENAME
    if not status.is_file():
        return False
    try:
        return frontmatter_is_true(
            read_flat_frontmatter(status),
            "whero_partial_disclosure",
        )
    except ValueError:
        return False


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
            partial = wiki and _is_partial(child)
            if submodule or wiki:
                commit, url = submodules.get(relative, (None, None))
                kind = "partial-wiki" if partial else "whero-wiki" if wiki else "submodule"
                mounts.append(WikiMount(relative, child, kind, submodule, commit, url))
                continue
            if name != ".git":
                retained.append(name)
        dirnames[:] = retained
    return sorted(mounts, key=lambda mount: mount.path.as_posix())


def discover_boundaries(
    root: Path,
) -> tuple[list[WikiMount], list[PreservedPath], list[str]]:
    raw_mounts = _discover_mounts_raw(root)
    preserved, problems = discover_preserved_paths(
        root,
        excluded_roots={mount.path for mount in raw_mounts},
    )
    mounts = [
        mount
        for mount in raw_mounts
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
    partial = _is_partial(root)
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
            if child.is_symlink() and relative not in excluded_paths and partial:
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
