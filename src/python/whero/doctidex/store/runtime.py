"""Journaled, multi-file transactional storage for one Git-root work model."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, replace
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
_UNCOMMITTED_SHA256 = "0" * 64


class RecoveryRequired(StoreFailure):
    """A journal contains state that cannot be safely restored automatically."""


class RepairRequired(RuntimeError):
    """Signal that a normal transaction found residual RuntimeStore journals."""

    def __init__(self, transaction_ids: tuple[str, ...]) -> None:
        super().__init__("RuntimeStore repair is required before the transaction can start")
        self.transaction_ids = transaction_ids


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One RuntimeStore target and its expected pre/post-publication digests."""

    target: str
    old_sha256: str | None
    new_sha256: str
    stage: str
    backup: str

    def to_json(self) -> dict[str, str | None]:
        """Return the journal entry as its persisted representation."""

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
        """Reconstruct a TransactionJournal from one persisted journal value."""

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
        """Return the TransactionJournal as its persisted representation."""

        return {
            "version": 1,
            "transaction-id": self.transaction_id,
            "store": "runtime",
            "state": self.state,
            "entries": [entry.to_json() for entry in self.entries],
        }

    def with_state(self, state: JournalState) -> TransactionJournal:
        """Return a copy of this journal at the requested state."""

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

    def diagnostic_transaction(self) -> RuntimeDiagnosticTransaction:
        """Return a locked read-only snapshot without journal recovery.

        ``validate`` and the existing-workspace branch of ``init`` need to observe a
        pending transaction as evidence, rather than silently recovering it.  This
        transaction deliberately has no publication capability and never changes a
        journal, state file, or cache record.
        """

        return RuntimeDiagnosticTransaction(self)

    def write_transaction(self) -> RuntimeWriteTransaction:
        """Return a write transaction that journals its existence on entry."""

        return RuntimeWriteTransaction(self)

    def unlocked_read_only_transaction(self) -> RuntimeUnlockedReadOnlyTransaction:
        """Return a lock-free read-only snapshot for already-isolated contexts."""

        return RuntimeUnlockedReadOnlyTransaction(self)

    def read_state(self) -> RuntimeState:
        """Read a state snapshot through the normal residual-journal check."""

        with self.read_only_transaction() as transaction:
            return transaction.state

    def clean_journal(self, directory: Path, *, phase: str = "recovery") -> None:
        """Remove one transaction journal directory and sync its parent."""

        try:
            shutil.rmtree(directory)
            fsync_directory(self.transactions_path, store="runtime", phase=phase)
        except OSError as exc:
            raise StoreFailure(store="runtime", phase=phase, state_path=directory) from exc

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

    def _pending_journals(self) -> tuple[TransactionJournal, ...]:
        if not self.transactions_path.exists():
            return ()
        try:
            directories = sorted(path for path in self.transactions_path.iterdir() if path.is_dir())
        except OSError as exc:
            raise StoreFailure(store="runtime", phase="recovery", state_path=self.transactions_path) from exc
        return tuple(_load_journal(directory / "journal.json") for directory in directories)

    def _inspect_pending_journals(self) -> tuple[TransactionJournal, ...]:
        """Read pending journals without changing them for diagnostic callers."""

        journals = self._pending_journals()
        for journal in journals:
            if journal.state == "committed":
                observed = tuple(observe_entry(self.workspace_path, entry) for entry in journal.entries)
                if not all(state == "new" for state in observed):
                    raise RecoveryRequired(
                        store="runtime",
                        phase="diagnostic-read",
                        state_path=self.transactions_path / journal.transaction_id / "journal.json",
                        transaction_id=journal.transaction_id,
                    )
        return journals

    def _commit(
        self,
        *,
        state: RuntimeState,
        snapshot_hashes: dict[str, str | None],
        directory: Path,
        transaction_id: str,
    ) -> None:
        new_documents = encode_state(state)
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
            self.clean_journal(directory, phase="commit")
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
            self.clean_journal(directory, phase="commit")
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
            pending = self.store._pending_journals()
            if pending:
                raise RepairRequired(tuple(journal.transaction_id for journal in pending))
            self._set_state(self.store._load_state())
            self._snapshot_hashes = self.store._snapshot_hashes()
            self._after_enter()
        except Exception:
            self.store._lock.release()
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            self._before_exit(exc_type)
        finally:
            self.store._lock.release()
        return False

    def model_view(self):
        """Return the read-only work-model view for this transaction."""

        from .model_view import RuntimeModelView

        return RuntimeModelView(self)

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

    def _before_exit(self, exc_type: object) -> None:
        """Complete or discard transaction-specific work before releasing the lock."""


