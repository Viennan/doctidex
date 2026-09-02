from __future__ import annotations

from pathlib import Path

import pytest
from conftest import CliRunner, git_head, read_json, write_json

from whero.doctidex.model import (
    BranchSnapshot,
    InstallationContextReference,
    InstallationShare,
    ModelFormatError,
    RuntimeState,
    Worktree,
)


def _share(
    *,
    git_url: str = "https://example.test/repository.git",
    commit_hash: str = "0123456789abcdef",
    install_path: str = "/.doctidex-git/imports/example/commit/0123456789abcdef",
    install_ids: tuple[str, ...] = ("install",),
    context_references: tuple[InstallationContextReference, ...] = (),
    branch_refs: tuple[str, ...] = (),
) -> InstallationShare:
    return InstallationShare(
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path,
        install_ids=install_ids,
        context_references=context_references,
        branch_refs=branch_refs,
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
            "branch-snapshots": {},
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
            runtime={"imports": [], "worktrees": [], "branch-snapshots": {}},
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
                "branch-snapshots": {},
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
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [first, second],
            "branch-snapshots": {},
        },
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

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


def test_runtime_state_round_trips_branch_snapshots_and_share_branch_refs() -> None:
    share = _share(branch_refs=("main", "feature/topic"))
    snapshot = BranchSnapshot(
        installations=(),
        worktrees=(
            Worktree(
                url="https://example.test/work.git",
                install_id=None,
                base_commit_hash="0123456789abcdef",
                work_path="/work",
            ),
        ),
        installation_shares=(share,),
    )
    state = RuntimeState.from_documents(
        boundary_set=[],
        imports=[],
        import_refs=[],
        runtime={
            "imports": [],
            "worktrees": [],
            "installation-shares": [],
            "branch-snapshots": {"main": snapshot.to_json()},
        },
    )

    assert state.branch_snapshots == {"main": snapshot}
    assert state.to_documents()["runtime.json"]["branch-snapshots"] == {"main": snapshot.to_json()}


def test_runtime_state_requires_branch_snapshots() -> None:
    with pytest.raises(ModelFormatError) as exc_info:
        RuntimeState.from_documents(
            boundary_set=[],
            imports=[],
            import_refs=[],
            runtime={"imports": [], "worktrees": [], "installation-shares": []},
        )

    assert exc_info.value.artifact == "runtime.json"


def test_installation_share_requires_branch_refs() -> None:
    with pytest.raises(ModelFormatError):
        RuntimeState.from_documents(
            boundary_set=[],
            imports=[],
            import_refs=[],
            runtime={
                "imports": [],
                "worktrees": [],
                "installation-shares": [
                    {
                        "git-url": "https://example.test/repository.git",
                        "commit-hash": "0123456789abcdef",
                        "install-path": "/.doctidex-git/imports/example/commit/0123456789abcdef",
                        "install-ids": [],
                        "context-references": [],
                    }
                ],
                "branch-snapshots": {},
            },
        )


def _runtime_shares(root: Path) -> list[dict[str, object]]:
    return read_json(root / ".doctidex-git" / "runtime.json")["installation-shares"]


def test_branch_links_to_share_path_and_direct_commit_owns_share_path(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    branch = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--key",
        "topic",
    )
    direct = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--commit",
        commit,
    )

    assert branch.code == 0
    assert direct.code == 0
    branch_path = initialized_root / branch.payload["install-path"].lstrip("/")
    direct_path = initialized_root / direct.payload["install-path"].lstrip("/")
    share = _runtime_shares(initialized_root)[0]
    share_path = initialized_root / share["install-path"].lstrip("/")

    assert branch_path.is_symlink()
    assert direct_path.is_dir()
    assert share_path == direct_path
    assert branch_path.resolve(strict=False) == share_path.resolve(strict=False)
    assert set(share["install-ids"]) == {
        branch.payload["install-id"],
        direct.payload["install-id"],
    }
    assert share["branch-refs"] == ["main"]


def test_branch_and_tag_both_link_to_one_share_path(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    branch = cli.run(
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
    tag = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--tag",
        "v1",
    )

    assert branch.code == 0
    assert tag.code == 0
    branch_path = initialized_root / branch.payload["install-path"].lstrip("/")
    tag_path = initialized_root / tag.payload["install-path"].lstrip("/")
    assert branch_path.is_symlink()
    assert tag_path.is_symlink()
    assert branch_path.resolve(strict=False) == tag_path.resolve(strict=False)

    shares = _runtime_shares(initialized_root)
    assert len(shares) == 1
    assert set(shares[0]["install-ids"]) == {
        branch.payload["install-id"],
        tag.payload["install-id"],
    }


def test_removing_branch_keeps_share_path_for_direct_commit(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    branch = cli.run(
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
    direct = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--commit",
        commit,
    )

    removed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--install-id",
        branch.payload["install-id"],
    )

    assert removed.code == 0
    branch_path = initialized_root / branch.payload["install-path"].lstrip("/")
    direct_path = initialized_root / direct.payload["install-path"].lstrip("/")
    assert not branch_path.exists()
    assert direct_path.is_dir()
    shares = _runtime_shares(initialized_root)
    assert len(shares) == 1
    assert shares[0]["install-ids"] == [direct.payload["install-id"]]


def test_removing_direct_commit_keeps_share_path_for_branch(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    branch = cli.run(
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
    direct = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--commit",
        commit,
    )

    removed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--install-id",
        direct.payload["install-id"],
    )

    assert removed.code == 0
    branch_path = initialized_root / branch.payload["install-path"].lstrip("/")
    assert branch_path.is_symlink()
    assert branch_path.resolve(strict=False).is_dir()
    shares = _runtime_shares(initialized_root)
    assert len(shares) == 1
    assert shares[0]["install-ids"] == [branch.payload["install-id"]]


def test_query_and_untracked_selection_use_recorded_installations(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    branch = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--key",
        "topic",
    )

    queried = cli.run("--repos-path", str(initialized_root), "import", "query", "--key", "topic")
    selected = cli.run("--repos-path", str(initialized_root), "import", "remove", "--untracked")

    assert queried.code == 0
    assert [item["install-id"] for item in queried.payload["candidates"]] == [
        branch.payload["install-id"]
    ]
    assert selected.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert runtime["imports"] == []
    assert runtime["installation-shares"] == []


def test_removing_current_branch_keeps_share_for_other_branch_ref(
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
    runtime_path = initialized_root / ".doctidex-git" / "runtime.json"
    runtime = read_json(runtime_path)
    runtime["installation-shares"][0]["branch-refs"] = ["main", "feature"]
    write_json(runtime_path, runtime)

    removed = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--install-id",
        installed.payload["install-id"],
    )

    assert removed.code == 0
    shares = _runtime_shares(initialized_root)
    assert len(shares) == 1
    assert shares[0]["install-ids"] == []
    assert shares[0]["branch-refs"] == ["feature"]
    assert (initialized_root / shares[0]["install-path"].lstrip("/")).is_dir()
