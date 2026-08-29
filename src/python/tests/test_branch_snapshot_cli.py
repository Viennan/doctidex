from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, read_json, write_json

from whero.doctidex.model import BranchSnapshot, InstallationShare, RuntimeState
from whero.doctidex.paths import repo_path_to_fs


def _share(
    *,
    branch_refs: tuple[str, ...] = ("main",),
    install_path: str = "/.doctidex-git/imports/example/hash",
) -> InstallationShare:
    return InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path=install_path,
        install_ids=(),
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


def test_import_remove_branch_dispatches_to_snapshot_cleanup(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "feature",
    )

    assert result.code == 0


def test_import_remove_branch_rejects_current_branch(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "main",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "import.branch-snapshot.remove.current-branch"


def test_import_remove_branch_is_repeatable(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "feature",
        "--branch",
        "gone",
    )

    assert result.code == 0


def test_import_remove_branch_is_mutually_exclusive_with_auto(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "feature",
        "--auto",
    )

    assert result.code == 2


def test_cli_remove_branch_persists_snapshot_and_share_cleanup(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    share = _share(branch_refs=("main", "feature"))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"feature": snapshot},
    )

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "feature",
    )

    assert result.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert runtime["branch-snapshots"] == {}
    assert runtime["installation-shares"][0]["branch-refs"] == ["main"]


def test_cli_remove_auto_deletes_stale_snapshot_and_orphan_worktree(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    share = _share(branch_refs=("gone",))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"gone": snapshot},
    )
    _create_share_path(initialized_root, share)

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--auto",
    )

    assert result.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert runtime["branch-snapshots"] == {}
    assert runtime["installation-shares"] == []
    assert not repo_path_to_fs(initialized_root, share.install_path).exists()


def test_cli_remove_current_branch_preserves_runtime_state(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    share = _share(branch_refs=("main",))
    snapshot = BranchSnapshot(installations=(), worktrees=(), installation_shares=(share,))
    _write_state(
        initialized_root,
        shares=(share,),
        branch_snapshots={"main": snapshot},
    )

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--branch",
        "main",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "import.branch-snapshot.remove.current-branch"
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert runtime["branch-snapshots"] == {"main": snapshot.to_json()}
    assert runtime["installation-shares"] == [share.to_json()]
