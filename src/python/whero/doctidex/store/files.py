"""Small POSIX file-system primitives used by the durable state stores."""

from __future__ import annotations

import fcntl
import hashlib
import os
import tempfile
from pathlib import Path


class StoreFailure(RuntimeError):
    """A store operation failed without exposing an underlying system error to callers."""

    def __init__(
        self,
        *,
        store: str,
        phase: str,
        state_path: Path,
        transaction_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(f"{store} store operation failed during {phase}")
        self.store = store
        self.phase = phase
        self.state_path = state_path
        self.transaction_id = transaction_id
        self.details = details or {}


class FileLock:
    """An advisory file lock with shared and exclusive acquisition modes."""

    def __init__(self, path: Path, *, store: str) -> None:
        self.path = path
        self.store = store
        self._handle: object | None = None

    def acquire_shared(self) -> None:
        """Take a shared advisory lock, creating the lock file as needed."""

        self._acquire(fcntl.LOCK_SH)

    def acquire_exclusive(self) -> None:
        """Take the exclusive advisory lock, creating the lock file as needed."""

        self._acquire(fcntl.LOCK_EX)

    def _acquire(self, operation: int) -> None:
        handle = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = self.path.open("a+b")
            fcntl.flock(handle.fileno(), operation)
        except OSError as exc:
            if handle is not None:
                handle.close()
            raise StoreFailure(store=self.store, phase="lock", state_path=self.path) from exc
        self._handle = handle

    def release(self) -> None:
        """Release the held advisory lock, if any."""

        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        except OSError as exc:
            raise StoreFailure(store=self.store, phase="unlock", state_path=self.path) from exc


def file_sha256(path: Path, *, store: str = "runtime") -> str | None:
    """Return a file digest, with ``None`` representing an absent file."""

    try:
        if not path.exists():
            return None
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise StoreFailure(store=store, phase="hash", state_path=path) from exc
    return digest.hexdigest()


def read_bytes(path: Path, *, store: str, phase: str) -> bytes:
    """Read one store file and translate an OS error into ``StoreFailure``."""

    try:
        return path.read_bytes()
    except OSError as exc:
        raise StoreFailure(store=store, phase=phase, state_path=path) from exc


def atomic_write_bytes(path: Path, content: bytes, *, store: str, phase: str) -> None:
    """Durably publish one file through a same-directory temporary file."""

    descriptor: int | None = None
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as output:
            descriptor = None
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent, store=store, phase=phase)
    except OSError as exc:
        raise StoreFailure(store=store, phase=phase, state_path=path) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def fsync_directory(path: Path, *, store: str, phase: str) -> None:
    """Persist directory metadata after a rename, creation, or deletion."""

    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        raise StoreFailure(store=store, phase=phase, state_path=path) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
