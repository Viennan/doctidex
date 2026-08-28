from __future__ import annotations

import os
import sys
from pathlib import Path

from conftest import CliRunner


def _expected_command_path() -> str:
    return str((Path(sys.executable).parent / "doctidex-git").resolve())


def _post_checkout_hook(git_root: Path) -> Path:
    return git_root / ".git" / "hooks" / "post-checkout"


def test_hook_install_writes_executable_post_checkout_hook(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "hook", "install")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    hook = _post_checkout_hook(git_root)
    assert hook.is_file()
    assert os.access(hook, os.X_OK)
    assert _expected_command_path() in hook.read_text()


def test_hook_install_is_idempotent(git_root: Path, cli: CliRunner) -> None:
    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0
    first = _post_checkout_hook(git_root).read_text()

    assert cli.run("--repos-path", str(git_root), "hook", "install").code == 0

    assert _post_checkout_hook(git_root).read_text() == first


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
