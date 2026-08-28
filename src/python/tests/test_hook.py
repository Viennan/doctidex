from __future__ import annotations

import os
import sys
from pathlib import Path

from conftest import CliRunner, git


def _expected_command_path() -> str:
    return str((Path(sys.executable).parent / "doctidex-git").resolve())


def _post_checkout_hook(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "post-checkout"


def _pre_commit_hook(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "pre-commit"


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
