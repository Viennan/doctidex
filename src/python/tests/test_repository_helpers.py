from __future__ import annotations

from pathlib import Path

import pytest
from conftest import commit_file, git

from whero.doctidex.repository import branch_has_workspace, branch_name_from_ref, current_branch_name


def test_current_branch_name_returns_short_branch(git_root: Path) -> None:
    assert current_branch_name(git_root) == "main"


def test_current_branch_name_returns_none_for_detached_head(git_root: Path) -> None:
    head = commit_file(git_root, "readme.md", "readme\n")
    assert git(git_root, "checkout", "--detach", head).returncode == 0

    assert current_branch_name(git_root) is None


@pytest.mark.parametrize(
    ("reference", "expected"),
    (
        ("refs/heads/main", "main"),
        ("refs/heads/feature/topic", "feature/topic"),
        ("refs/tags/v1", None),
        ("0123456789abcdef", None),
    ),
)
def test_branch_name_from_ref(reference: str, expected: str | None) -> None:
    assert branch_name_from_ref(reference) == expected


def test_branch_has_workspace_requires_tracked_work_model(git_root: Path) -> None:
    assert branch_has_workspace(git_root, "main") is False

    (git_root / ".doctidex-git").mkdir()
    # An ignored runtime-only file is not enough to make this branch a workspace.
    (git_root / ".doctidex-git" / "runtime.json").write_text("{}\n")
    assert git(git_root, "add", ".doctidex-git").returncode == 0
    assert git(git_root, "commit", "--quiet", "-m", "workspace").returncode == 0

    assert branch_has_workspace(git_root, "main") is False

    (git_root / ".doctidex-git" / "config.toml").write_text("")
    assert git(git_root, "add", ".doctidex-git/config.toml").returncode == 0
    assert git(git_root, "commit", "--quiet", "-m", "workspace config").returncode == 0

    assert branch_has_workspace(git_root, "main") is True


def test_branch_has_workspace_respects_nested_branch_name(git_root: Path) -> None:
    assert git(git_root, "checkout", "-b", "feature/topic").returncode == 0
    (git_root / ".doctidex-git").mkdir()
    (git_root / ".doctidex-git" / "config.toml").write_text("")
    assert git(git_root, "add", ".doctidex-git/config.toml").returncode == 0
    assert git(git_root, "commit", "--quiet", "-m", "workspace").returncode == 0

    assert branch_has_workspace(git_root, "feature/topic") is True
    assert branch_has_workspace(git_root, "main") is False
