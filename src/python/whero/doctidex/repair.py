"""Best-effort alignment of managed physical objects with RuntimeStore JSON."""

from __future__ import annotations

import os
from pathlib import Path

from whero.doctidex import imports as import_workflow
from whero.doctidex import worktree as worktree_workflow
from whero.doctidex.errors import CommandFailure
from whero.doctidex.git_cache import GitCache, GitCacheWriteTransaction
from whero.doctidex.initialization import _ensure_runtime_ignores
from whero.doctidex.model_view import RuntimeModelView, scan_managed_symlinks
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.store.files import StoreFailure, atomic_write_bytes, file_sha256, fsync_directory, read_bytes
from whero.doctidex.store.runtime import RecoveryRequired, RuntimeStore, TransactionJournal, _observe_entry


def repair(store: RuntimeStore, cache: GitCache) -> None:
    """Run an explicit full maintenance pass in a fresh GitCache Write transaction."""

    with cache.write_transaction() as cache_transaction:
        repair_core(store, cache_transaction)


def repair_core(
    store: RuntimeStore,
    cache_transaction: GitCacheWriteTransaction,
) -> None:
    """Repair under a caller-owned GitCache Write transaction.

    The caller must already hold the command coordination lock. This core only acquires the
    RuntimeStore diagnostic lock, so a normal command can reuse its existing Write transaction
    after a `repair-required` signal without nesting GitCache locks.
    """

    with store.diagnostic_transaction() as transaction:
        journals = transaction.pending_journals
        requires_physical_repair = _recover_pending_journals(store, journals)
        transaction.reload_state()
        model = RuntimeModelView(transaction)
        if requires_physical_repair:
            _ensure_runtime_ignores(store.git_root)
            worktree_workflow._align_custom_ignores(
                store.git_root,
                tuple(
                    item.work_path
                    for item in model.worktrees
                    if not item.work_path.startswith("/.doctidex-git/worktrees/")
                ),
            )

            for installation in model.installations:
                target = repo_path_to_fs(store.git_root, installation.install_path)
                if installation.tracked and not target.exists() and not target.is_symlink():
                    # Tracked installations can intentionally exist as metadata without files.
                    continue
                repository = cache_transaction.load(installation.git_url)
                _align_installation(store, repository, installation)

            _align_refs(store, model)
            _remove_unregistered_refs(store, model)

            for worktree in model.worktrees:
                target = repo_path_to_fs(store.git_root, worktree.work_path)
                if target.exists() or target.is_symlink():
                    continue
                repository = cache_transaction.load(worktree.url)
                _create_missing_worktree(store, repository, worktree)

        _clean_recovered_journals(store, journals)


def _recover_pending_journals(store: RuntimeStore, journals: tuple[TransactionJournal, ...]) -> bool:
    """Reconcile residual JSON as the first explicit step of repair.

    ``True`` means a non-committed journal may have outlived command-side physical effects, so
    repair must also align the physical model before those journals can be removed.
    """

    requires_physical_repair = not journals
    for journal in journals:
        directory = store.transactions_path / journal.transaction_id
        observed = tuple(_observe_entry(store.workspace_path, entry) for entry in journal.entries)
        if journal.state == "committed":
            if not all(state == "new" for state in observed):
                raise RecoveryRequired(
                    store="runtime",
                    phase="repair",
                    state_path=directory / "journal.json",
                    transaction_id=journal.transaction_id,
                )
            continue
        requires_physical_repair = True
        if any(state == "unknown" for state in observed):
            raise RecoveryRequired(
                store="runtime",
                phase="repair",
                state_path=directory / "journal.json",
                transaction_id=journal.transaction_id,
            )
        if not all(state == "new" for state in observed) and not all(state == "old" for state in observed):
            _restore_old_state(store, directory, journal)
    return requires_physical_repair


def _restore_old_state(store: RuntimeStore, directory: Path, journal: TransactionJournal) -> None:
    """Restore one mixed publication from its journal backup during repair."""

    for entry in journal.entries:
        target = store.workspace_path / entry.target
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
    # The repair lock excludes another doctidex-git writer. Rehashing cannot defend against
    # arbitrary external edits or a later race, so it adds no meaningful protection here.


def _clean_recovered_journals(store: RuntimeStore, journals: tuple[TransactionJournal, ...]) -> None:
    """Remove only journals whose JSON and physical repair completed in this invocation."""

    for journal in journals:
        store._clean_journal(store.transactions_path / journal.transaction_id, phase="repair")


def _align_installation(store: RuntimeStore, repository: Path, installation) -> None:
    target = repo_path_to_fs(store.git_root, installation.install_path)
    import_workflow._ensure_install_commit(
        repository,
        installation.git_url,
        "commit",
        installation.commit_hash,
        installation.commit_hash,
    )
    if not import_workflow._prepare_install_path(
        repository,
        target,
        git_url=installation.git_url,
        commit_hash=installation.commit_hash,
        install_path=installation.install_path,
    ):
        import_workflow._create_worktree(
            repository,
            target,
            installation.commit_hash,
            install_path=installation.install_path,
        )


def _align_refs(store: RuntimeStore, model: RuntimeModelView) -> None:
    by_id = {item.install_id: item for item in model.installations}
    for reference in model.refs:
        installation = by_id.get(reference.install_id)
        if installation is None:
            continue
        install_path = repo_path_to_fs(store.git_root, installation.install_path)
        source = install_path / reference.src_sub_dir.lstrip("/")
        target = repo_path_to_fs(store.git_root, reference.target_dir)
        expected = source.resolve(strict=False)
        if target.is_symlink() and target.resolve(strict=False) == expected:
            continue
        if target.exists() or target.is_symlink():
            raise _ref_target_failure(reference.target_dir, installation.install_id, "align")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(os.path.relpath(source, start=target.parent), target, target_is_directory=source.is_dir())
        except OSError as exc:
            raise _ref_target_failure(reference.target_dir, installation.install_id, "create") from exc


def _remove_unregistered_refs(store: RuntimeStore, model: RuntimeModelView) -> None:
    for candidate in scan_managed_symlinks(store.git_root, model):
        if candidate.ref is not None:
            continue
        path = repo_path_to_fs(store.git_root, candidate.path)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise _ref_target_failure(candidate.path, candidate.installation.install_id, "remove") from exc


def _create_missing_worktree(store: RuntimeStore, repository: Path, worktree) -> None:
    target = repo_path_to_fs(store.git_root, worktree.work_path)
    selector_kind = "install-id" if worktree.install_id is not None else "commit"
    selector_value = worktree.install_id or worktree.base_commit_hash
    worktree_workflow._ensure_worktree_commit(
        repository,
        worktree.url,
        worktree.base_commit_hash,
        work_path=worktree.work_path,
        selector_kind=selector_kind,
        selector_value=selector_value,
    )
    worktree_workflow._create_git_worktree(
        repository,
        target,
        worktree.base_commit_hash,
        worktree.work_path,
        worktree.url,
        worktree.install_id,
    )


def _ref_target_failure(target_dir: str, install_id: str, operation: str) -> CommandFailure:
    return CommandFailure(
        code="ref.target.unavailable",
        summary="The managed reference target cannot be aligned with its recorded source.",
        subject={"kind": "ref", "target-dir": target_dir},
        details={"install-id": install_id, "operation": operation},
    )


__all__ = ["repair", "repair_core"]
