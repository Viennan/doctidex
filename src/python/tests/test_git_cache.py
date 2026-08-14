from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from whero.doctidex.errors import CommandFailure
from whero.doctidex.git_cache import GitCache, _cache_repository_path
from whero.doctidex.model import CacheItem, CacheItemStatus
from whero.doctidex.repository import ensure_commit_available


def test_git_cache_write_load_publishes_and_reuses_one_repository(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    cache = GitCache(tmp_path / "cache")

    with cache.write_transaction() as transaction:
        first = transaction.load(str(source))
        second = transaction.load(str(source))
        assert first == second
        status = json.loads(cache.store.status_path.read_text())
        assert status["records"] == [
            {
                "status": "published",
                "git-url": str(source),
                "path": f"local/{source.as_posix().lstrip('/')}",
            }
        ]
        assert first == cache.cache_path / status["records"][0]["path"]

    with cache.read_only_transaction() as transaction:
        assert transaction.find(str(source)) == first
        assert transaction.repository(str(source)) == first
        assert not hasattr(transaction, "load")


def test_git_cache_load_failure_leaves_preparing_record_for_next_transaction(tmp_path: Path) -> None:
    cache = GitCache(tmp_path / "cache")
    missing_source = tmp_path / "missing-source"

    with pytest.raises(CommandFailure, match="could not provide"):
        with cache.write_transaction() as transaction:
            transaction.load(str(missing_source))

    records = json.loads(cache.store.status_path.read_text())["records"]
    assert records[0]["status"] == "preparing"
    repository = cache.cache_path / records[0]["path"]

    with cache.read_only_transaction() as transaction:
        assert transaction.find(str(missing_source)) is None

    assert not repository.exists()
    assert json.loads(cache.store.status_path.read_text()) == {"records": []}


def test_git_cache_write_load_replaces_an_unusable_published_repository(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    cache = GitCache(tmp_path / "cache")
    record = CacheItem(
        status=CacheItemStatus.PUBLISHED,
        git_url=str(source),
        path="repositories/source.git",
    )
    stale = cache.cache_path / record.path
    stale.mkdir(parents=True)
    (stale / "not-a-repository").write_text("stale\n")
    cache.store._publish_records((record,), phase="test")

    with cache.write_transaction() as transaction:
        repository = transaction.load(str(source))

    assert repository.is_dir()
    assert subprocess.run(
        ["git", "-C", str(repository), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == str(source)


def test_ensure_commit_available_fetches_only_a_missing_commit(tmp_path: Path) -> None:
    source = _source_repository(tmp_path)
    cache = GitCache(tmp_path / "cache")
    with cache.write_transaction() as transaction:
        repository = transaction.load(str(source))

    commit = _commit(source, "later.md", "later\n")
    ensure_commit_available(repository, str(source), commit)
    source.rename(tmp_path / "source-unavailable")

    ensure_commit_available(repository, str(source), commit)
    assert subprocess.run(
        ["git", "-C", str(repository), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=True,
    ).returncode == 0


@pytest.mark.parametrize(
    ("git_url", "path"),
    [
        ("https://github.com/Viennan/doctidex.git", "github.com/Viennan/doctidex"),
        ("git@github.com:Viennan/doctidex.git", "github.com/Viennan/doctidex"),
        ("/workspace/sources/doctidex.git", "local/workspace/sources/doctidex"),
    ],
)
def test_git_cache_repository_path_uses_git_url_domain_and_hierarchy(git_url: str, path: str) -> None:
    assert _cache_repository_path(git_url) == path


def _source_repository(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", "--initial-branch", "main", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.email", "tests@example.test"], check=True)
    subprocess.run(["git", "-C", str(source), "config", "user.name", "Tests"], check=True)
    _commit(source, "readme.md", "source\n")
    return source


def _commit(repository: Path, name: str, content: str) -> str:
    (repository / name).write_text(content)
    subprocess.run(["git", "-C", str(repository), "add", name], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "--quiet", "-m", name], check=True)
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