class RuntimeReadOnlyTransaction(RuntimeTransaction):
    """A RuntimeStore snapshot that never creates or publishes a transaction journal."""


class RuntimeUnlockedReadOnlyTransaction(RuntimeTransaction):
    """A read-only snapshot that deliberately does not acquire the RuntimeStore lock."""

    def __enter__(self) -> Self:
        self._set_state(self.store._load_state())
        self._snapshot_hashes = self.store._snapshot_hashes()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self._before_exit(exc_type)
        return False


class RuntimeDiagnosticTransaction(RuntimeTransaction):
    """A locked snapshot that reports pending journals without recovering them."""

    def __init__(self, store: RuntimeStore) -> None:
        super().__init__(store)
        self.pending_journals: tuple[TransactionJournal, ...] = ()

    def __enter__(self) -> Self:
        self.store._lock.acquire()
        try:
            self.pending_journals = self.store._inspect_pending_journals()
            # A prepared or publishing journal must short-circuit user-visible
            # validation before a potentially inconsistent projection is read.
            if not any(journal.state in {"prepared", "publishing"} for journal in self.pending_journals):
                self._set_state(self.store._load_state())
        except Exception:
            self.store._lock.release()
            raise
        return self

    def reload_state(self) -> None:
        """Refresh the snapshot after repair has explicitly reconciled pending journals."""

        self._set_state(self.store._load_state())
        self._snapshot_hashes = self.store._snapshot_hashes()

    def repair_model_view(self):
        """Return the narrow repair view for this diagnostic transaction."""

        from .model_view import RuntimeRepairModelView

        return RuntimeRepairModelView(self)

    def _replace_refs_for_repair(self, refs: tuple[Ref, ...]) -> None:
        """Publish repair's narrowed Ref cleanup without opening a business journal."""

        if refs == self.state.refs:
            return
        atomic_write_bytes(
            self.store.workspace_path / "import-refs.json",
            _encode_json([reference.to_json() for reference in refs]),
            store="runtime",
            phase="repair",
        )
        self._set_state(replace(self.state, refs=refs))
        self._snapshot_hashes = self.store._snapshot_hashes()


class RuntimeWriteTransaction(RuntimeTransaction):
    """A RuntimeStore transaction whose existence is journaled as soon as it opens."""

    def __init__(self, store: RuntimeStore) -> None:
        super().__init__(store)
        self._changed = False
        self._transaction_id: str | None = None
        self._directory: Path | None = None

    def replace_state(self, state: RuntimeState) -> None:
        """Replace the transaction state and mark it for publication."""

        self._set_state(state)
        self._changed = True

    def write_model_view(self):
        """Return the write view for this transaction."""

        from .model_view import RuntimeWriteModelView

        return RuntimeWriteModelView(self)

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
                    custom_boundary_points if custom_boundary_points is not None else self.state.custom_boundary_points
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
            self.store.clean_journal(directory, phase="rollback")


def observe_entry(workspace: Path, entry: JournalEntry) -> Literal["old", "new", "unknown"]:
    """Classify one journal entry against the current on-disk target."""

    observed = file_sha256(workspace / entry.target)
    if observed == entry.new_sha256:
        return "new"
    if observed == entry.old_sha256:
        return "old"
    return "unknown"


def encode_state(state: RuntimeState) -> dict[str, bytes]:
    """Return the encoded state documents keyed by artifact name."""

    return {name: _encode_json(document) for name, document in state.to_documents().items()}


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
