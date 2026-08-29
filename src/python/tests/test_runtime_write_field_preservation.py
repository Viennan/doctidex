from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields
from pathlib import Path

from conftest import write_json

from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    Installation,
    InstallationContextReference,
    InstallationShare,
    Ref,
    RuntimeState,
    Worktree,
)
from whero.doctidex.store.model_view import RuntimeWriteModelView
from whero.doctidex.store.runtime import RuntimeStore


def _sentinel_state() -> RuntimeState:
    installation = Installation(
        tracked=False,
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_id="sentinel-install",
        install_path="/sentinel-install",
        keys=("sentinel",),
        branch="sentinel-branch",
        tag="",
    )
    share = InstallationShare(
        git_url=installation.git_url,
        commit_hash=installation.commit_hash,
        install_path="/sentinel-share",
        install_ids=(installation.install_id,),
        context_references=(
            InstallationContextReference(install_id="sentinel-context", owner_install_id="sentinel-parent"),
        ),
        branch_refs=(installation.branch,),
    )
    ref = Ref(install_id=installation.install_id, src_sub_dir="", target_dir="/sentinel-ref")
    worktree = Worktree(
        url="https://example.test/worktree.git",
        install_id=None,
        base_commit_hash=installation.commit_hash,
        work_path="/sentinel-worktree",
    )
    snapshot = BranchSnapshot(
        installations=(installation,),
        worktrees=(worktree,),
        installation_shares=(share,),
    )
    return RuntimeState(
        custom_boundary_points=(BoundaryPoint(type="custom", path="/sentinel-boundary"),),
        installations=(installation,),
        refs=(ref,),
        worktrees=(worktree,),
        installation_shares=(share,),
        branch_snapshots={installation.branch: snapshot},
    )


def _write_view_cases(
    state: RuntimeState,
) -> tuple[tuple[str, set[str], Callable[[RuntimeWriteModelView], None]], ...]:
    installation = state.installations[0]
    share = state.installation_shares[0]
    ref = state.refs[0]
    worktree = state.worktrees[0]
    return (
        (
            "set-installation-tracking",
            {"installations"},
            lambda view: view.set_installation_tracking(installation, tracked=True),
        ),
        (
            "upsert-custom-boundary-points",
            {"custom_boundary_points"},
            lambda view: view.upsert_custom_boundary_points(
                (BoundaryPoint(type="custom", path="/new-boundary"),)
            ),
        ),
        (
            "remove-custom-boundary-points",
            {"custom_boundary_points"},
            lambda view: view.remove_custom_boundary_points(("/sentinel-boundary",)),
        ),
        ("upsert-installation", {"installations"}, lambda view: view.upsert_installation(installation)),
        ("remove-installations", {"installations"}, lambda view: view.remove_installations((installation.install_id,))),
        ("upsert-installation-share", {"installation_shares"}, lambda view: view.upsert_installation_share(share)),
        (
            "remove-installation-share",
            {"installation_shares"},
            lambda view: view.remove_installation_share(share.git_url, share.commit_hash),
        ),
        ("upsert-ref", {"refs"}, lambda view: view.upsert_ref(ref)),
        ("remove-ref", {"refs"}, lambda view: view.remove_ref(ref.target_dir)),
        ("upsert-worktree", {"worktrees"}, lambda view: view.upsert_worktree(worktree)),
        ("remove-worktrees", {"worktrees"}, lambda view: view.remove_worktrees((worktree.work_path,))),
        (
            "replace-branch-snapshots",
            {"branch_snapshots"},
            lambda view: view.replace_branch_snapshots({}),
        ),
        (
            "remove-branch-snapshots",
            {"branch_snapshots"},
            lambda view: view.remove_branch_snapshots((installation.branch,)),
        ),
    )


def _write_state(root: Path, state: RuntimeState) -> None:
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def test_each_write_view_mutation_preserves_unmodified_runtime_fields(initialized_root: Path) -> None:
    store = RuntimeStore(initialized_root)
    sentinel = _sentinel_state()

    for case_name, changed_fields, mutate in _write_view_cases(sentinel):
        _write_state(initialized_root, sentinel)
        with store.write_transaction() as transaction:
            mutate(transaction.write_model_view())
            actual = transaction.state

        for field in fields(RuntimeState):
            if field.name not in changed_fields:
                assert getattr(actual, field.name) == getattr(sentinel, field.name), case_name


def test_write_view_replaces_and_removes_branch_snapshots(initialized_root: Path) -> None:
    store = RuntimeStore(initialized_root)
    sentinel = _sentinel_state()

    _write_state(initialized_root, sentinel)
    with store.write_transaction() as transaction:
        transaction.write_model_view().remove_branch_snapshots(("sentinel-branch",))
        assert transaction.state.branch_snapshots == {}

    _write_state(initialized_root, sentinel)
    with store.write_transaction() as transaction:
        transaction.write_model_view().replace_branch_snapshots(
            {"new-branch": sentinel.branch_snapshots["sentinel-branch"]}
        )
        assert set(transaction.state.branch_snapshots) == {"new-branch"}
