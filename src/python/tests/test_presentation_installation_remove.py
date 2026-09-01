from __future__ import annotations

import hashlib
from pathlib import Path

from conftest import CliRunner, write_json

from whero.doctidex.imports import remove
from whero.doctidex.model import (
    BranchSnapshot,
    Installation,
    InstallationContextReference,
    InstallationShare,
    RuntimeState,
)
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.store.runtime import RuntimeStore


def _share(
    *,
    git_url: str = "https://example.test/repository.git",
    commit_hash: str,
    install_path: str,
    install_ids: tuple[str, ...] = (),
    context_references: tuple[InstallationContextReference, ...] = (),
    branch_refs: tuple[str, ...] = ("main",),
) -> InstallationShare:
    return InstallationShare(
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path,
        install_ids=install_ids,
        context_references=context_references,
        branch_refs=branch_refs,
    )


def _write_state(
    root: Path,
    *,
    installations: tuple[Installation, ...] = (),
    shares: tuple[InstallationShare, ...],
    branch_snapshots: dict[str, BranchSnapshot] | None = None,
) -> None:
    state = RuntimeState(
        custom_boundary_points=(),
        installations=installations,
        refs=(),
        worktrees=(),
        installation_shares=shares,
        branch_snapshots=branch_snapshots or {},
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def _presentation_id(share: InstallationShare) -> str:
    return hashlib.sha256(share.install_path.encode("utf-8")).hexdigest()[:16]


def _normal_installation(install_id: str, install_path: str, *, commit_hash: str) -> Installation:
    return Installation(
        tracked=False,
        git_url="https://example.test/repository.git",
        commit_hash=commit_hash,
        install_id=install_id,
        install_path=install_path,
        keys=(),
        branch="",
        tag="",
    )


def test_install_id_removal_does_not_delete_presentation_context_share(
    initialized_root: Path,
) -> None:
    normal_share = _share(
        commit_hash="normal-commit",
        install_path="/.doctidex-git/imports/example/commit/normal",
        install_ids=("normal",),
    )
    presentation_owner_share = _share(
        commit_hash="presentation-owner-commit",
        install_path="/.doctidex-git/imports/example/commit/presentation-owner",
    )
    targeted_share = _share(
        commit_hash="targeted-commit",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(
                install_id="child",
                owner_install_id=_presentation_id(presentation_owner_share),
            ),
        ),
    )
    _write_state(
        initialized_root,
        installations=(
            _normal_installation("normal", normal_share.install_path, commit_hash=normal_share.commit_hash),
        ),
        shares=(normal_share, presentation_owner_share, targeted_share),
    )

    remove(
        RuntimeStore(initialized_root),
        "normal",
        untracked=False,
        auto=False,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert {share.install_path for share in state.installation_shares} == {
        presentation_owner_share.install_path,
        targeted_share.install_path,
    }


def test_targeted_selector_deletes_qualifying_share_and_physical_path(
    initialized_root: Path,
) -> None:
    presentation_owner_share = _share(
        commit_hash="presentation-owner-commit",
        install_path="/.doctidex-git/imports/example/commit/presentation-owner",
    )
    targeted_share = _share(
        commit_hash="targeted-commit",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(
                install_id="child",
                owner_install_id=_presentation_id(presentation_owner_share),
            ),
        ),
    )
    _write_state(
        initialized_root,
        shares=(presentation_owner_share, targeted_share),
    )
    repo_path_to_fs(initialized_root, targeted_share.install_path).mkdir(parents=True)

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=False,
        presentation_installation_context=True,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert state.installation_shares == ()
    assert not repo_path_to_fs(initialized_root, targeted_share.install_path).exists()


def test_auto_includes_presentation_context_cleanup(
    initialized_root: Path,
) -> None:
    presentation_owner_share = _share(
        commit_hash="presentation-owner-commit",
        install_path="/.doctidex-git/imports/example/commit/presentation-owner",
    )
    targeted_share = _share(
        commit_hash="targeted-commit",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(
                install_id="child",
                owner_install_id=_presentation_id(presentation_owner_share),
            ),
        ),
    )
    _write_state(
        initialized_root,
        shares=(presentation_owner_share, targeted_share),
    )
    repo_path_to_fs(initialized_root, targeted_share.install_path).mkdir(parents=True)

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=True,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    assert state.installation_shares == ()
    assert not repo_path_to_fs(initialized_root, targeted_share.install_path).exists()


def test_cli_presentation_installation_context_selector(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    presentation_owner_share = _share(
        commit_hash="presentation-owner-commit",
        install_path="/.doctidex-git/imports/example/commit/presentation-owner",
    )
    targeted_share = _share(
        commit_hash="targeted-commit",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(
                install_id="child",
                owner_install_id=_presentation_id(presentation_owner_share),
            ),
        ),
    )
    _write_state(
        initialized_root,
        shares=(presentation_owner_share, targeted_share),
    )
    repo_path_to_fs(initialized_root, targeted_share.install_path).mkdir(parents=True)

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--presentation-installation-context",
    )

    assert result.code == 0
    state = RuntimeStore(initialized_root).read_state()
    assert state.installation_shares == ()
    assert not repo_path_to_fs(initialized_root, targeted_share.install_path).exists()


def test_targeted_selector_cleans_selected_share_and_owned_references_from_snapshots(
    initialized_root: Path,
) -> None:
    owner_share = _share(
        commit_hash="owner",
        install_path="/.doctidex-git/imports/example/commit/owner",
    )
    targeted_share = _share(
        commit_hash="targeted",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(
                install_id="child",
                owner_install_id=_presentation_id(owner_share),
            ),
        ),
    )
    survivor_share = _share(
        commit_hash="survivor",
        install_path="/.doctidex-git/imports/example/commit/survivor",
        install_ids=("survivor-install",),
        context_references=(
            InstallationContextReference(
                install_id="other-child",
                owner_install_id=_presentation_id(targeted_share),
            ),
        ),
    )
    snapshot = BranchSnapshot(
        installations=(),
        worktrees=(),
        installation_shares=(targeted_share, survivor_share),
    )
    _write_state(
        initialized_root,
        shares=(owner_share, targeted_share, survivor_share),
        branch_snapshots={"feature": snapshot},
    )

    remove(
        RuntimeStore(initialized_root),
        None,
        untracked=False,
        auto=False,
        presentation_installation_context=True,
        branches=(),
    )

    state = RuntimeStore(initialized_root).read_state()
    snapshot_shares = state.branch_snapshots["feature"].installation_shares
    assert {share.commit_hash for share in snapshot_shares} == {"survivor"}
    assert snapshot_shares[0].context_references == ()
