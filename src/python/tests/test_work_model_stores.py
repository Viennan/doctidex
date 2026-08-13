from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

from whero.doctidex.cli.main import main
from whero.doctidex.initialization import RUNTIME_IGNORE_PATHS
from whero.doctidex.model import (
    BoundaryPoint,
    CacheItem,
    CacheItemStatus,
    Installation,
    ModelFormatError,
    RuntimeState,
    Worktree,
)
from whero.doctidex.model_view import RuntimeModelView, RuntimeWriteModelView
from whero.doctidex.store.cache import CacheStore
from whero.doctidex.store.files import atomic_write_bytes
from whero.doctidex.store.runtime import (
    JournalEntry,
    RecoveryRequired,
    RuntimeStore,
    TransactionJournal,
    _encode_json,
    _encode_state,
)


def test_init_creates_a_complete_ignored_workspace(tmp_path: Path) -> None:
    root = _git_repository(tmp_path)

    result = _run(["--repos-path", str(root), "init"])

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    workspace = root / ".doctidex-git"
    assert json.loads((workspace / "boundary-set.json").read_text()) == []
    assert json.loads((workspace / "imports.json").read_text()) == []
    assert json.loads((workspace / "import-refs.json").read_text()) == []
    assert json.loads((workspace / "runtime.json").read_text()) == {"imports": [], "worktrees": []}
    assert (workspace / "config.toml").read_text() == ""
    assert not list(root.glob(".*doctidex-git.initializing-*"))

    for path in RUNTIME_IGNORE_PATHS:
        ignored = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", "--", path.lstrip("/")],
            check=False,
        )
        assert ignored.returncode == 0


def test_init_is_idempotent_and_keeps_existing_model_state(tmp_path: Path) -> None:
    root = _git_repository(tmp_path)
    assert _run(["--repos-path", str(root), "init"]).code == 0
    store = RuntimeStore(root)
    state = RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/external"),),
        installations=(_installation(tracked=True),),
        refs=(),
        worktrees=(
            Worktree(
                url="https://example.test/work.git",
                install_id=None,
                base_commit_hash="0123456789abcdef",
                work_path="/work",
            ),
        ),
    )
    with store.write_transaction() as transaction:
        transaction.replace_state(state)

    result = _run(["--repos-path", str(root), "init"])

    assert result.code == 0
    assert store.read_state() == state


def test_init_reports_an_unresolved_explicit_git_root(tmp_path: Path) -> None:
    result = _run(["--repos-path", str(tmp_path), "init"])

    assert result.code == 2
    assert result.payload["message"]["code"] == "git-root.unresolved"
    assert result.payload["message"]["details"]["requested-repos-path"] == str(tmp_path)


def test_init_leaves_existing_workspace_validation_to_validate(tmp_path: Path) -> None:
    root = _git_repository(tmp_path)
    workspace = root / ".doctidex-git"
    workspace.mkdir()
    (workspace / "imports.json").write_text("[]\n")

    result = _run(["--repos-path", str(root), "init"])

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    assert not (workspace / "runtime.json").exists()


def test_init_does_not_interpret_pending_transactions_before_validate(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)
    changed = RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/external"),),
        installations=(),
        refs=(),
        worktrees=(),
    )
    _, directory = _prepared_journal(store, changed, transaction_id="pending-init")

    result = _run(["--repos-path", str(root), "init"])

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    assert directory.exists()


def test_runtime_state_rebuilds_tracked_and_runtime_projections(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)
    tracked = _installation(tracked=True)
    untracked = _installation(tracked=False, install_id="untracked", install_path="/imports/untracked")
    state = RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/external"),),
        installations=(tracked, untracked),
        refs=(),
        worktrees=(
            Worktree(
                url="https://example.test/work.git",
                install_id=None,
                base_commit_hash="0123456789abcdef",
                work_path="/work",
            ),
        ),
    )

    with store.write_transaction() as transaction:
        transaction.replace_state(state)

    workspace = root / ".doctidex-git"
    assert json.loads((workspace / "imports.json").read_text()) == [tracked.to_json()]
    assert json.loads((workspace / "runtime.json").read_text()) == {
        "imports": [untracked.to_json()],
        "worktrees": [state.worktrees[0].to_json()],
    }
    restored = store.read_state()
    assert restored == state
    assert {(point.type, point.path) for point in restored.boundary_points} == {
        ("custom", "/external"),
        ("import", "/imports/tracked"),
        ("import", "/imports/untracked"),
        ("worktree", "/work"),
    }


