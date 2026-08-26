from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, write_json

from whero.doctidex.model import InstallationContextReference, InstallationShare, ModelFormatError, RuntimeState


def _share(
    *,
    git_url: str = "https://example.test/repository.git",
    commit_hash: str = "0123456789abcdef",
    install_path: str = "/.doctidex-git/imports/example/0123456789abcdef",
    install_ids: tuple[str, ...] = ("install",),
    context_references: tuple[InstallationContextReference, ...] = (),
) -> InstallationShare:
    return InstallationShare(
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path,
        install_ids=install_ids,
        context_references=context_references,
    )


def test_runtime_state_round_trips_installation_shares() -> None:
    context_reference = InstallationContextReference(
        install_id="owner-side-id",
        owner_install_id="parent-id",
    )
    share = _share(
        install_ids=("owner-side-id", "selector"),
        context_references=(context_reference,),
    )
    documents = {
        "boundary-set.json": [],
        "imports.json": [],
        "import-refs.json": [],
        "runtime.json": {
            "imports": [],
            "worktrees": [],
            "installation-shares": [share.to_json()],
        },
    }

    state = RuntimeState.from_documents(
        boundary_set=documents["boundary-set.json"],
        imports=documents["imports.json"],
        import_refs=documents["import-refs.json"],
        runtime=documents["runtime.json"],
    )

    assert state.installation_shares == (share,)
    assert state.to_documents()["runtime.json"]["installation-shares"] == [share.to_json()]


def test_runtime_state_requires_installation_shares() -> None:
    with pytest.raises(ModelFormatError) as exc_info:
        RuntimeState.from_documents(
            boundary_set=[],
            imports=[],
            import_refs=[],
            runtime={"imports": [], "worktrees": []},
        )

    assert exc_info.value.artifact == "runtime.json"


def test_runtime_state_rejects_a_malformed_installation_share() -> None:
    with pytest.raises(ModelFormatError):
        RuntimeState.from_documents(
            boundary_set=[],
            imports=[],
            import_refs=[],
            runtime={
                "imports": [],
                "worktrees": [],
                "installation-shares": [{"git-url": "https://example.test/repository.git"}],
            },
        )


def test_validate_reports_conflicting_installation_shares(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    first = _share(install_ids=("first",)).to_json()
    second = _share(install_ids=("second",)).to_json()
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [first, second]},
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--model-structure")

    assert result.code == 1
    violations = [
        item
        for diagnostic in result.payload["diagnostics"]
        if diagnostic["rule"] == "work-model.valid"
        for item in diagnostic["details"]["violations"]
    ]
    assert any(
        item["code"] == "state-record.invalid" and item["details"]["identity-field"] == "installation-share-commit"
        for item in violations
    )
