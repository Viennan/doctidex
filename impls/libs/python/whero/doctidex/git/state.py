from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def state_home() -> Path:
    override = os.environ.get("WHERO_DOCTIDEX_STATE_DIR")
    if override:
        return Path(override).expanduser().absolute()
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache).expanduser() if cache else Path.home() / ".cache"
    return base / "whero-doctidex"


def stable_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        identity = str(root.absolute())
        self.directory = state_home() / "roots" / stable_key(identity)
        self.path = self.directory / "state.json"
        self.lock_path = self.directory / "state.lock"

    def read(self) -> dict[str, Any]:
        with self.locked():
            return self._read_unlocked()

    def update(self, callback: Any) -> dict[str, Any]:
        with self.locked():
            data = self._read_unlocked()
            data["root"] = str(self.root)
            callback(data)
            self._write_unlocked(data)
            return data

    @contextmanager
    def locked(self) -> Iterator[None]:
        with file_lock(self.lock_path):
            yield

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "mounts": {}, "maintenance": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "mounts": {}, "maintenance": {}}
        if not isinstance(value, dict):
            return {"version": 1, "mounts": {}, "maintenance": {}}
        value.setdefault("version", 1)
        value.setdefault("mounts", {})
        value.setdefault("maintenance", {})
        return value

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        descriptor, name = tempfile.mkstemp(prefix=".state.", dir=self.directory)
        temp = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
        finally:
            temp.unlink(missing_ok=True)


def source_directory(url: str) -> Path:
    return state_home() / "sources" / stable_key(url)


def maintenance_host(maintenance_root: Path) -> Path | None:
    target = str(maintenance_root.absolute())
    roots = state_home() / "roots"
    if not roots.is_dir():
        return None
    for path in sorted(roots.glob("*/state.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict):
            continue
        maintenance = value.get("maintenance")
        if not isinstance(maintenance, dict):
            continue
        for item in maintenance.values():
            if not isinstance(item, dict) or item.get("path") != target:
                continue
            host_root = item.get("host_root") or value.get("root")
            return Path(host_root) if isinstance(host_root, str) and host_root else None
    return None


def write_diagnostic(error: BaseException) -> str:
    identifier = uuid.uuid4().hex[:12]
    directory = state_home() / "diagnostics"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{identifier}.log"
    path.write_text("".join(traceback.format_exception(error)), encoding="utf-8")
    return identifier