def test_runtime_read_only_transaction_does_not_create_a_journal(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)

    with store.read_only_transaction() as transaction:
        assert transaction.state == RuntimeState.empty()
        assert not hasattr(transaction, "replace_state")
        assert not store.transactions_path.exists()

    assert not store.transactions_path.exists()


def test_runtime_transactions_expose_the_model_and_refresh_indexes_after_updates(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)
    installation = _installation(tracked=False)

    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        view.upsert_installation(installation)
        assert view.installation(installation.install_id) == installation
        assert view.installation_at(installation.install_path) == installation

        tracked = view.set_installation_tracking(installation, tracked=True)
        assert tracked.tracked is True
        assert view.installation(installation.install_id) == tracked

    with store.read_only_transaction() as transaction:
        assert not hasattr(transaction, "view")
        view = RuntimeModelView(transaction)
        assert not hasattr(view, "upsert_installation")
        assert view.installation(installation.install_id) == tracked


def test_runtime_write_view_batches_custom_boundary_point_updates(tmp_path: Path, monkeypatch) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)

    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        replacements = 0
        original_replace_collections = transaction._replace_collections

        def replace_collections(**collections):
            nonlocal replacements
            replacements += 1
            original_replace_collections(**collections)

        monkeypatch.setattr(transaction, "_replace_collections", replace_collections)
        view.upsert_custom_boundary_points(
            (
                BoundaryPoint(type="custom", path="/first"),
                BoundaryPoint(type="custom", path="/second"),
            )
        )

        assert replacements == 1
        assert {item.path for item in transaction.state.custom_boundary_points} == {"/first", "/second"}

        view.remove_custom_boundary_points(("/first", "/second"))
        assert replacements == 2
        assert transaction.state.custom_boundary_points == ()


def test_runtime_write_transaction_marks_open_context_before_returning(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)

    transaction = store.write_transaction()
    transaction.__enter__()
    directories = list(store.transactions_path.iterdir())
    assert len(directories) == 1
    directory = directories[0]
    assert (directory / "journal.json").is_file()
    assert (directory / "stage").is_dir()
    assert (directory / "backup").is_dir()

    # Model an abrupt process termination: __exit__ is not called, but the lock is released by
    # the operating system.  A later transaction must observe and resolve the open marker.
    store._lock.release()
    with RuntimeStore(root).read_only_transaction() as recovered:
        assert recovered.recovery == "rolled-back"
    assert not directory.exists()


def test_runtime_write_transaction_cleans_marker_on_normal_noop_exit(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)

    with store.write_transaction():
        assert store.transactions_path.exists()

    assert not store.transactions_path.exists() or not any(store.transactions_path.iterdir())


def test_runtime_transaction_restores_old_state_from_a_mixed_publication(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)
    changed = RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/external"),),
        installations=(_installation(tracked=False),),
        refs=(),
        worktrees=(),
    )
    journal, directory = _prepared_journal(store, changed, transaction_id="mixed-publication")
    first_entry = journal.entries[0]
    os.replace(directory / first_entry.stage, store.workspace_path / first_entry.target)

    with store.read_only_transaction() as transaction:
        assert transaction.recovery == "rolled-back"
        assert transaction.state == RuntimeState.empty()

    assert not directory.exists()
    assert store.read_state() == RuntimeState.empty()


def test_runtime_transaction_refuses_unknown_recovery_state(tmp_path: Path) -> None:
    root = _initialized_repository(tmp_path)
    store = RuntimeStore(root)
    changed = RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/external"),),
        installations=(),
        refs=(),
        worktrees=(),
    )
    journal, directory = _prepared_journal(store, changed, transaction_id="unknown-state")
    target = store.workspace_path / journal.entries[0].target
    atomic_write_bytes(target, b'[\n  {"type": "custom", "path": "/other"}\n]\n', store="runtime", phase="test")

    with pytest.raises(RecoveryRequired):
        with store.read_only_transaction():
            pass

    assert (directory / "journal.json").exists()


