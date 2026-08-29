from __future__ import annotations

from pathlib import Path

import pytest
from conftest import write_json

from whero.doctidex.errors import CommandFailure
from whero.doctidex.imports import remove
from whero.doctidex.model import BranchSnapshot, InstallationShare, RuntimeState
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.store.model_view import RuntimeWriteModelView
from whero.doctidex.store.runtime import RuntimeStore


def _share(
    *,
    branch_refs: tuple[str, ...] = ("main",),
    install_ids: tuple[str, ...] = (),
    install_path: str = "/.doctidex-git/imports/example/hash",
) -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path=install_path,
        install_ids=install_ids,
        context_references=(),
        branch_refs=branch_refs,
    )


def _write_state(
    root: Path,
    *,
    shares: tuple[InstallationShare, ...],
    branch_snapshots: dict[str, BranchSnapshot],
) -> None:
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=shares,
        branch_snapshots=branch_snapshots,
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def _create_share_path(root: Path, share: InstallationShare) -> None:
    repo_path_to_fs(root, share.install_path).mkdir(parents=True)


def test_remove_explicit_branch_reconciles_active_share_refs(initialized_root: Path) -> None:
    share = _share(branch_refs=("main", "feature"))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"feature": snapshot},
    )

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=False,
        branches=("feature",),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert state.branch_snapshots == {}
    assert state.installation_shares[0].branch_refs == ("main",)


def test_remove_explicit_current_branch_is_rejected_before_mutation(initialized_root: Path) -> None:
    share = _share(branch_refs=("main",))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"main": snapshot},
    )

    with pytest.raises(CommandFailure) as exc_info:
        remove(
            RuntimeStore(initialized_root),
            None,
            untracked=False,
            auto=False,
            branches=("main",),
        )

    assert exc_info.value.code == "import.branch-snapshot.remove.current-branch"
    state = RuntimeStore(initialized_root).read_state()
    assert state.branch_snapshots == {"main": snapshot}
    assert state.installation_shares == (share,)


def test_remove_explicit_multiple_branches_and_unknown_is_noop(initialized_root: Path) -> None:
    share = _share(branch_refs=("main", "feature", "gone"))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"feature": snapshot, "gone": snapshot},
    )

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=False,
        branches=("feature", "gone", "missing"),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert state.branch_snapshots == {}
    assert state.installation_shares[0].branch_refs == ("main",)


def test_remove_auto_removes_stale_snapshot_and_keeps_current(initialized_root: Path) -> None:
    share = _share(branch_refs=("main", "gone"))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"main": snapshot, "gone": snapshot},
    )

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=True,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert set(state.branch_snapshots) == {"main"}
    assert state.installation_shares[0].branch_refs == ("main",)


def test_remove_auto_deletes_orphaned_share_and_worktree(initialized_root: Path) -> None:
    share = _share(branch_refs=("gone",))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"gone": snapshot},
    )
    _create_share_path(initialized_root, share)

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=True,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert state.branch_snapshots == {}
    assert state.installation_shares == ()
    assert not repo_path_to_fs(initialized_root, share.install_path).exists()


def test_branch_snapshot_removal_publishes_active_shares_once(
    initialized_root: Path,
    monkeypatch,
) -> None:
    share = _share(branch_refs=("main", "feature"))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"feature": snapshot},
    )
    calls: list[tuple[InstallationShare, ...]] = []
    original_replace = RuntimeWriteModelView.replace_installation_shares

    def recording_replace(
        view: RuntimeWriteModelView,
        shares: tuple[InstallationShare, ...],
    ) -> None:
        calls.append(shares)
        original_replace(view, shares)

    monkeypatch.setattr(RuntimeWriteModelView, "replace_installation_shares", recording_replace)

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=False,
        branches=("feature",),
    )

    assert len(calls) == 1
    assert calls[0][0].branch_refs == ("main",)
