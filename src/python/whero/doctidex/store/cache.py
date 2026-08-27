"""Recoverable single-file state for the user-level Git cache."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Self

from whero.doctidex.model import CacheItem, CacheItemStatus, ModelFormatError

from .files import FileLock, StoreFailure, atomic_write_bytes, read_bytes

_MAX_CACHE_READ_RECOVERY_ATTEMPTS = 3


class CacheStore:
    """Manage CacheStore records and their cache repository paths."""

    def __init__(self, cache_path: Path) -> None:
        self.cache_path = cache_path
        self.status_path = cache_path / "status.json"
        self._lock = FileLock(cache_path / ".lock", store="cache")

    def read_only_transaction(self) -> CacheReadOnlyTransaction:
        """Open a locked record snapshot without exposing record replacement."""

        return CacheReadOnlyTransaction(self)

    def write_transaction(self) -> CacheWriteTransaction:
        """Open a locked transaction whose record replacements publish immediately."""

        return CacheWriteTransaction(self)

    def _read_records(self) -> tuple[CacheItem, ...]:
        if not self.status_path.exists():
            return ()
        document = _decode_status(read_bytes(self.status_path, store="cache", phase="read"))
        records = tuple(CacheItem.from_json(item, artifact="status.json") for item in document["records"])
        _validate_records(records)
        return records

    def _publish_records(self, records: tuple[CacheItem, ...], *, phase: str) -> None:
        _validate_records(records)
        atomic_write_bytes(
            self.status_path,
            _encode_status(records),
            store="cache",
            phase=phase,
        )

    def _path_for_record(self, record: CacheItem) -> Path:
        relative = Path(record.path)
        if relative.is_absolute() or relative == Path(".") or ".." in relative.parts or not record.path:
            raise ModelFormatError("status.json", "cache item paths relative to cache-path")
        return self.cache_path / relative


class CacheTransaction:
    """Base locked CacheStore transaction with startup recovery."""

    def __init__(self, store: CacheStore) -> None:
        self.store = store
        self.records: tuple[CacheItem, ...] = ()

    def __enter__(self) -> Self:
        self.store._lock.acquire_exclusive()
        try:
            self.records = self.store._read_records()
            self._recover_preparing()
        except Exception:
            self.store._lock.release()
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            pass
        finally:
            self.store._lock.release()
        return False

    def find(self, git_url: str) -> CacheItem | None:
        """Return the CacheItem for ``git_url``, if one is recorded."""

        return next((record for record in self.records if record.git_url == git_url), None)

    def _has_preparing(self) -> bool:
        """Return whether any current record is still preparing."""

        return any(record.status == CacheItemStatus.PREPARING for record in self.records)

    def _recover_preparing(self) -> None:
        preparing = tuple(record for record in self.records if record.status == CacheItemStatus.PREPARING)
        if not preparing:
            return
        for record in preparing:
            target = self.store._path_for_record(record)
            try:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                elif target.exists():
                    shutil.rmtree(target)
            except OSError as exc:
                raise StoreFailure(store="cache", phase="recovery", state_path=target) from exc
        self.records = tuple(record for record in self.records if record.status != CacheItemStatus.PREPARING)
        self.store._publish_records(self.records, phase="recovery")


class CacheReadOnlyTransaction(CacheTransaction):
    """A CacheStore transaction exposing only record queries."""

    def __enter__(self) -> Self:
        """Enter with a shared lock, recovering interrupted preparing records when needed."""

        for _attempt in range(_MAX_CACHE_READ_RECOVERY_ATTEMPTS):
            self.store._lock.acquire_shared()
            try:
                self.records = self.store._read_records()
                if not self._has_preparing():
                    return self
            except Exception:
                self.store._lock.release()
                raise
            self.store._lock.release()
            self.store._lock.acquire_exclusive()
            try:
                self.records = self.store._read_records()
                self._recover_preparing()
            finally:
                self.store._lock.release()
        raise StoreFailure(
            store="cache",
            phase="recovery",
            state_path=self.store.status_path,
            details={"attempts": _MAX_CACHE_READ_RECOVERY_ATTEMPTS},
        )


class CacheWriteTransaction(CacheTransaction):
    """A CacheStore transaction with immediate record publication."""

    def replace_records(self, records: tuple[CacheItem, ...] | list[CacheItem]) -> None:
        """Publish the complete record set and update the in-memory copy."""

        candidate = tuple(records)
        self.store._publish_records(candidate, phase="commit")
        self.records = candidate


def _decode_status(content: bytes) -> dict[str, object]:
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelFormatError("status.json", "an object with a records array") from exc
    if not isinstance(document, dict) or not isinstance(document.get("records"), list):
        raise ModelFormatError("status.json", "an object with a records array")
    return document


def _validate_records(records: tuple[CacheItem, ...]) -> None:
    urls = [record.git_url for record in records]
    if len(urls) != len(set(urls)):
        raise ModelFormatError("status.json", "records with unique git-url values")
    for record in records:
        if not record.git_url:
            raise ModelFormatError("status.json", "cache records with non-empty git-url values")
        if not record.path:
            raise ModelFormatError("status.json", "cache records with non-empty relative paths")


def _encode_status(records: tuple[CacheItem, ...]) -> bytes:
    document = {"records": [record.to_json() for record in records]}
    return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode()
