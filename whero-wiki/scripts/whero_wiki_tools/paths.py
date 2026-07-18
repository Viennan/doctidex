"""Safe source-relative path handling shared by Whero tools."""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

from .errors import WheroToolError


def parse_relative_path(
    raw: str,
    *,
    label: str = "path",
    single_component: bool = False,
) -> PurePosixPath:
    value = raw.strip()
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise WheroToolError(
            f"{label} must be a non-empty POSIX path relative to the Wiki root: {raw!r}"
        )
    if single_component and len(path.parts) != 1:
        raise WheroToolError(f"{label} must be one direct child directory name: {raw!r}")
    return path


def path_from_root(root: Path, relative: PurePosixPath) -> Path:
    return root.joinpath(*relative.parts)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_within(
    root: Path,
    relative: PurePosixPath,
    *,
    must_exist: bool = True,
) -> Path:
    candidate = path_from_root(root, relative)
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise WheroToolError(f"cannot resolve Wiki path {relative}: {exc}") from exc
    if not is_within(resolved, root):
        raise WheroToolError(f"Wiki path resolves outside the Wiki root: {relative}")
    return resolved


def wiki_relative(path: Path, root: Path) -> PurePosixPath:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise WheroToolError(f"path is outside the Wiki root: {path}") from exc
    return PurePosixPath(*relative.parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise WheroToolError(f"cannot hash source file {path}: {exc}") from exc
    return digest.hexdigest()