def test_cache_store_write_transaction_publishes_records_immediately(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache")
    record = CacheItem(
        status=CacheItemStatus.PREPARING,
        git_url="https://example.test/repository.git",
        path="repository.git",
    )

    with store.write_transaction() as transaction:
        transaction.replace_records([record])
        assert json.loads(store.status_path.read_text()) == {"records": [record.to_json()]}

    assert json.loads(store.status_path.read_text()) == {"records": [record.to_json()]}


def test_cache_store_read_only_transaction_has_no_replace_records(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache")

    with store.read_only_transaction() as transaction:
        assert transaction.records == ()
        assert not hasattr(transaction, "replace_records")


def test_cache_store_transaction_cleans_preparing_records_and_repositories(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache")
    preparing = CacheItem(
        status=CacheItemStatus.PREPARING,
        git_url="https://example.test/preparing.git",
        path="repositories/preparing.git",
    )
    published = CacheItem(
        status=CacheItemStatus.PUBLISHED,
        git_url="https://example.test/published.git",
        path="repositories/published.git",
    )
    preparing_path = store.cache_path / preparing.path
    published_path = store.cache_path / published.path
    preparing_path.mkdir(parents=True)
    published_path.mkdir(parents=True)
    store._publish_records((preparing, published), phase="test")

    with store.read_only_transaction() as transaction:
        assert transaction.records == (published,)

    assert not preparing_path.exists()
    assert published_path.exists()
    assert json.loads(store.status_path.read_text()) == {"records": [published.to_json()]}


def test_cache_store_rejects_a_preparing_path_at_the_cache_root(tmp_path: Path) -> None:
    store = CacheStore(tmp_path / "cache")
    record = CacheItem(
        status=CacheItemStatus.PREPARING,
        git_url="https://example.test/root.git",
        path=".",
    )
    store._publish_records((record,), phase="test")

    with pytest.raises(ModelFormatError):
        with store.read_only_transaction():
            pass

    assert store.status_path.exists()


def _prepared_journal(
    store: RuntimeStore, state: RuntimeState, *, transaction_id: str
) -> tuple[TransactionJournal, Path]:
    new_documents = _encode_state(state)
    entries: list[JournalEntry] = []
    for name, new_content in new_documents.items():
        old_content = (store.workspace_path / name).read_bytes()
        if old_content == new_content:
            continue
        entries.append(
            JournalEntry(
                target=name,
                old_sha256=_sha256(old_content),
                new_sha256=_sha256(new_content),
                stage=f"stage/{name}",
                backup=f"backup/{name}",
            )
        )
    journal = TransactionJournal(transaction_id=transaction_id, state="publishing", entries=tuple(entries))
    directory = store.transactions_path / transaction_id
    (directory / "stage").mkdir(parents=True)
    (directory / "backup").mkdir()
    for entry in entries:
        old_content = (store.workspace_path / entry.target).read_bytes()
        atomic_write_bytes(directory / entry.stage, new_documents[entry.target], store="runtime", phase="test")
        atomic_write_bytes(directory / entry.backup, old_content, store="runtime", phase="test")
    atomic_write_bytes(directory / "journal.json", _encode_json(journal.to_json()), store="runtime", phase="test")
    return journal, directory


def _installation(
    *, tracked: bool, install_id: str = "tracked", install_path: str = "/imports/tracked"
) -> Installation:
    return Installation(
        tracked=tracked,
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_id=install_id,
        install_path=install_path,
        keys=("documentation",),
    )


def _initialized_repository(tmp_path: Path) -> Path:
    root = _git_repository(tmp_path)
    assert _run(["--repos-path", str(root), "init"]).code == 0
    return root


def _git_repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    return root


def _run(argv: list[str]) -> _RunResult:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(argv)
    return _RunResult(code, json.loads(output.getvalue()))


class _RunResult:
    def __init__(self, code: int, payload: dict[str, object]) -> None:
        self.code = code
        self.payload = payload


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
