from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.document import DoctidexDocument

SCHEMA_VERSION = "1.0"


def cache_root() -> Path:
    override = os.environ.get("DOCTIDEX_GIT_CACHE")
    if override:
        return Path(override).expanduser().absolute()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "doctidex-git"


def source_id(canonical_source: str) -> str:
    return hashlib.sha256(canonical_source.encode()).hexdigest()[:24]


def source_cache(canonical_source: str) -> Path:
    return cache_root() / "sources" / f"{source_id(canonical_source)}.git"


class RootStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.absolute()
        self.directory = self.root / ".doctidex" / "git"
        self.install_directory = self.directory / "installs"
        self.worktree_directory = self.directory / "worktrees"
        self.runtime_path = self.directory / "runtime.json"
        self.manifest_path = self.directory / "manifest.json"
        self.lock_path = self.directory / ".mutation.lock"

    def read_runtime(self) -> dict[str, Any]:
        value = _read_json(self.runtime_path, missing=_empty_runtime())
        if not _valid_runtime(value):
            raise DoctidexError(
                "The doctidex-git runtime records are damaged.",
                operation="external",
                affected=[str(self.root)],
                actions=["Restore the records from a known valid state or recreate the affected managed object."],
                code="mapping_damaged",
                domain="external",
            )
        return value

    def update_runtime(self, callback: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        value = self.read_runtime()
        callback(value)
        self.directory.mkdir(parents=True, exist_ok=True)
        _write_json(self.runtime_path, value)
        return value

    def read_manifest(self, *, required: bool = False) -> dict[str, Any]:
        if not self.manifest_path.is_file():
            if required:
                raise DoctidexError(
                    "The versioned external recovery manifest is missing.",
                    operation="external_restore",
                    affected=[str(self.manifest_path)],
                    actions=["Restore the manifest from Git before retrying."],
                    requires_user="recovery_manifest",
                    code="recovery_manifest_missing",
                    domain="external",
                    path=str(self.manifest_path),
                )
            return _empty_manifest()
        try:
            value = _read_json(self.manifest_path, missing=None)
        except DoctidexError as exc:
            raise self._manifest_error() from exc
        if not _valid_manifest(value):
            raise self._manifest_error()
        return value

    def write_manifest(self, value: dict[str, Any]) -> None:
        if not _valid_manifest(value):
            raise self._manifest_error()
        self.directory.mkdir(parents=True, exist_ok=True)
        _write_json(self.manifest_path, value)

    def _manifest_error(self) -> DoctidexError:
        return DoctidexError(
            "The versioned external recovery manifest is invalid.",
            operation="external_restore",
            affected=[str(self.manifest_path)],
            actions=["Restore or repair a schema 1.0 manifest before retrying."],
            requires_user="recovery_manifest",
            code="recovery_manifest_invalid",
            domain="external",
            path=str(self.manifest_path),
        )

    def manifest_identity(self, value: dict[str, Any]) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()[:24]

    @contextmanager
    def mutation(self) -> Iterator[None]:
        self.directory.mkdir(parents=True, exist_ok=True)
        with directory_lock(self.lock_path, operation="root_mutation"):
            yield

    def ensure_host_layout(self) -> tuple[list[Path], dict[str, str]]:
        from .runner import git

        changed: list[Path] = []
        index_path = self.root / "index.md"
        document = DoctidexDocument.load(index_path)
        doctidex = document.doctidex
        if doctidex is None:
            doctidex = CommentedMap()
            document.data["doctidex"] = doctidex
        frontmatter = {"boundary_set": "existing", "unsafe": "existing"}
        for key, report_key in (("boundary-set", "boundary_set"), ("unsafe", "unsafe")):
            entries = doctidex.get(key)
            if not isinstance(entries, list):
                entries = CommentedSeq()
                doctidex[key] = entries
            if not any(isinstance(item, dict) and item.get("path") == ".doctidex/git/installs" for item in entries):
                entries.append(CommentedMap({"path": ".doctidex/git/installs"}))
                frontmatter[report_key] = "add"
        if "add" in frontmatter.values():
            document.write()
            changed.append(index_path)

        host_result = git(
            ["-C", str(self.root), "rev-parse", "--show-toplevel"],
            operation="host_git",
            check=False,
        )
        if host_result.returncode != 0:
            raise DoctidexError(
                "The selected doctidex root is not inside a Git working tree.",
                operation="host_git",
                affected=[str(self.root)],
                actions=["Select a doctidex root inside one Git working tree."],
                code="host_git_not_found",
                domain="external",
            )
        host = Path(host_result.stdout.strip()).absolute()
        prefix = self.root.relative_to(host).as_posix()
        base = f"/{prefix}/" if prefix != "." else "/"
        gitignore = host / ".gitignore"
        required = [
            f"{base}.doctidex/git/installs/",
            f"{base}.doctidex/git/worktrees/",
            f"{base}.doctidex/git/runtime.json",
            f"{base}.doctidex/git/.mutation.lock/",
        ]
        existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.is_file() else []
        missing = [line for line in required if line not in existing]
        if missing:
            content = "\n".join([*existing, *missing]).strip("\n") + "\n"
            _atomic_text(gitignore, content)
            changed.append(gitignore)
        return changed, frontmatter


@contextmanager
def source_mutation(
    canonical_source: str,
    *,
    operation: str = "source_mutation",
    conflict_code: str = "index_update_conflict",
) -> Iterator[None]:
    with source_mutation_id(
        source_id(canonical_source),
        operation=operation,
        conflict_code=conflict_code,
    ):
        yield


@contextmanager
def source_mutation_id(
    identifier: str,
    *,
    operation: str = "source_mutation",
    conflict_code: str = "index_update_conflict",
) -> Iterator[None]:
    lock = cache_root() / "locks" / f"{identifier}.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    with directory_lock(lock, operation=operation, conflict_code=conflict_code):
        yield


@contextmanager
def directory_lock(
    path: Path,
    *,
    operation: str,
    timeout: float = 10.0,
    conflict_code: str = "index_update_conflict",
) -> Iterator[None]:
    deadline = time.monotonic() + timeout
    while True:
        try:
            path.mkdir(parents=False)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise DoctidexError(
                    "A concurrent doctidex-git mutation is still active.",
                    operation=operation,
                    affected=[],
                    actions=["Wait for the active operation to finish, then rerun the dry-run."],
                    code=conflict_code,
                ) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        shutil.rmtree(path, ignore_errors=True)


def git_file_state(repository: Path, path: Path) -> str:
    from .runner import git

    if not path.exists():
        return "absent"
    relative = path.relative_to(repository).as_posix()
    tracked = git(
        ["-C", str(repository), "ls-files", "--error-unmatch", "--", relative], operation="git_state", check=False
    )
    if tracked.returncode == 0:
        modified = git(
            ["-C", str(repository), "status", "--porcelain", "--", relative], operation="git_state", check=False
        )
        return "modified" if modified.stdout.strip() else "tracked"
    return "untracked"


def _empty_runtime() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "installs": {}, "links": {}, "worktrees": {}}


