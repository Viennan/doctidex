from __future__ import annotations

from pathlib import Path

from conftest import write_json

from whero.doctidex.model import Installation, InstallationShare, RuntimeState
from whero.doctidex.store.runtime import RuntimeStore


def _write_state(root: Path, *, share: InstallationShare) -> None:
    state = RuntimeState(
        custom_boundary_points=(),
        installations=(),
        refs=(),
        worktrees=(),
        installation_shares=(share,),
    )
    for name, document in state.to_documents().items():
        write_json(root / ".doctidex-git" / name, document)


def _share() -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
        install_ids=(),
        context_references=(),
        branch_refs=("main",),
    )


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
