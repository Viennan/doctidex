from __future__ import annotations

from pathlib import Path

from conftest import write_json

from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    InstallationShare,
    RuntimeState,
)
from whero.doctidex.store.runtime import RuntimeStore


def _write_state(
    root: Path,
    *,
    branch_snapshots: dict[str, BranchSnapshot] | None = None,
) -> None:
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=(),
        branch_snapshots=branch_snapshots or {},
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def test_write_mutations_defer_index_rebuild_until_query(
    initialized_root: Path,
    monkeypatch,
) -> None:
    share = InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/hash",
        install_ids=(),
        context_references=(),
        branch_refs=(),
    )
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(initialized_root, branch_snapshots={"feature": snapshot})
    store = RuntimeStore(initialized_root)

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        rebuild_count = 0
        original_reindex = transaction._reindex

        def counted_reindex() -> None:
            nonlocal rebuild_count
            rebuild_count += 1
            original_reindex()

        monkeypatch.setattr(transaction, "_reindex", counted_reindex)

        view.replace_branch_snapshots({})
        assert rebuild_count == 0

        assert view.installation("missing") is None
        assert rebuild_count == 1


def test_decorated_boundary_query_sees_new_boundary_after_mutation(
    initialized_root: Path,
) -> None:
    _write_state(initialized_root)
    store = RuntimeStore(initialized_root)

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        view.upsert_custom_boundary_points(
            (BoundaryPoint(type="custom", path="/new-boundary"),)
        )

        assert view.first_boundary("/new-boundary/child") == BoundaryPoint(
            type="custom", path="/new-boundary"
        )
