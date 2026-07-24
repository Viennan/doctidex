from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.errors import DoctidexError

from .runner import git
from .state import file_lock, source_directory


@dataclass(frozen=True, slots=True)
class RevisionSelector:
    kind: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


class SourceRepository:
    def __init__(self, url: str) -> None:
        self.url = url
        self.directory = source_directory(url)
        self.repository = self.directory / "repo.git"
        self.revisions = self.directory / "revisions"
        self.maintenance = self.directory / "maintenance"

    def ensure(self) -> None:
        with file_lock(self.directory / "source.lock"):
            self._ensure_unlocked()

    def _ensure_unlocked(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.repository.is_dir():
            return
        git(["clone", "--bare", self.url, str(self.repository)], operation="mount_prepare")

    def resolve(self, selector: RevisionSelector, *, refresh: bool) -> str:
        with file_lock(self.directory / "source.lock"):
            self._ensure_unlocked()
            operation = "mount_sync" if refresh else "mount_prepare"
            if refresh or not self._can_resolve(selector):
                self._fetch(selector, operation=operation)
            expression = self._expression(selector)
            result = git(
                ["--git-dir", str(self.repository), "rev-parse", "--verify", f"{expression}^{{commit}}"],
                operation=operation,
            )
            commit = result.stdout.strip()
            if len(commit) != 40:
                raise DoctidexError(
                    "The declared Git revision did not resolve to a commit.",
                    operation=operation,
                    actions=["Confirm the declared commit, tag, or branch."],
                    code="git_revision_not_commit",
                )
            return commit

    def revision_view(self, commit: str) -> Path:
        with file_lock(self.directory / "source.lock"):
            self._ensure_unlocked()
            self.revisions.mkdir(parents=True, exist_ok=True)
            view = self.revisions / commit
            if view.is_dir():
                current = git(["-C", str(view), "rev-parse", "HEAD"], operation="mount_prepare", check=False)
                if current.returncode == 0 and current.stdout.strip() == commit:
                    return view
                raise DoctidexError(
                    "The existing revision view is not usable.",
                    operation="mount_prepare",
                    actions=["Retry the operation; if it persists, enable debug diagnostics."],
                    code="revision_view_unavailable",
                )
            git(
                ["--git-dir", str(self.repository), "worktree", "add", "--detach", str(view), commit],
                operation="mount_prepare",
            )
            _make_read_only(view)
            return view

    def open_maintenance(self, commit: str, identifier: str) -> Path:
        with file_lock(self.directory / "source.lock"):
            self._ensure_unlocked()
            self.maintenance.mkdir(parents=True, exist_ok=True)
            target = self.maintenance / identifier
            git(
                ["--git-dir", str(self.repository), "worktree", "add", "--detach", str(target), commit],
                operation="maintenance_open",
            )
            return target

    def remove_maintenance(self, path: Path) -> None:
        with file_lock(self.directory / "source.lock"):
            git(
                ["--git-dir", str(self.repository), "worktree", "remove", str(path)],
                operation="maintenance_close",
            )

    def _can_resolve(self, selector: RevisionSelector) -> bool:
        if not self.repository.is_dir():
            return False
        result = git(
            ["--git-dir", str(self.repository), "rev-parse", "--verify", f"{self._expression(selector)}^{{commit}}"],
            operation="mount_prepare",
            check=False,
        )
        return result.returncode == 0

    def _fetch(self, selector: RevisionSelector, *, operation: str) -> None:
        if selector.kind == "branch":
            refspec = f"+refs/heads/{selector.value}:refs/remotes/origin/{selector.value}"
        elif selector.kind == "tag":
            refspec = f"+refs/tags/{selector.value}:refs/tags/{selector.value}"
        else:
            refspec = selector.value
        git(
            ["--git-dir", str(self.repository), "fetch", "--no-recurse-submodules", "origin", refspec],
            operation=operation,
        )

    @staticmethod
    def _expression(selector: RevisionSelector) -> str:
        if selector.kind == "branch":
            return f"refs/remotes/origin/{selector.value}"
        if selector.kind == "tag":
            return f"refs/tags/{selector.value}"
        return selector.value


def _make_read_only(root: Path) -> None:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        for filename in filenames:
            path = current / filename
            if path.is_symlink() or path.name == ".git":
                continue
            mode = path.stat().st_mode
            path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        for dirname in dirnames:
            path = current / dirname
            if path.is_symlink():
                continue
            mode = path.stat().st_mode
            path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
