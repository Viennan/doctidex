"""Journaled, multi-file transactional storage for one Git-root work model."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from whero.doctidex.model import BoundaryPoint, Installation, ModelFormatError, Ref, RuntimeState, Worktree

from .files import (
    FileLock,
    StoreFailure,
    atomic_write_bytes,
    file_sha256,
    fsync_directory,
    read_bytes,
)

STATE_FILES = ("boundary-set.json", "imports.json", "import-refs.json", "runtime.json")
JournalState = Literal["prepared", "publishing", "committed"]
RecoveryOutcome = Literal["none", "committed", "rolled-back"]
_UNCOMMITTED_SHA256 = "0" * 64


class RecoveryRequired(StoreFailure):
    """A journal contains state that cannot be safely restored automatically."""


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One RuntimeStore target and its expected pre/post-publication digests."""

    target: str
    old_sha256: str | None
    new_sha256: str
    stage: str
    backup: str

    def to_json(self) -> dict[str, str | None]:
        return {
            "target": self.target,
            "old-sha256": self.old_sha256,
            "new-sha256": self.new_sha256,
            "stage": self.stage,
            "backup": self.backup,
        }


@dataclass(frozen=True, slots=True)
class TransactionJournal:
    """The persisted state machine for one RuntimeStore publication."""

    transaction_id: str
    state: JournalState
    entries: tuple[JournalEntry, ...]

    @classmethod
    def from_json(cls, value: object, *, journal_path: Path) -> TransactionJournal:
        if not isinstance(value, dict):
            raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
        transaction_id = value.get("transaction-id")
        state = value.get("state")
        entries = value.get("entries")
        if (
            value.get("version") != 1
            or value.get("store") != "runtime"
            or not isinstance(transaction_id, str)
            or state not in {"prepared", "publishing", "committed"}
            or not isinstance(entries, list)
        ):
            raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
        if journal_path.parent.name != transaction_id:
            raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
        parsed = tuple(_journal_entry(item, journal_path=journal_path) for item in entries)
        if not parsed:
            raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
        return cls(transaction_id=transaction_id, state=state, entries=parsed)

    def to_json(self) -> dict[str, object]:
        return {
            "version": 1,
            "transaction-id": self.transaction_id,
            "store": "runtime",
            "state": self.state,
            "entries": [entry.to_json() for entry in self.entries],
        }

    def with_state(self, state: JournalState) -> TransactionJournal:
        return TransactionJournal(transaction_id=self.transaction_id, state=state, entries=self.entries)


