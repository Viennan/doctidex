from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pytest

from whero.doctidex.cli.main import main


class CliResult:
    """One CLI invocation's exit status and parsed JSON payload."""

    def __init__(self, code: int, payload: object) -> None:
        self.code = code
        self.payload = payload


class CliRunner:
    """Run the CLI entry point and capture its single machine-readable result."""

    def run(self, *argv: str) -> CliResult:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(list(argv))
        text = output.getvalue()
        payload: object = json.loads(text) if text.strip() else {}
        return CliResult(code, payload)

    def ok(self, *argv: str) -> object:
        result = self.run(*argv)
        assert result.code == 0, result.payload
        return result.payload

    def error(self, *argv: str) -> object:
        result = self.run(*argv)
        assert result.code == 2, result.payload
        return result.payload


def read_json(path: Path) -> object:
    return json.loads(path.read_text())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n")


def write_residual_journal(
    git_root: Path,
    *,
    state: str,
    transaction_id: str = "residual",
) -> Path:
    """Write a durable residual RuntimeStore journal without using product code."""

    workspace = git_root / ".doctidex-git"
    directory = workspace / ".transactions" / transaction_id
    (directory / "stage").mkdir(parents=True, exist_ok=True)
    (directory / "backup").mkdir(parents=True, exist_ok=True)

    target_name = "boundary-set.json"
    target_path = workspace / target_name
    old_content = target_path.read_bytes()
    new_content = json.dumps([{"type": "custom", "path": "/external"}], ensure_ascii=False).encode() + b"\n"
    (directory / "stage" / target_name).write_bytes(new_content)
    (directory / "backup" / target_name).write_bytes(old_content)
    if state == "committed":
        target_path.write_bytes(new_content)
    journal = {
        "version": 1,
        "store": "runtime",
        "transaction-id": transaction_id,
        "state": state,
        "entries": [
            {
                "target": target_name,
                "old-sha256": hashlib.sha256(old_content).hexdigest(),
                "new-sha256": hashlib.sha256(new_content).hexdigest(),
                "stage": f"stage/{target_name}",
                "backup": f"backup/{target_name}",
            }
        ],
    }
    write_json(directory / "journal.json", journal)
    return directory


def git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def git_head(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_remote(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_status(repository: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def git_ignored(repository: Path, repository_internal_path: str) -> bool:
    completed = git(repository, "check-ignore", "--quiet", "--no-index", "--", repository_internal_path.lstrip("/"))
    return completed.returncode == 0


def commit_file(repository: Path, name: str, content: str) -> str:
    (repository / name).write_text(content)
    git(repository, "add", name)
    git(repository, "commit", "--quiet", "-m", name)
    return git_head(repository)


def make_git_repository(path: Path) -> Path:
    """Create a committed, deterministic Git repository at ``path``."""

    _init_git_repository(path)
    return path


def _init_git_repository(path: Path) -> None:
    path.mkdir(parents=True)
    git(path.parent, "init", "--quiet", "--initial-branch", "main", str(path))
    git(path, "config", "user.email", "tests@example.test")
    git(path, "config", "user.name", "Tests")


@pytest.fixture
def git_root(tmp_path: Path) -> Path:
    path = tmp_path / "root"
    _init_git_repository(path)
    return path


@pytest.fixture
def source_repository(tmp_path: Path) -> Path:
    path = tmp_path / "source"
    _init_git_repository(path)
    commit_file(path, "readme.md", "source\n")
    git(path, "tag", "v1")
    return path


@pytest.fixture
def cache_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "cache-home"
    monkeypatch.setenv("DOCTIDEX-GIT-HOME", str(path))
    return path


@pytest.fixture
def cli() -> CliRunner:
    return CliRunner()


@pytest.fixture
def initialized_root(git_root: Path, cli: CliRunner) -> Path:
    result = cli.run("--repos-path", str(git_root), "init")
    assert result.code == 0, result.payload
    return git_root
