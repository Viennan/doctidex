"""Initialization of the repository-local doctidex-git work model."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.model import ModelFormatError, RuntimeState
from whero.doctidex.repository import GitRootUnresolved, resolve_git_root
from whero.doctidex.store.files import StoreFailure, atomic_write_bytes, fsync_directory
from whero.doctidex.store.runtime import RuntimeStore, _encode_state

WORKSPACE_NAME = ".doctidex-git"
WORKSPACE_ARTIFACTS = ("config.toml", "boundary-set.json", "imports.json", "import-refs.json", "runtime.json")
RUNTIME_IGNORE_PATHS = (
    "/.doctidex-git/.lock",
    "/.doctidex-git/.command.lock",
    "/.doctidex-git/runtime.json",
    "/.doctidex-git/.transactions/",
    "/.doctidex-git/imports/",
    "/.doctidex-git/worktrees/",
)


@dataclass(frozen=True, slots=True)
class WorkspaceInitializeFailed(RuntimeError):
    """New workspace artifacts could not all be established."""

    git_root: Path
    unavailable_artifacts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InitResult:
    """The root selected by initialization and whether it was newly created."""

    git_root: Path
    created: bool


def initialize(repos_path: str | None, *, cwd: Path | None = None) -> InitResult:
    """Create a complete workspace, or safely validate an existing one without changing it."""

    git_root = resolve_git_root(repos_path, cwd=cwd)
    workspace = git_root / WORKSPACE_NAME
    if workspace.exists():
        _existing_workspace_violations(git_root)
        return InitResult(git_root=git_root, created=False)

    _create_workspace(git_root)
    try:
        RuntimeStore(git_root).read_state()
    except (ModelFormatError, StoreFailure) as exc:
        raise WorkspaceInitializeFailed(git_root, tuple(WORKSPACE_ARTIFACTS)) from exc
    return InitResult(git_root=git_root, created=True)


def _create_workspace(git_root: Path) -> None:
    workspace = git_root / WORKSPACE_NAME
    workspace_sync_started = False
    try:
        with tempfile.TemporaryDirectory(prefix="doctidex-git-init-") as temporary_directory:
            temporary = Path(temporary_directory) / WORKSPACE_NAME
            temporary.mkdir()
            (temporary / "config.toml").write_bytes(b"")
            for name, content in _encode_state(RuntimeState.empty()).items():
                (temporary / name).write_bytes(content)
            _ensure_runtime_ignores(git_root)
            if workspace.exists():
                raise FileExistsError(workspace)
            workspace_sync_started = True
            shutil.copytree(temporary, workspace)
            fsync_directory(git_root, store="runtime", phase="initialize")
    except (OSError, StoreFailure) as exc:
        if workspace_sync_started and workspace.exists():
            _remove_partial_workspace(workspace)
        raise WorkspaceInitializeFailed(git_root, tuple(WORKSPACE_ARTIFACTS)) from exc


def _remove_partial_workspace(workspace: Path) -> None:
    try:
        if workspace.exists():
            shutil.rmtree(workspace)
    except OSError:
        pass


def _existing_workspace_violations(git_root: Path) -> None:
    # Placeholder: requirement 0002-07 (phase 5) must determine the complete validate workflow and
    # its result/error contract before this existing-workspace branch performs any checks.
    pass


def _ensure_runtime_ignores(git_root: Path) -> None:
    gitignore = git_root / ".gitignore"
    try:
        current = gitignore.read_text() if gitignore.exists() else ""
    except OSError as exc:
        raise StoreFailure(store="runtime", phase="initialize", state_path=gitignore) from exc
    lines = current.splitlines()
    additions = [path for path in RUNTIME_IGNORE_PATHS if path not in lines]
    if not additions:
        return
    content = "\n".join([*lines, *additions]) + "\n"
    atomic_write_bytes(gitignore, content.encode(), store="runtime", phase="initialize")


__all__ = [
    "GitRootUnresolved",
    "InitResult",
    "WorkspaceInitializeFailed",
    "initialize",
]
