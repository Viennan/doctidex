from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, git, git_head, read_json, write_json

from whero.doctidex.git_cache import GitCache, _live_worktree_heads
from whero.doctidex.model import CacheItemStatus


def test_write_transaction_exposes_and_replaces_records(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache"
    write_json(
        cache_path / "cache-status.json",
        {
            "records": [
                {
                    "status": "published",
                    "git-url": "https://example.test/repository.git",
                    "path": "data/repositories/repository.git",
                }
            ]
        },
    )

    with GitCache(cache_path).write_transaction() as transaction:
        assert len(transaction.records) == 1
        assert transaction.records[0].status == CacheItemStatus.PUBLISHED
        transaction.replace_records(())

    assert read_json(cache_path / "cache-status.json")["records"] == []


def test_live_worktree_heads_ignore_the_bare_repository(
    tmp_path: Path,
    source_repository: Path,
) -> None:
    cache_repository = tmp_path / "cache.git"
    assert git(tmp_path, "clone", "--bare", str(source_repository), str(cache_repository)).returncode == 0
    commit = git_head(source_repository)
    worktree = tmp_path / "worktree"
    assert git(cache_repository, "worktree", "add", "--detach", str(worktree), commit).returncode == 0

    assert _live_worktree_heads(cache_repository, str(source_repository)) == (commit,)


def test_cache_clean_removes_unused_repository(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    assert installed.code == 0
    install_id = installed.payload["install-id"]
    assert cli.run("--repos-path", str(initialized_root), "import", "remove", "--install-id", install_id).code == 0

    status_path = cache_home / "cache" / "cache-status.json"
    record = read_json(status_path)["records"][0]
    repository = cache_home / "cache" / record["path"]
    assert repository.exists()

    cleaned = cli.run("cache", "clean")

    assert cleaned.code == 0
    assert read_json(status_path)["records"] == []
    assert not repository.exists()


def test_cache_clean_retains_live_worktree_repository(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    assert installed.code == 0

    cleaned = cli.run("cache", "clean")

    assert cleaned.code == 0
    status_path = cache_home / "cache" / "cache-status.json"
    records = read_json(status_path)["records"]
    assert len(records) == 1
    assert (cache_home / "cache" / records[0]["path"]).exists()


def test_cache_clean_reuses_preparing_recovery(cache_home: Path, cli: CliRunner) -> None:
    status_path = cache_home / "cache" / "cache-status.json"
    write_json(
        status_path,
        {
            "records": [
                {
                    "status": "preparing",
                    "git-url": "https://example.test/repository.git",
                    "path": "data/repositories/repository.git",
                }
            ]
        },
    )
    repository = cache_home / "cache" / "data" / "repositories" / "repository.git"
    repository.mkdir(parents=True)

    cleaned = cli.run("cache", "clean")

    assert cleaned.code == 0
    assert read_json(status_path)["records"] == []
    assert not repository.exists()


def test_cache_compact_runs_for_published_repository(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    assert installed.code == 0

    compacted = cli.run("cache", "compact")

    assert compacted.code == 0
    assert compacted.payload["compacted"] == [str(source_repository)]
