from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import read_json, write_residual_journal


def _cli_executable() -> Path:
    return Path(sys.executable).with_name("doctidex-git")


def _environment(cache_home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["DOCTIDEX-GIT-HOME"] = str(cache_home)
    return environment


def _start_cli(cache_home: Path, *arguments: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [str(_cli_executable()), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_environment(cache_home),
    )


def _run_cli(cache_home: Path, *arguments: str) -> tuple[int, object]:
    completed = subprocess.run(
        [str(_cli_executable()), *arguments],
        capture_output=True,
        text=True,
        env=_environment(cache_home),
        timeout=30,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload


def test_concurrent_read_only_cli_processes_complete(
    initialized_root: Path,
    cache_home: Path,
) -> None:
    first = _start_cli(cache_home, "--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")
    second = _start_cli(cache_home, "--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    first_stdout, first_stderr = first.communicate(timeout=30)
    second_stdout, second_stderr = second.communicate(timeout=30)

    assert first.returncode == 0, first_stderr
    assert second.returncode == 0, second_stderr
    assert json.loads(first_stdout)["status"] == "ok"
    assert json.loads(second_stdout)["status"] == "ok"


def test_concurrent_writer_and_reader_complete_without_command_lock(
    initialized_root: Path,
    cache_home: Path,
) -> None:
    writer = _start_cli(cache_home, "--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/one")
    reader = _start_cli(cache_home, "--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    writer_stdout, writer_stderr = writer.communicate(timeout=30)
    reader_stdout, reader_stderr = reader.communicate(timeout=30)

    assert writer.returncode == 0, writer_stderr
    assert reader.returncode == 0, reader_stderr
    assert json.loads(writer_stdout)["status"] == "ok"
    assert json.loads(reader_stdout)["status"] == "ok"
    assert read_json(initialized_root / ".doctidex-git" / "boundary-set.json") == [
        {"type": "custom", "path": "/one"}
    ]
    assert not (initialized_root / ".doctidex-git" / ".command.lock").exists()


def test_cli_process_repairs_residual_journal_without_command_lock(
    initialized_root: Path,
    cache_home: Path,
) -> None:
    directory = write_residual_journal(initialized_root, state="prepared")

    code, payload = _run_cli(
        cache_home,
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        "/docs",
    )

    assert code == 0
    assert payload == {
        "status": "ok",
        "message": {},
        "results": [{"has-boundary": False, "path": "/docs"}],
    }
    assert not directory.exists()
    assert not (initialized_root / ".doctidex-git" / ".command.lock").exists()