class RuntimeStore:
    """Manage tracked projections and runtime state under ``.doctidex-git``."""

    def __init__(self, git_root: Path) -> None:
        self.git_root = git_root
        self.workspace_path = git_root / ".doctidex-git"
        self.transactions_path = self.workspace_path / ".transactions"
        self._lock = FileLock(self.workspace_path / ".lock", store="runtime")

    def read_only_transaction(self) -> RuntimeReadOnlyTransaction:
        """Return a locked snapshot transaction without a publication journal."""

        return RuntimeReadOnlyTransaction(self)

    def write_transaction(self) -> RuntimeWriteTransaction:
        """Return a write transaction that journals its existence on entry."""

        return RuntimeWriteTransaction(self)

    def read_state(self) -> RuntimeState:
        """Read a locked state snapshot without recovering pending transactions."""

        self._lock.acquire()
        try:
            return self._load_state()
        finally:
            self._lock.release()

    def _load_state(self) -> RuntimeState:
        documents: dict[str, object] = {}
        for name in STATE_FILES:
            path = self.workspace_path / name
            if not path.is_file():
                raise ModelFormatError(name, "a required state file")
            documents[name] = _decode_json(read_bytes(path, store="runtime", phase="read"), artifact=name)
        return RuntimeState.from_documents(
            boundary_set=documents["boundary-set.json"],
            imports=documents["imports.json"],
            import_refs=documents["import-refs.json"],
            runtime=documents["runtime.json"],
        )

    def _snapshot_hashes(self) -> dict[str, str | None]:
        return {name: file_sha256(self.workspace_path / name) for name in STATE_FILES}

    def _recover_pending(self) -> RecoveryOutcome:
        if not self.transactions_path.exists():
            return "none"
        try:
            directories = sorted(path for path in self.transactions_path.iterdir() if path.is_dir())
        except OSError as exc:
            raise StoreFailure(store="runtime", phase="recovery", state_path=self.transactions_path) from exc

        outcome: RecoveryOutcome = "none"
        for directory in directories:
            journal_path = directory / "journal.json"
            journal = _load_journal(journal_path)
            observed = [_observe_entry(self.workspace_path, entry) for entry in journal.entries]
            if any(state == "unknown" for state in observed):
                raise RecoveryRequired(
                    store="runtime",
                    phase="recovery",
                    state_path=journal_path,
                    transaction_id=journal.transaction_id,
                )
            if all(state == "new" for state in observed):
                self._clean_journal(directory)
                outcome = "committed"
                continue
            if all(state == "old" for state in observed):
                self._clean_journal(directory)
                outcome = "rolled-back"
                continue
            self._restore_old_state(directory, journal)
            self._clean_journal(directory)
            outcome = "rolled-back"
        return outcome

    def _restore_old_state(self, directory: Path, journal: TransactionJournal) -> None:
        for entry in journal.entries:
            target = self.workspace_path / entry.target
            if entry.old_sha256 is None:
                try:
                    target.unlink(missing_ok=True)
                    fsync_directory(target.parent, store="runtime", phase="recovery")
                except OSError as exc:
                    raise StoreFailure(
                        store="runtime",
                        phase="recovery",
                        state_path=target,
                        transaction_id=journal.transaction_id,
                    ) from exc
                continue
            backup = directory / entry.backup
            if file_sha256(backup) != entry.old_sha256:
                raise RecoveryRequired(
                    store="runtime",
                    phase="recovery",
                    state_path=backup,
                    transaction_id=journal.transaction_id,
                )
            atomic_write_bytes(
                target,
                read_bytes(backup, store="runtime", phase="recovery"),
                store="runtime",
                phase="recovery",
            )
        # Do not rehash targets here. The recovery lock excludes another doctidex-git writer, while
        # one extra check cannot make arbitrary external edits safe or rule out a later race.

    def _clean_journal(self, directory: Path, *, phase: str = "recovery") -> None:
        try:
            shutil.rmtree(directory)
            fsync_directory(self.transactions_path, store="runtime", phase=phase)
        except OSError as exc:
            raise StoreFailure(store="runtime", phase=phase, state_path=directory) from exc

    def _commit(
        self,
        *,
        state: RuntimeState,
        snapshot_hashes: dict[str, str | None],
        directory: Path,
        transaction_id: str,
    ) -> None:
        new_documents = _encode_state(state)
        entries = tuple(
            JournalEntry(
                target=name,
                old_sha256=snapshot_hashes[name],
                new_sha256=_sha256(content),
                stage=f"stage/{name}",
                backup=f"backup/{name}",
            )
            for name, content in new_documents.items()
            if _sha256(content) != snapshot_hashes[name]
        )
        if not entries:
            self._clean_journal(directory, phase="commit")
            return

        journal = TransactionJournal(transaction_id=transaction_id, state="prepared", entries=entries)
        try:
            (directory / "stage").mkdir(parents=True, exist_ok=True)
            (directory / "backup").mkdir(exist_ok=True)
            for entry in entries:
                atomic_write_bytes(
                    directory / entry.stage,
                    new_documents[entry.target],
                    store="runtime",
                    phase="prepare",
                )
                if entry.old_sha256 is not None:
                    atomic_write_bytes(
                        directory / entry.backup,
                        read_bytes(self.workspace_path / entry.target, store="runtime", phase="prepare"),
                        store="runtime",
                        phase="prepare",
                    )
            self._write_journal(directory, journal, phase="prepare")
            journal = journal.with_state("publishing")
            self._write_journal(directory, journal, phase="publish")
            for entry in entries:
                try:
                    target = self.workspace_path / entry.target
                    target.parent.mkdir(parents=True, exist_ok=True)
                    (directory / entry.stage).replace(target)
                    fsync_directory(target.parent, store="runtime", phase="publish")
                except OSError as exc:
                    raise StoreFailure(
                        store="runtime",
                        phase="publish",
                        state_path=self.workspace_path / entry.target,
                        transaction_id=transaction_id,
                    ) from exc
            journal = journal.with_state("committed")
            self._write_journal(directory, journal, phase="commit")
            self._clean_journal(directory, phase="commit")
        except StoreFailure:
            raise
        except OSError as exc:
            raise StoreFailure(
                store="runtime",
                phase="prepare",
                state_path=directory,
                transaction_id=transaction_id,
            ) from exc

    def _write_journal(self, directory: Path, journal: TransactionJournal, *, phase: str) -> None:
        atomic_write_bytes(
            directory / "journal.json",
            _encode_json(journal.to_json()),
            store="runtime",
            phase=phase,
        )


