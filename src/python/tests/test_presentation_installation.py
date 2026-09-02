from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from conftest import CliRunner, git_head, read_json, write_json

from whero.doctidex import imports
from whero.doctidex.errors import CommandFailure
from whero.doctidex.hooks import _merge_share_membership
from whero.doctidex.imports import remove
from whero.doctidex.installation import resolve_installation_context_by_id
from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    Installation,
    InstallationContextReference,
    InstallationShare,
    RuntimeState,
    is_presentation_installation,
)
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.store.runtime import RuntimeStore
from whero.doctidex.validate import _context_reference_violations


def _share(
    *,
    git_url: str = "https://example.test/repository.git",
    commit_hash: str = "0123456789abcdef",
    install_path: str | None = None,
    install_ids: tuple[str, ...] = (),
    context_references: tuple[InstallationContextReference, ...] = (),
    branch_refs: tuple[str, ...] = ("main",),
) -> InstallationShare:
    return InstallationShare(
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path or f"/.doctidex-git/imports/example/commit/{commit_hash}",
        install_ids=install_ids,
        context_references=context_references,
        branch_refs=branch_refs,
    )


def _write_state(
    root: Path,
    *,
    installations: tuple[Installation, ...] = (),
    shares: tuple[InstallationShare, ...] = (),
    branch_snapshots: dict[str, BranchSnapshot] | None = None,
    share: InstallationShare | None = None,
) -> None:
    if share is not None:
        shares = (share,)
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


