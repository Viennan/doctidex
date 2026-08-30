"""Transaction-scoped access to cached bare Git repositories."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Self
from urllib.parse import urlsplit

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import CacheItem, CacheItemStatus
from whero.doctidex.store.cache import CacheReadOnlyTransaction, CacheStore, CacheWriteTransaction


class GitCache:
    """Expose cache repositories only through locked GitCache transactions."""

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.store = CacheStore(cache_path)

    @classmethod
    def from_environment(cls) -> GitCache:
        """Build the default cache selected by the documented process environment."""

        home = Path(os.environ.get("DOCTIDEX-GIT-HOME", str(Path.home() / ".doctidex-git")))
        return cls(_configured_cache_path(home))

    def read_only_transaction(self) -> GitCacheReadOnlyTransaction:
        """Open cache access that cannot load a missing bare repository."""

        return GitCacheReadOnlyTransaction(self, self.store.read_only_transaction())

    def write_transaction(self) -> GitCacheWriteTransaction:
        """Open cache access that can load a missing bare repository."""

        return GitCacheWriteTransaction(self, self.store.write_transaction())

    def clean(self) -> tuple[str, ...]:
        """Remove published cache repositories that have no live linked worktree."""

        with self.write_transaction() as transaction:
            unused = [
                record
                for record in transaction.records
                if not _live_worktree_heads(_safe_cache_path(self.cache_path, record.path), record.git_url)
            ]
            if not unused:
                return ()

            surviving = tuple(record for record in transaction.records if record not in unused)
            preparing = tuple(replace(record, status=CacheItemStatus.PREPARING) for record in unused)
            transaction.replace_records((*surviving, *preparing))

            for record in unused:
                _remove_cache_repository(_safe_cache_path(self.cache_path, record.path), record.git_url)

            transaction.replace_records(surviving)
            return tuple(record.git_url for record in unused)

    def compact(self) -> tuple[str, ...]:
        """Run Git maintenance for every published cache repository."""

        compacted: list[str] = []
        with self.write_transaction() as transaction:
            for record in transaction.records:
                repository = _safe_cache_path(self.cache_path, record.path)
                _git_cache_result(repository, record.git_url, "worktree", "prune")
                _git_cache_result(repository, record.git_url, "gc", "--prune=now")
                compacted.append(record.git_url)
        return tuple(compacted)


class GitCacheTransaction:
    """Base wrapper that keeps all Git cache activity inside a CacheStore transaction."""

    def __init__(self, cache: GitCache, transaction: CacheReadOnlyTransaction | CacheWriteTransaction) -> None:
        self.cache = cache
        self._transaction = transaction

    def __enter__(self) -> Self:
        self._transaction.__enter__()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return self._transaction.__exit__(exc_type, exc, traceback)

    def find(self, git_url: str) -> Path | None:
        """Return a published repository when its CacheItem is locally usable."""

        record = self._transaction.find(git_url)
        if record is None or record.status != CacheItemStatus.PUBLISHED:
            return None
        path = _safe_cache_path(self.cache.cache_path, record.path)
        return path if _repository_is_usable(path, git_url) else None

    def repository(self, git_url: str) -> Path:
        """Return a published usable repository or the documented cache error."""

        repository = self.find(git_url)
        if repository is None:
            raise _cache_failure(git_url, operation="find")
        return repository


class GitCacheReadOnlyTransaction(GitCacheTransaction):
    """Git cache queries without load capability."""


class GitCacheWriteTransaction(GitCacheTransaction):
    """Git cache access that can register and load a bare repository."""

    @property
    def records(self) -> tuple[CacheItem, ...]:
        """Return the currently published CacheItem records."""

        return self._write_transaction.records

    def replace_records(self, records: tuple[CacheItem, ...] | list[CacheItem]) -> None:
        """Publish a complete CacheItem record set."""

        self._write_transaction.replace_records(records)

    def load(self, git_url: str) -> Path:
        """Reuse or create the CacheItem/repository for ``git_url``."""

        existing = self._write_transaction.find(git_url)
        if existing is not None and existing.status == CacheItemStatus.PUBLISHED:
            path = _safe_cache_path(self.cache.cache_path, existing.path)
            if _repository_is_usable(path, git_url):
                return path
            records = tuple(record for record in self._write_transaction.records if record.git_url != git_url)
        else:
            records = self._write_transaction.records

        path_value = _cache_repository_path(git_url)
        repository = _safe_cache_path(self.cache.cache_path, path_value)
        preparing = CacheItem(status=CacheItemStatus.PREPARING, git_url=git_url, path=path_value)
        self._write_transaction.replace_records((*records, preparing))
        try:
            if repository.is_symlink() or repository.is_file():
                repository.unlink()
            elif repository.exists():
                shutil.rmtree(repository)
            repository.parent.mkdir(parents=True, exist_ok=True)
            _git_clone_bare(git_url, repository)
        except CommandFailure:
            raise
        except OSError as exc:
            raise _cache_failure(git_url, operation="load") from exc
        self._write_transaction.replace_records((*records, replace(preparing, status=CacheItemStatus.PUBLISHED)))
        return repository

    @property
    def _write_transaction(self) -> CacheWriteTransaction:
        assert isinstance(self._transaction, CacheWriteTransaction)
        return self._transaction


def _live_worktree_heads(repository: Path, git_url: str) -> tuple[str, ...]:
    """Return the HEAD commit of each non-bare linked worktree."""

    _git_cache_result(repository, git_url, "worktree", "prune")
    output = _git_cache_result(repository, git_url, "worktree", "list", "--porcelain")
    return tuple(head for _, head in _parse_worktree_entries(output))


def _parse_worktree_entries(output: str) -> tuple[tuple[str, str], ...]:
    """Parse non-bare linked worktree paths and HEAD hashes from porcelain output."""

    entries: list[tuple[str, str]] = []
    block: list[str] = []

    def append(block: list[str]) -> None:
        worktree: str | None = None
        head: str | None = None
        bare = False
        for line in block:
            if line == "bare":
                bare = True
            elif line.startswith("worktree "):
                worktree = line[len("worktree ") :]
            elif line.startswith("HEAD "):
                head = line[len("HEAD ") :]
        if worktree is not None and not bare and head is not None:
            entries.append((worktree, head))

    for line in output.splitlines():
        if line:
            block.append(line)
            continue
        append(block)
        block = []
    append(block)
    return tuple(entries)


def _git_cache_result(repository: Path, git_url: str, *arguments: str) -> str:
    """Run one Git cache command and return its stdout."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _cache_failure(git_url, operation=arguments[0]) from exc
    return completed.stdout