def _empty_manifest() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "installs": {}, "links": {}}


def _valid_runtime(value: object) -> bool:
    if not (
        isinstance(value, dict)
        and value.get("schema_version") == SCHEMA_VERSION
        and all(isinstance(value.get(key), dict) for key in ("installs", "links", "worktrees"))
    ):
        return False
    installs = value["installs"]
    links = value["links"]
    worktrees = value["worktrees"]
    return (
        all(
            isinstance(identifier, str) and _valid_install(record, identifier, portable=False)
            for identifier, record in installs.items()
        )
        and all(_valid_link(record, target, installs) for target, record in links.items())
        and all(_valid_worktree(record, identifier) for identifier, record in worktrees.items())
    )


def _valid_manifest(value: object) -> bool:
    if not (
        isinstance(value, dict)
        and value.get("schema_version") == SCHEMA_VERSION
        and isinstance(value.get("installs"), dict)
        and isinstance(value.get("links"), dict)
    ):
        return False
    installs = value["installs"]
    links = value["links"]
    return all(
        isinstance(identifier, str) and _valid_install(record, identifier, portable=True)
        for identifier, record in installs.items()
    ) and all(_valid_link(record, target, installs) for target, record in links.items())


def _valid_install(record: object, identifier: str, *, portable: bool) -> bool:
    if not isinstance(record, dict):
        return False
    selector = record.get("revision_selector")
    commit = record.get("resolved_commit")
    valid = (
        record.get("install_id") == identifier
        and record.get("install_path") == f"/.doctidex/git/installs/{identifier}"
        and isinstance(record.get("source_url"), str)
        and bool(record["source_url"])
        and record.get("source_relation") in {"host_repository", "other", "unknown"}
        and isinstance(selector, dict)
        and selector.get("kind") in {"commit", "tag", "branch"}
        and isinstance(selector.get("value"), str)
        and bool(selector["value"])
        and (record.get("default_branch") is None or isinstance(record.get("default_branch"), str))
        and isinstance(commit, str)
        and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", commit) is not None
    )
    if portable or not valid:
        return valid
    return (
        isinstance(record.get("canonical_source"), str)
        and bool(record["canonical_source"])
        and isinstance(record.get("requested_default"), bool)
        and record.get("role") in {"direct", "dependency"}
        and isinstance(record.get("parents"), list)
        and all(isinstance(parent, str) and parent for parent in record["parents"])
        and len(set(record["parents"])) == len(record["parents"])
        and record.get("managed_state") == "complete"
    )