def _load_state(root: Path) -> RuntimeState:
    return RuntimeState.from_documents(
        boundary_set=read_json(root / ".doctidex-git" / "boundary-set.json"),
        imports=read_json(root / ".doctidex-git" / "imports.json"),
        import_refs=read_json(root / ".doctidex-git" / "import-refs.json"),
        runtime=read_json(root / ".doctidex-git" / "runtime.json"),
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


def _write_presentation_state(root: Path) -> InstallationShare:
    share = _share()
    _write_state(root, shares=(share,))
    return share


def _read_presentation_id(root: Path) -> str:
    store = RuntimeStore(root)
    with store.read_only_transaction() as transaction:
        return transaction.model_view().state.presentation_installations[0].install_id


def _share_presentation_id(share: InstallationShare) -> str:
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


def _share_key(share: InstallationShare) -> tuple[str, str]:
    return (share.git_url, share.commit_hash)


def test_resolve_installation_context_accepts_derived_presentation_install_id(
    initialized_root: Path,
) -> None:
    share = _share()
    _write_state(initialized_root, shares=(share,))
    repo_path_to_fs(initialized_root, share.install_path).mkdir(parents=True)

    presentation = RuntimeStore(initialized_root).read_state().presentation_installations[0]
    context = resolve_installation_context_by_id(initialized_root, presentation.install_id)

    assert context.owner_root == initialized_root
    assert context.install_path == share.install_path


def test_boundary_set_parse_reports_presentation_install_path(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    share = _share()
    _write_state(initialized_root, shares=(share,))

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        f"{share.install_path}/readme.md",
    )

    assert parsed.code == 0
    assert parsed.payload["results"] == [
        {
            "path": f"{share.install_path}/readme.md",
            "has-boundary": True,
            "boundary-point": share.install_path,
            "boundary-type": "import",
        }
    ]


def test_merge_replaces_membership_but_preserves_current_branch_refs() -> None:
    current = _share(commit_hash="current", install_ids=("old",), branch_refs=("main", "feature"))
    target = _share(
        commit_hash="current",
        install_ids=("new",),
        context_references=(
            InstallationContextReference(install_id="child", owner_install_id="owner"),
        ),
        branch_refs=("feature",),
    )

    merged = _merge_share_membership([current.to_json()], (target,))

    assert merged == (
        _share(
            commit_hash="current",
            install_ids=("new",),
            context_references=(
                InstallationContextReference(install_id="child", owner_install_id="owner"),
            ),
            branch_refs=("main", "feature"),
        ),
    )


def test_merge_does_not_import_target_only_share() -> None:
    current = _share(commit_hash="current", install_ids=("old",))
    target_only = _share(commit_hash="target-only", install_ids=("target",))

    merged = _merge_share_membership([current.to_json()], (target_only,))

    assert _share_key(merged[0]) == ("https://example.test/repository.git", "current")
    assert all(share.commit_hash != "target-only" for share in merged)


def test_merge_keeps_current_only_share_with_empty_membership() -> None:
    current_only = _share(commit_hash="current-only", install_ids=("old",), branch_refs=("main", "feature"))

    merged = _merge_share_membership([current_only.to_json()], ())

    assert merged == (
        _share(commit_hash="current-only", install_ids=(), branch_refs=("main", "feature")),
    )


def test_branch_install_persists_selector_installation_and_derives_presentation(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )

    assert installed.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert len(runtime["imports"]) == 1
    assert runtime["imports"][0]["branch"] == "main"
    assert runtime["imports"][0]["tag"] == ""
    assert runtime["imports"][0]["install-id"] == installed.payload["install-id"]
    assert runtime["installation-shares"][0]["install-ids"] == [installed.payload["install-id"]]

    state = _load_state(initialized_root)
    assert len(state.presentation_installations) == 1
    presentation = state.presentation_installations[0]
    assert presentation.branch == ""
    assert presentation.tag == ""
    assert presentation.install_id not in runtime["installation-shares"][0]["install-ids"]


def test_commit_install_persists_normal_commit_installation_without_derived_duplicate(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--commit",
        git_head(source_repository),
    )

    assert installed.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert len(runtime["imports"]) == 1
    assert runtime["imports"][0]["branch"] == ""
    assert runtime["imports"][0]["tag"] == ""
    assert runtime["installation-shares"][0]["install-ids"] == [installed.payload["install-id"]]

    state = _load_state(initialized_root)
    assert state.presentation_installations == ()


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


def test_track_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _read_presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.track(RuntimeStore(initialized_root), presentation_id)

    assert exc_info.value.code == "installation.not-found"


def test_unload_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _read_presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.unload(RuntimeStore(initialized_root), (presentation_id,))

    assert exc_info.value.code == "installation.not-found"


def test_ref_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _read_presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.ref(RuntimeStore(initialized_root), presentation_id, "", "/linked")

    assert exc_info.value.code == "installation.not-found"


def test_worktree_create_rejects_presentation_install_id(
    initialized_root: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _read_presentation_id(initialized_root)

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--install-id",
        presentation_id,
        "--work-path",
        "/work",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "worktree.source.unavailable"


def test_query_resolves_presentation_install_id_and_path(initialized_root: Path) -> None:
    share = _write_presentation_state(initialized_root)
    store = RuntimeStore(initialized_root)

    with store.read_only_transaction() as transaction:
        model = transaction.model_view()
        presentation_id = model.state.presentation_installations[0].install_id

        by_id = imports.query(
            model,
            git_root=initialized_root,
            install_id=presentation_id,
            install_path=None,
            ref_path=None,
            keys=[],
        )
        by_path = imports.query(
            model,
            git_root=initialized_root,
            install_id=None,
            install_path=share.install_path,
            ref_path=None,
            keys=[],
        )

    assert [item["install-id"] for item in by_id] == [presentation_id]
    assert [item["install-id"] for item in by_path] == [presentation_id]


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
                owner_install_id=_share_presentation_id(presentation_owner_share),
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
                owner_install_id=_share_presentation_id(presentation_owner_share),
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
                owner_install_id=_share_presentation_id(presentation_owner_share),
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
                owner_install_id=_share_presentation_id(presentation_owner_share),
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
                owner_install_id=_share_presentation_id(owner_share),
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
                owner_install_id=_share_presentation_id(targeted_share),
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


def test_context_reference_owner_may_be_derived_presentation_installation() -> None:
    owner_share = _share(
        commit_hash="owner",
        install_path="/.doctidex-git/imports/example/commit/owner",
    )
    owner_install_id = _share_presentation_id(owner_share)
    targeted_share = _share(
        commit_hash="targeted",
        install_path="/.doctidex-git/imports/example/commit/targeted",
        context_references=(
            InstallationContextReference(install_id="child", owner_install_id=owner_install_id),
        ),
    )
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=(owner_share, targeted_share),
        branch_snapshots={},
    )

    violations = _context_reference_violations(state)

    assert all(item["code"] != "installation.context-reference.owner.missing" for item in violations)


def test_runtime_model_view_resolves_presentation_installation_by_id_and_path(
    initialized_root: Path,
) -> None:
    share = _share()
    _write_state(initialized_root, share=share)
    store = RuntimeStore(initialized_root)

    with store.read_only_transaction() as transaction:
        view = transaction.model_view()
        presentation = view.state.presentation_installations[0]

        assert view.installation(presentation.install_id) == presentation
        assert view.installation_at(share.install_path) == presentation
        assert view.installations == ()


def test_runtime_model_view_persisted_installation_excludes_presentation(
    initialized_root: Path,
) -> None:
    share = _share()
    _write_state(initialized_root, share=share)
    store = RuntimeStore(initialized_root)

    with store.read_only_transaction() as transaction:
        view = transaction.model_view()
        presentation = view.state.presentation_installations[0]

        assert view.persisted_installation(presentation.install_id) is None


def test_upsert_installation_treats_presentation_id_as_new_persisted_record(
    initialized_root: Path,
) -> None:
    share = _share()
    _write_state(initialized_root, share=share)
    store = RuntimeStore(initialized_root)

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        presentation = view.state.presentation_installations[0]
        installation = Installation(
            tracked=False,
            git_url=share.git_url,
            commit_hash=share.commit_hash,
            install_id=presentation.install_id,
            install_path=share.install_path,
            keys=(),
        )

        view.upsert_installation(installation)

        assert view.installations == (installation,)
        assert view.installation(installation.install_id) == installation
        assert view.persisted_installation(installation.install_id) == installation
