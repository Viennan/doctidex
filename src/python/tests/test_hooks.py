from __future__ import annotations

import os
import sys
from pathlib import Path

from conftest import CliRunner, git, read_json, write_json

from whero.doctidex.model import Installation, InstallationShare
from whero.doctidex.paths import repo_path_to_fs


def _expected_command_path() -> str:
    return str((Path(sys.executable).parent / "doctidex-git").resolve())


def _post_checkout_hook(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "post-checkout"


def _pre_commit_hook(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "pre-commit"


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
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
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


def test_hook_install_writes_executable_supported_hooks(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "hook", "install")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    for hook in (_post_checkout_hook(git_root), _pre_commit_hook(git_root)):
        assert hook.is_file()
        assert os.access(hook, os.X_OK)
        assert _expected_command_path() in hook.read_text()


def test_hook_install_is_idempotent(git_root: Path, cli: CliRunner) -> None:
    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0
    first_post_checkout = _post_checkout_hook(git_root).read_text()
    first_pre_commit = _pre_commit_hook(git_root).read_text()

    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0

    assert _post_checkout_hook(git_root).read_text() == first_post_checkout
    assert _pre_commit_hook(git_root).read_text() == first_pre_commit


def test_hook_install_injects_into_existing_hook_script(git_root: Path, cli: CliRunner) -> None:
    hook = _pre_commit_hook(git_root)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\n# existing\nexisting-command \"$@\"\n")

    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0

    text = hook.read_text()
    assert "# doctidex-git begin pre-commit" in text
    assert "# doctidex-git end pre-commit" in text
    assert 'existing-command "$@"' in text
    assert text.index(_expected_command_path()) < text.index('existing-command "$@"')


def test_hook_install_replaces_old_doctidex_block(git_root: Path, cli: CliRunner) -> None:
    hook = _pre_commit_hook(git_root)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        "#!/bin/sh\n"
        "# doctidex-git begin pre-commit\n"
        "OLD COMMAND\n"
        "# doctidex-git end pre-commit\n"
        "existing-command\n"
    )

    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0

    text = hook.read_text()
    assert "OLD COMMAND" not in text
    assert text.count("# doctidex-git begin pre-commit") == 1
    assert text.count("# doctidex-git end pre-commit") == 1
    assert "existing-command" in text


def test_hook_post_checkout_has_a_stable_worker(git_root: Path, cli: CliRunner) -> None:
    result = cli.run(
        "--repos-path",
        str(git_root),
        "hook",
        "post-checkout",
        "old-head",
        "new-head",
        "1",
    )

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}


def test_init_installs_hooks_automatically(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    assert _post_checkout_hook(git_root).is_file()
    assert _pre_commit_hook(git_root).is_file()


def test_hook_pre_commit_passes_without_workspace(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "hook", "pre-commit")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}


def test_hook_pre_commit_passes_valid_workspace(initialized_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(initialized_root), "hook", "pre-commit")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}


def test_hook_pre_commit_reports_invalid_workspace(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / ".doctidex-git" / "runtime.json").unlink()

    result = cli.run("--repos-path", str(initialized_root), "hook", "pre-commit")

    assert result.code == 2
    assert result.payload["status"] == "error"
    assert result.payload["message"]["code"] == "hook.pre-commit.validation.failed"
    diagnostics = result.payload["message"]["details"]["diagnostics"]
    assert any(item["rule"] == "work-model.valid" for item in diagnostics)


def test_pre_commit_hook_allows_valid_commit(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / "topic.md").write_text("topic\n")
    assert git(initialized_root, "add", "topic.md").returncode == 0

    committed = git(initialized_root, "commit", "--quiet", "-m", "topic")

    assert committed.returncode == 0


def test_pre_commit_hook_blocks_invalid_commit(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / ".doctidex-git" / "runtime.json").unlink()
    (initialized_root / "topic.md").write_text("topic\n")
    assert git(initialized_root, "add", "topic.md").returncode == 0

    committed = git(initialized_root, "commit", "--quiet", "-m", "topic")

    assert committed.returncode != 0


def test_pre_commit_hook_allows_commit_without_workspace(git_root: Path, cli: CliRunner) -> None:
    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0
    (git_root / "topic.md").write_text("topic\n")
    assert git(git_root, "add", "topic.md").returncode == 0

    committed = git(git_root, "commit", "--quiet", "-m", "topic")

    assert committed.returncode == 0


def test_pre_commit_hook_runs_existing_hook_after_doctidex_success(
    git_root: Path, cli: CliRunner
) -> None:
    marker = git_root / "existing-hook-ran"
    hook = _pre_commit_hook(git_root)
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\n: > existing-hook-ran\n")
    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0
    (git_root / "topic.md").write_text("topic\n")
    assert git(git_root, "add", "topic.md").returncode == 0

    committed = git(git_root, "commit", "--quiet", "-m", "topic")

    assert committed.returncode == 0
    assert marker.is_file()


def test_pre_commit_hook_does_not_run_existing_hook_when_doctidex_fails(
    initialized_root: Path, cli: CliRunner
) -> None:
    marker = initialized_root / "existing-hook-ran"
    hook = _pre_commit_hook(initialized_root)
    hook.write_text("#!/bin/sh\n: > existing-hook-ran\n")
    assert cli.run("--repos-path", str(initialized_root), "hook", "install").code == 0
    (initialized_root / ".doctidex-git" / "runtime.json").unlink()
    (initialized_root / "topic.md").write_text("topic\n")
    assert git(initialized_root, "add", "topic.md").returncode == 0

    committed = git(initialized_root, "commit", "--quiet", "-m", "topic")

    assert committed.returncode != 0
    assert not marker.exists()


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
    share_path = repo_path_to_fs(git_root, "/.doctidex-git/imports/example/commit/0123456789abcdef")
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
