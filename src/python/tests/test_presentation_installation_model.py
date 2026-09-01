from __future__ import annotations

import hashlib

from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    Installation,
    InstallationShare,
    RuntimeState,
    is_presentation_installation,
)


def _share(
    *,
    install_ids: tuple[str, ...] = (),
    branch_refs: tuple[str, ...] = ("main",),
) -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
        install_ids=install_ids,
        context_references=(),
        branch_refs=branch_refs,
    )


def _documents(*, installations: list[object], shares: list[object], branch_snapshots: object | None = None) -> dict:
    runtime = {
        "imports": installations,
        "worktrees": [],
        "installation-shares": shares,
        "branch-snapshots": branch_snapshots if branch_snapshots is not None else {},
    }
    return {
        "boundary-set.json": [],
        "imports.json": [],
        "import-refs.json": [],
        "runtime.json": runtime,
    }


def test_share_without_commit_installation_derives_presentation_installation() -> None:
    share = _share()
    documents = _documents(installations=[], shares=[share.to_json()])

    state = RuntimeState.from_documents(
        boundary_set=documents["boundary-set.json"],
        imports=documents["imports.json"],
        import_refs=documents["import-refs.json"],
        runtime=documents["runtime.json"],
    )

    assert state.installations == ()
    assert len(state.presentation_installations) == 1
    presentation = state.presentation_installations[0]
    expected_id = hashlib.sha256(share.install_path.encode("utf-8")).hexdigest()[:16]
    assert presentation.tracked is False
    assert presentation.branch == ""
    assert presentation.tag == ""
    assert presentation.install_path == share.install_path
    assert presentation.install_id == expected_id
    assert presentation.keys == ()
    assert presentation.presentation_path is None
    assert presentation.presentation_install_id is None
    assert is_presentation_installation(presentation, state.installation_shares) is True


def test_presentation_installation_contributes_import_boundary() -> None:
    share = _share()
    documents = _documents(installations=[], shares=[share.to_json()])

    state = RuntimeState.from_documents(
        boundary_set=documents["boundary-set.json"],
        imports=documents["imports.json"],
        import_refs=documents["import-refs.json"],
        runtime=documents["runtime.json"],
    )

    assert BoundaryPoint(type="import", path=share.install_path) in state.boundary_points


def test_share_with_normal_commit_installation_does_not_derive_duplicate() -> None:
    share = _share(install_ids=("commit",))
    installation = Installation(
        tracked=False,
        git_url=share.git_url,
        commit_hash=share.commit_hash,
        install_id="commit",
        install_path=share.install_path,
        keys=(),
        branch="",
        tag="",
    )
    documents = _documents(installations=[installation.to_json()], shares=[share.to_json()])

    state = RuntimeState.from_documents(
        boundary_set=documents["boundary-set.json"],
        imports=documents["imports.json"],
        import_refs=documents["import-refs.json"],
        runtime=documents["runtime.json"],
    )

    assert state.installations == (installation,)
    assert state.presentation_installations == ()
    assert is_presentation_installation(installation, state.installation_shares) is False


def test_runtime_state_round_trip_does_not_persist_derived_presentation_installation() -> None:
    share = _share()
    documents = _documents(installations=[], shares=[share.to_json()])

    state = RuntimeState.from_documents(
        boundary_set=documents["boundary-set.json"],
        imports=documents["imports.json"],
        import_refs=documents["import-refs.json"],
        runtime=documents["runtime.json"],
    )
    persisted = state.to_documents()

    assert persisted["runtime.json"]["imports"] == []
    assert persisted["runtime.json"]["installation-shares"] == [share.to_json()]


def test_branch_snapshot_does_not_derive_presentation_installation() -> None:
    share = _share()
    snapshot = BranchSnapshot.from_json(
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [share.to_json()],
        },
        artifact="runtime.json",
    )

    assert snapshot.installations == ()


def test_selector_installation_is_not_presentation_installation() -> None:
    share = _share(install_ids=("branch",))
    branch_installation = Installation(
        tracked=False,
        git_url=share.git_url,
        commit_hash=share.commit_hash,
        install_id="branch",
        install_path="/.doctidex-git/imports/example/branch/main",
        keys=(),
        branch="main",
        tag="",
    )

    assert is_presentation_installation(branch_installation, (share,)) is False
