from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from whero.doctidex.errors import CommandFailure
from whero.doctidex.git_cache import GitCache, _cache_repository_path
from whero.doctidex.model import CacheItem, CacheItemStatus


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


def test_git_cache_with_repository_keeps_the_selected_transaction_open(tmp_path: Path, monkeypatch) -> None:
    source = _source_repository(tmp_path)
    cache = GitCache(tmp_path / "cache")
    active: list[str] = []
    events: list[str] = []
    _record_transactions(cache, active, events, monkeypatch)

    first = cache.with_repository(str(source), lambda repository: (active[:], repository))
    assert first[0] == ["write"]
    assert events == ["read-only:open", "read-only:close", "write:open", "write:close"]

    events.clear()
    second = cache.with_repository(str(source), lambda repository: (active[:], repository))
    assert second == (["read-only"], first[1])
    assert events == ["read-only:open", "read-only:close"]


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
    (source / "readme.md").write_text("source\n")
    subprocess.run(["git", "-C", str(source), "add", "readme.md"], check=True)
    subprocess.run(["git", "-C", str(source), "commit", "--quiet", "-m", "initial"], check=True)
    return source


def _record_transactions(cache: GitCache, active: list[str], events: list[str], monkeypatch) -> None:
    for name, kind in (("read_only_transaction", "read-only"), ("write_transaction", "write")):
        original = getattr(cache, name)

        def transaction(*, original=original, kind=kind):
            class RecordedTransaction:
                def __enter__(self):
                    events.append(f"{kind}:open")
                    self.value = original().__enter__()
                    active.append(kind)
                    return self.value

                def __exit__(self, exc_type, exc, traceback):
                    active.pop()
                    result = self.value.__exit__(exc_type, exc, traceback)
                    events.append(f"{kind}:close")
                    return result

            return RecordedTransaction()

        monkeypatch.setattr(cache, name, transaction)
