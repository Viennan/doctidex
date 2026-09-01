from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, write_json

from whero.doctidex import imports
from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import InstallationShare, RuntimeState
from whero.doctidex.store.runtime import RuntimeStore


def _share() -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
        install_ids=(),
        context_references=(),
        branch_refs=("main",),
    )


def _write_presentation_state(root: Path) -> InstallationShare:
    share = _share()
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=(share,),
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)
    return share


def _presentation_id(root: Path) -> str:
    store = RuntimeStore(root)
    with store.read_only_transaction() as transaction:
        return transaction.model_view().state.presentation_installations[0].install_id


def test_track_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.track(RuntimeStore(initialized_root), presentation_id)

    assert exc_info.value.code == "installation.not-found"


def test_unload_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.unload(RuntimeStore(initialized_root), (presentation_id,))

    assert exc_info.value.code == "installation.not-found"


def test_ref_rejects_presentation_install_id(initialized_root: Path) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _presentation_id(initialized_root)

    with pytest.raises(CommandFailure) as exc_info:
        imports.ref(RuntimeStore(initialized_root), presentation_id, "", "/linked")

    assert exc_info.value.code == "installation.not-found"


def test_worktree_create_rejects_presentation_install_id(
    initialized_root: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    _write_presentation_state(initialized_root)
    presentation_id = _presentation_id(initialized_root)

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