class RuntimeTransaction:
    """A locked RuntimeStore state holder with private indexes for scoped ModelViews."""

    def __init__(self, store: RuntimeStore) -> None:
        self.store = store
        self.state = RuntimeState.empty()
        self.recovery: RecoveryOutcome = "none"
        self._snapshot_hashes: dict[str, str | None] = {}
        self._installations_by_id: dict[str, Installation] = {}
        self._installations_by_path: dict[str, Installation] = {}
        self._installations_by_source: dict[tuple[str, str, str], Installation] = {}
        self._installations_by_commit: dict[tuple[str, str], Installation] = {}
        self._refs_by_target_dir: dict[str, Ref] = {}
        self._refs_by_installation: dict[str, tuple[Ref, ...]] = {}
        self._worktrees_by_path: dict[str, Worktree] = {}
        self._custom_boundary_points_by_path: dict[str, BoundaryPoint] = {}
        self._boundary_points: tuple[BoundaryPoint, ...] = ()
        self._boundary_points_by_path: dict[str, BoundaryPoint] = {}
        self._reindex()

    def __enter__(self) -> Self:
        self.store._lock.acquire()
        try:
            self.recovery = self.store._recover_pending()
            self._set_state(self.store._load_state())
            self._snapshot_hashes = self.store._snapshot_hashes()
            self._after_enter()
        except Exception:
            self.store._lock.release()
            raise
        return self

    def _after_enter(self) -> None:
        """Allow write transactions to persist their transaction marker."""

    def _set_state(self, state: RuntimeState) -> None:
        self.state = state
        self._reindex()

    def _reindex(self) -> None:
        """Rebuild the private lookup indexes consumed by the current ModelView."""

        self._installations_by_id = {item.install_id: item for item in self.state.installations}
        self._installations_by_path = {item.install_path: item for item in self.state.installations}
        self._installations_by_source = {}
        self._installations_by_commit = {}
        for item in self.state.installations:
            if item.branch or item.tag:
                self._installations_by_source.setdefault((item.git_url, item.branch, item.tag), item)
            self._installations_by_commit.setdefault((item.git_url, item.commit_hash), item)
        self._refs_by_target_dir = {item.target_dir: item for item in self.state.refs}
        refs_by_installation: dict[str, list[Ref]] = {}
        for reference in self.state.refs:
            refs_by_installation.setdefault(reference.install_id, []).append(reference)
        self._refs_by_installation = {
            install_id: tuple(references) for install_id, references in refs_by_installation.items()
        }
        self._worktrees_by_path = {item.work_path: item for item in self.state.worktrees}
        self._custom_boundary_points_by_path = {item.path: item for item in self.state.custom_boundary_points}
        self._boundary_points = self.state.boundary_points
        self._boundary_points_by_path = {}
        for point in self._boundary_points:
            self._boundary_points_by_path.setdefault(point.path, point)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            self._before_exit(exc_type)
        finally:
            self.store._lock.release()
        return False

    def _before_exit(self, exc_type: object) -> None:
        """Complete or discard transaction-specific work before releasing the lock."""


class RuntimeReadOnlyTransaction(RuntimeTransaction):
    """A RuntimeStore snapshot that never creates or publishes a transaction journal."""