def _remove_cache_repository(repository: Path, git_url: str) -> None:
    """Remove one cache repository path."""

    try:
        if repository.is_symlink() or repository.is_file():
            repository.unlink()
        elif repository.exists():
            shutil.rmtree(repository)
    except OSError as exc:
        raise _cache_failure(git_url, operation="remove") from exc


def _configured_cache_path(home: Path) -> Path:
    config = home / "config.toml"
    if not config.is_file():
        return home / "cache"
    try:
        import tomllib

        document = tomllib.loads(config.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CommandFailure(
            code="cache.repository.unavailable",
            summary="The doctidex-git cache configuration could not be read.",
            subject={"kind": "cache-item"},
            details={"operation": "read-config", "revision": None},
        ) from exc
    configured = document.get("cache-path", "cache")
    if not isinstance(configured, str) or not configured:
        raise CommandFailure(
            code="cache.repository.unavailable",
            summary="The doctidex-git cache configuration does not contain a usable cache path.",
            subject={"kind": "cache-item"},
            details={"operation": "read-config", "revision": None},
        )
    candidate = Path(configured)
    return candidate if candidate.is_absolute() else home / candidate


def _safe_cache_path(cache_path: Path, relative_path: str) -> Path:
    relative = Path(relative_path)
    if relative.is_absolute() or relative == Path(".") or ".." in relative.parts or not relative_path:
        raise CommandFailure(
            code="cache.repository.unavailable",
            summary="The cached repository record uses an invalid local path.",
            subject={"kind": "cache-item"},
            details={"operation": "read-record", "revision": None},
        )
    return cache_path / relative


def _cache_failure(git_url: str, *, operation: str) -> CommandFailure:
    return CommandFailure(
        code="cache.repository.unavailable",
        summary="The Git repository cache could not provide the requested source.",
        subject={"kind": "cache-item", "git-url": git_url},
        details={"operation": operation, "revision": None},
    )


def _cache_repository_path(git_url: str) -> str:
    domain, repository_path = _repository_location(git_url)
    return "/".join((domain, *repository_path))


def _repository_location(git_url: str) -> tuple[str, tuple[str, ...]]:
    parsed = urlsplit(git_url)
    if parsed.hostname is not None:
        domain = parsed.hostname
        repository_path = parsed.path
    elif parsed.scheme == "file":
        domain = "local"
        repository_path = parsed.path
    elif match := re.fullmatch(r"(?:[^@/:]+@)?(?P<domain>[^/:]+):(?P<path>.+)", git_url):
        domain = match.group("domain")
        repository_path = match.group("path")
    else:
        domain = "local"
        repository_path = git_url

    raw_components = repository_path.strip("/").split("/")
    components = tuple(
        _cache_path_component(
            component.removesuffix(".git") if index == len(raw_components) - 1 else component,
            fallback="repository",
        )
        for index, component in enumerate(raw_components)
        if component
    )
    return _cache_path_component(domain, fallback="local"), components or ("repository",)


def _cache_path_component(value: str, *, fallback: str) -> str:
    component = "".join(
        character if character.isascii() and (character.isalnum() or character in "._-") else "_"
        for character in value
    )
    return component or fallback


def _git_clone_bare(git_url: str, target: Path) -> None:
    try:
        subprocess.run(
            ["git", "clone", "--bare", "--depth=1", git_url, str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _cache_failure(git_url, operation="clone") from exc


def _repository_is_usable(repository: Path, git_url: str) -> bool:
    if not repository.is_dir():
        return False
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return completed.stdout.strip() == git_url
