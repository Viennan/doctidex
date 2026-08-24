"""Managed repository symlink scanning."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.model import Installation, Ref
from whero.doctidex.paths import fs_path_to_repo_path, normalize_repo_path, repo_path_to_fs
from whero.doctidex.store.model_view import RuntimeModelView


@dataclass(frozen=True, slots=True)
class ManagedSymlink:
    """A repository symlink whose resolved target lies in an Installation."""

    path: str
    target_path: str
    installation: Installation
    ref: Ref | None


def scan_managed_symlinks(
    git_root: Path,
    model: RuntimeModelView,
    *,
    scope: str = "/",
) -> tuple[ManagedSymlink, ...]:
    """Return repository symlinks that resolve into an Installation under ``scope``."""

    scope = normalize_repo_path(scope, parameter="scope")
    root = repo_path_to_fs(git_root, scope)
    installation_roots = tuple((repo_path_to_fs(git_root, item.install_path), item) for item in model.installations)
    boundaries = {point.path for point in model.boundary_points}
    result: list[ManagedSymlink] = []
    for directory, child_directories, files in os.walk(root, followlinks=False):
        current = fs_path_to_repo_path(git_root, Path(directory))
        retained_directories: list[str] = []
        for name in child_directories:
            candidate = Path(directory) / name
            candidate_repo = _join_repo_path(current, name)
            if name == ".doctidex-git" or candidate_repo in boundaries:
                continue
            if candidate.is_symlink():
                _append_managed_symlink(result, candidate, candidate_repo, installation_roots, model, git_root)
                continue
            retained_directories.append(name)
        child_directories[:] = retained_directories
        for name in files:
            candidate = Path(directory) / name
            if candidate.is_symlink():
                _append_managed_symlink(
                    result, candidate, _join_repo_path(current, name), installation_roots, model, git_root
                )
    return tuple(result)


def _append_managed_symlink(
    result: list[ManagedSymlink],
    candidate: Path,
    candidate_repo: str,
    installation_roots: tuple[tuple[Path, Installation], ...],
    model: RuntimeModelView,
    git_root: Path,
) -> None:
    try:
        resolved = candidate.resolve(strict=False)
    except OSError:
        return
    for install_root, installation in installation_roots:
        try:
            resolved.relative_to(install_root)
        except ValueError:
            continue
        target_repo = fs_path_to_repo_path(git_root, resolved)
        result.append(
            ManagedSymlink(
                path=candidate_repo,
                target_path=target_repo,
                installation=installation,
                ref=model.ref(candidate_repo),
            )
        )
        return


def _join_repo_path(parent: str, child: str) -> str:
    return f"{parent.rstrip('/')}/{child}" if parent != "/" else f"/{child}"


__all__ = ["ManagedSymlink", "scan_managed_symlinks"]
