from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, read_json, write_json, write_residual_journal

import whero.doctidex.coordination as coordination
from whero.doctidex.model import CacheItem, CacheItemStatus
from whero.doctidex.store.cache import CacheReadOnlyTransaction, CacheStore
from whero.doctidex.store.files import StoreFailure
from whero.doctidex.store.runtime import RuntimeStore


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


def test_cache_read_transaction_cleans_preparing_without_network(
    tmp_path: Path,
) -> None:
    store = CacheStore(tmp_path / "cache")
    status_path = store.status_path
    write_json(
        status_path,
        {
            "records": [
                {
                    "status": "preparing",
                    "git-url": "https://example.test/repository.git",
                    "path": "repositories/preparing.git",
                }
            ]
        },
    )
    target = store.cache_path / "repositories" / "preparing.git"
    target.mkdir(parents=True)

    with store.read_only_transaction() as transaction:
        assert transaction.find("https://example.test/repository.git") is None

    assert read_json(status_path)["records"] == []
    assert not target.exists()


def test_cache_read_transaction_recovery_exhaustion_reports_store_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = CacheStore(tmp_path / "cache")
    status_path = store.status_path
    write_json(
        status_path,
        {
            "records": [
                {
                    "status": "preparing",
                    "git-url": "https://example.test/repository.git",
                    "path": "repositories/preparing.git",
                }
            ]
        },
    )
    preparing = CacheItem(
        status=CacheItemStatus.PREPARING,
        git_url="https://example.test/repository.git",
        path="repositories/preparing.git",
    )

    def keep_preparing(_transaction: CacheReadOnlyTransaction) -> None:
        store._publish_records((preparing,), phase="recovery")

    monkeypatch.setattr(CacheReadOnlyTransaction, "_recover_preparing", keep_preparing)

    with pytest.raises(StoreFailure) as exc_info:
        store.read_only_transaction().__enter__()

    assert exc_info.value.store == "cache"
    assert exc_info.value.phase == "recovery"
    assert exc_info.value.state_path == status_path
    assert exc_info.value.details == {"attempts": 3}


def test_read_diagnostic_transaction_has_no_repair_surface(
    initialized_root: Path,
) -> None:
    store = RuntimeStore(initialized_root)

    with store.read_diagnostic_transaction() as transaction:
        assert transaction.pending_journals == ()
        assert not hasattr(transaction, "reload_state")
        assert not hasattr(transaction, "repair_model_view")
        assert not hasattr(transaction, "replace_refs_for_repair")


def test_repair_transaction_exposes_repair_surface(
    initialized_root: Path,
) -> None:
    store = RuntimeStore(initialized_root)

    with store.repair_transaction() as transaction:
        assert transaction.pending_journals == ()
        assert hasattr(transaction, "reload_state")
        assert hasattr(transaction, "repair_model_view")
        assert hasattr(transaction, "replace_refs_for_repair")
        assert transaction.repair_model_view() is not None


def test_residual_journal_is_recovered_before_a_normal_command(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    directory = write_residual_journal(initialized_root, state="prepared")

    result = cli.run("--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    assert result.code == 0
    assert not directory.exists()


def test_coordinated_command_does_not_create_command_lock(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    result = cli.run("--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/docs")

    assert result.code == 0
    assert not (initialized_root / ".doctidex-git" / ".command.lock").exists()


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