def _valid_link(record: object, target: object, installs: dict[str, Any]) -> bool:
    if not isinstance(target, str) or not _normalized_relative(target) or not isinstance(record, dict):
        return False
    install_id = record.get("install_id")
    return (
        record.get("target_path") == target
        and isinstance(install_id, str)
        and install_id in installs
        and _normalized_repository_path(record.get("repository_relative_path"))
        and record.get("safe_state") in {"safe", "unsafe"}
        and isinstance(record.get("responsible_index"), str)
        and _normalized_relative(record["responsible_index"])
        and PurePosixPath(record["responsible_index"]).name == "index.md"
    )


def _valid_worktree(record: object, identifier: object) -> bool:
    if not isinstance(identifier, str) or not isinstance(record, dict):
        return False
    selector = record.get("revision_selector")
    return (
        record.get("worktree_id") == identifier
        and record.get("source_kind") in {"managed_path", "url", "working_tree", "bare_gitdir", "gitfile"}
        and isinstance(record.get("source_identity"), str)
        and (record.get("source_url") is None or isinstance(record.get("source_url"), str))
        and isinstance(record.get("gitdir"), str)
        and isinstance(selector, dict)
        and selector.get("kind") in {"commit", "tag", "branch"}
        and isinstance(selector.get("value"), str)
        and re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", str(record.get("base_commit"))) is not None
        and record.get("root_internal_path") == f"/.doctidex/git/worktrees/{identifier}"
        and isinstance(record.get("worktree_path"), str)
        and _normalized_repository_path(record.get("repository_relative_path"))
    )


def _normalized_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _normalized_repository_path(value: object) -> bool:
    return value == "." or _normalized_relative(value)


def _read_json(path: Path, *, missing: Any) -> Any:
    if not path.is_file():
        return missing
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise DoctidexError(
            "A doctidex-git state document cannot be read.",
            operation="state_read",
            affected=[str(path)],
            actions=["Restore a valid state document before retrying."],
            code="mapping_damaged",
            domain="external",
            path=str(path),
        ) from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_text(path, content)


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
