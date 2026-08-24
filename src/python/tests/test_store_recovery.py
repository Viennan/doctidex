from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, read_json, write_json, write_residual_journal

import whero.doctidex.coordination as coordination


def test_cache_miss_and_hit_reuse_one_published_repository(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    first = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    second = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )

    assert first.code == 0
    assert second.payload == first.payload
    status = read_json(cache_home / "cache" / "status.json")
    assert len(status["records"]) == 1
    assert status["records"][0]["status"] == "published"


def test_interrupted_preparing_cache_record_is_cleaned_before_install(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    status_path = cache_home / "cache" / "status.json"
    write_json(
        status_path,
        {
            "records": [
                {
                    "status": "preparing",
                    "git-url": str(source_repository),
                    "path": "repositories/preparing.git",
                }
            ]
        },
    )

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )

    assert result.code == 0
    records = read_json(status_path)["records"]
    assert [record["status"] for record in records] == ["published"]


def test_residual_journal_is_recovered_before_a_normal_command(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    directory = write_residual_journal(initialized_root, state="prepared")

    result = cli.run("--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    assert result.code == 0
    assert not directory.exists()


def test_committed_residual_journal_is_cleaned_by_repair(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    directory = write_residual_journal(initialized_root, state="committed")

    result = cli.run("--repos-path", str(initialized_root), "repair")

    assert result.code == 0
    assert not directory.exists()


def test_recovery_retry_exhaustion_reports_a_structured_failure(
    initialized_root: Path,
    cache_home: Path,
    cli: CliRunner,
    monkeypatch,
) -> None:
    directory = write_residual_journal(initialized_root, state="prepared")
    monkeypatch.setattr(coordination, "repair_core", lambda _store, _transaction: None)

    result = cli.run("--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    assert result.code == 2
    assert result.payload["message"]["code"] == "store.transaction.unavailable"
    assert result.payload["message"]["details"]["attempts"] == 3
    assert result.payload["message"]["details"]["transaction-ids"] == ["residual"]
    assert directory.exists()
