from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, git, read_json, write_json

from whero.doctidex.model import Installation, InstallationShare
from whero.doctidex.paths import repo_path_to_fs


def _commit_workspace(git_root: Path, cli: CliRunner) -> None:
    assert cli.run("--repos-path", str(git_root), "init").code == 0
    assert git(git_root, "add", ".doctidex-git", ".gitignore").returncode == 0
    assert git(git_root, "commit", "--quiet", "-m", "workspace").returncode == 0


def _branch_workspaces(git_root: Path, cli: CliRunner) -> None:
    _commit_workspace(git_root, cli)
    assert git(git_root, "checkout", "-b", "feature").returncode == 0
    assert git(git_root, "checkout", "main").returncode == 0


def _write_branch_installation(git_root: Path) -> Installation:
    share = InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/0123456789abcdef",
        install_ids=("untracked",),
        branch_refs=("main",),
    )
    installation = Installation(
        tracked=False,
        git_url=share.git_url,
        commit_hash=share.commit_hash,
        install_id="untracked",
        install_path="/.doctidex-git/imports/example/main",
        keys=("repository",),
        branch="main",
        tag="",
    )
    write_json(
        git_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [installation.to_json()],
            "worktrees": [],
            "installation-shares": [share.to_json()],
            "branch-snapshots": {},
        },
    )
    repo_path_to_fs(git_root, share.install_path).mkdir(parents=True)
    return installation


def test_post_checkout_noop_without_workspace(git_root: Path, cli: CliRunner) -> None:
    result = cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/main",
        "refs/heads/feature",
        "1",
    )

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}


def test_post_checkout_saves_clears_and_restores_branch_snapshot(
    git_root: Path,
    cli: CliRunner,
) -> None:
    _branch_workspaces(git_root, cli)
    installation = _write_branch_installation(git_root)

    to_feature = cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/main",
        "refs/heads/feature",
        "1",
    )

    assert to_feature.code == 0
    runtime = read_json(git_root / ".doctidex-git" / "runtime.json")
    assert runtime["imports"] == []
    assert runtime["branch-snapshots"]["main"]["imports"] == [installation.to_json()]
    assert not repo_path_to_fs(git_root, installation.install_path).is_symlink()

    to_main = cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/feature",
        "refs/heads/main",
        "1",
    )

    assert to_main.code == 0
    runtime = read_json(git_root / ".doctidex-git" / "runtime.json")
    assert runtime["imports"] == [installation.to_json()]
    assert repo_path_to_fs(git_root, installation.install_path).is_symlink()


def test_post_checkout_manual_rerun_is_apply_only(
    git_root: Path,
    cli: CliRunner,
) -> None:
    _branch_workspaces(git_root, cli)
    installation = _write_branch_installation(git_root)
    assert cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/main",
        "refs/heads/feature",
        "1",
    ).code == 0
    assert cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/feature",
        "refs/heads/main",
        "1",
    ).code == 0

    rerun = cli.run("--repos-path", str(git_root), "hook", "post-checkout")

    assert rerun.code == 0
    runtime = read_json(git_root / ".doctidex-git" / "runtime.json")
    assert runtime["imports"] == [installation.to_json()]


def test_post_checkout_reports_missing_share_worktree(
    git_root: Path,
    cli: CliRunner,
) -> None:
    _branch_workspaces(git_root, cli)
    _write_branch_installation(git_root)
    share_path = repo_path_to_fs(git_root, "/.doctidex-git/imports/example/0123456789abcdef")
    if share_path.exists():
        share_path.rmdir()

    result = cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "refs/heads/main",
        "refs/heads/feature",
        "1",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "hook.post-checkout.reconcile.failed"
