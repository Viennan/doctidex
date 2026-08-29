from __future__ import annotations

from pathlib import Path

from conftest import write_json

from whero.doctidex.imports import remove
from whero.doctidex.model import Installation, InstallationShare, RuntimeState
from whero.doctidex.store.model_view import RuntimeWriteModelView
from whero.doctidex.store.runtime import RuntimeStore


def _installation(install_id: str, install_path: str, branch: str = "", tag: str = "") -> Installation:
    return Installation(
        tracked=False,
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_id=install_id,
        install_path=install_path,
        keys=("repository",),
        branch=branch,
        tag=tag,
    )


def _write_state(
    root: Path,
    *,
    installations: tuple[Installation, ...],
    shares: tuple[InstallationShare, ...],
) -> None:
    state = RuntimeState(
        custom_boundary_points=(),
        installations=installations,
        refs=(),
        worktrees=(),
        installation_shares=shares,
        branch_snapshots={},
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def test_import_remove_batches_installation_and_share_writes(
    initialized_root: Path,
    monkeypatch,
) -> None:
    first = _installation("first", "/.doctidex-git/imports/example/main", branch="main")
    second = _installation("second", "/.doctidex-git/imports/example/v1", tag="v1")
    share = InstallationShare(
        git_url=first.git_url,
        commit_hash=first.commit_hash,
        install_path="/.doctidex-git/imports/example/hash",
        install_ids=(first.install_id, second.install_id),
        context_references=(),
        branch_refs=("main",),
    )
    _write_state(
        initialized_root,
        installations=(first, second),
        shares=(share,),
    )
    remove_install_calls: list[tuple[str, ...]] = []
    replace_share_calls: list[tuple[InstallationShare, ...]] = []
    original_remove_installations = RuntimeWriteModelView.remove_installations
    original_replace_shares = RuntimeWriteModelView.replace_installation_shares

    def recording_remove_installations(
        view: RuntimeWriteModelView,
        install_ids: tuple[str, ...],
    ) -> None:
        remove_install_calls.append(install_ids)
        original_remove_installations(view, install_ids)

    def recording_replace_shares(
        view: RuntimeWriteModelView,
        shares: tuple[InstallationShare, ...],
    ) -> None:
        replace_share_calls.append(shares)
        original_replace_shares(view, shares)

    monkeypatch.setattr(RuntimeWriteModelView, "remove_installations", recording_remove_installations)
    monkeypatch.setattr(RuntimeWriteModelView, "replace_installation_shares", recording_replace_shares)

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=True,
        auto=False,
        branches=(),
    )

    assert len(remove_install_calls) == 1
    assert set(remove_install_calls[0]) == {first.install_id, second.install_id}
    assert len(replace_share_calls) == 1