class RuntimeWriteTransaction(RuntimeTransaction):
    """A RuntimeStore transaction whose existence is journaled as soon as it opens."""

    def __init__(self, store: RuntimeStore) -> None:
        super().__init__(store)
        self._changed = False
        self._transaction_id: str | None = None
        self._directory: Path | None = None

    def _after_enter(self) -> None:
        transaction_id = uuid.uuid4().hex
        directory = self.store.transactions_path / transaction_id
        entries = tuple(
            JournalEntry(
                target=name,
                old_sha256=self._snapshot_hashes[name],
                new_sha256=_provisional_new_hash(self._snapshot_hashes[name]),
                stage=f"stage/{name}",
                backup=f"backup/{name}",
            )
            for name in STATE_FILES
        )
        journal = TransactionJournal(transaction_id=transaction_id, state="prepared", entries=entries)
        # Leave a durable marker whenever creation reaches the filesystem. If the process
        # terminates after this point, the next transaction can roll it back and repair.
        (directory / "stage").mkdir(parents=True)
        (directory / "backup").mkdir()
        self.store._write_journal(directory, journal, phase="prepare")
        fsync_directory(self.store.transactions_path, store="runtime", phase="prepare")
        self._transaction_id = transaction_id
        self._directory = directory

    def replace_state(self, state: RuntimeState) -> None:
        self._set_state(state)
        self._changed = True

    def _replace_collections(
        self,
        *,
        custom_boundary_points: tuple[BoundaryPoint, ...] | None = None,
        installations: tuple[Installation, ...] | None = None,
        refs: tuple[Ref, ...] | None = None,
        worktrees: tuple[Worktree, ...] | None = None,
    ) -> None:
        self.replace_state(
            RuntimeState(
                custom_boundary_points=(
                    custom_boundary_points
                    if custom_boundary_points is not None
                    else self.state.custom_boundary_points
                ),
                installations=installations if installations is not None else self.state.installations,
                refs=refs if refs is not None else self.state.refs,
                worktrees=worktrees if worktrees is not None else self.state.worktrees,
            )
        )

    def _before_exit(self, exc_type: object) -> None:
        directory = self._directory
        transaction_id = self._transaction_id
        if directory is None or transaction_id is None:
            return
        if exc_type is None and self._changed:
            self.store._commit(
                state=self.state,
                snapshot_hashes=self._snapshot_hashes,
                directory=directory,
                transaction_id=transaction_id,
            )
        else:
            self.store._clean_journal(directory, phase="rollback")


def _provisional_new_hash(old_hash: str | None) -> str:
    """Return a valid digest that cannot be mistaken for the current state hash."""

    if old_hash != _UNCOMMITTED_SHA256:
        return _UNCOMMITTED_SHA256
    return "1" * 64


def _journal_entry(value: object, *, journal_path: Path) -> JournalEntry:
    if not isinstance(value, dict):
        raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
    target = value.get("target")
    old_hash = value.get("old-sha256")
    new_hash = value.get("new-sha256")
    stage = value.get("stage")
    backup = value.get("backup")
    if (
        target not in STATE_FILES
        or old_hash is not None
        and not _is_digest(old_hash)
        or not _is_digest(new_hash)
        or stage != f"stage/{target}"
        or backup != f"backup/{target}"
    ):
        raise RecoveryRequired(store="runtime", phase="recovery", state_path=journal_path)
    return JournalEntry(target=target, old_sha256=old_hash, new_sha256=new_hash, stage=stage, backup=backup)


def _load_journal(path: Path) -> TransactionJournal:
    try:
        content = read_bytes(path, store="runtime", phase="recovery")
        document = _decode_json(content, artifact="journal.json")
        return TransactionJournal.from_json(document, journal_path=path)
    except ModelFormatError as exc:
        raise RecoveryRequired(store="runtime", phase="recovery", state_path=path) from exc


def _observe_entry(workspace: Path, entry: JournalEntry) -> Literal["old", "new", "unknown"]:
    observed = file_sha256(workspace / entry.target)
    if observed == entry.new_sha256:
        return "new"
    if observed == entry.old_sha256:
        return "old"
    return "unknown"


def _encode_state(state: RuntimeState) -> dict[str, bytes]:
    return {name: _encode_json(document) for name, document in state.to_documents().items()}


def _decode_json(content: bytes, *, artifact: str) -> object:
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelFormatError(artifact, "valid JSON") from exc


def _encode_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def _sha256(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)
