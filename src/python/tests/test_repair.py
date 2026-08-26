from __future__ import annotations

import shutil
from pathlib import Path

from conftest import CliRunner, git_head, git_status, read_json, write_json


def _install_tracked(cli: CliRunner, root: Path, source: Path) -> dict[str, object]:
    result = cli.run(
        "--repos-path",
        str(root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source),
        "--branch",
        "main",
    )
    assert result.code == 0
    return result.payload


def test_repair_recreates_missing_ref_and_removes_unregistered_install_link(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    installed = cli.run(
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
    assert installed.code == 0
    installed = installed.payload
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        installed["install-id"],
        "--target-dir",
        "/linked",
    )
    (initialized_root / "linked").unlink()
    (initialized_root / "orphan").symlink_to(initialized_root / installed["install-path"].lstrip("/"))

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert (initialized_root / "linked").is_symlink()
    assert not (initialized_root / "orphan").exists()


def test_repair_recreates_a_dangling_ref_when_tracked_install_is_missing(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = _install_tracked(cli, initialized_root, source_repository)
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        installed["install-id"],
        "--target-dir",
        "/linked",
    )
    install_root = initialized_root / installed["install-path"].lstrip("/")
    shutil.rmtree(install_root.resolve())
    install_root.unlink()
    (initialized_root / "linked").unlink()

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert (initialized_root / "linked").is_symlink()
    assert (initialized_root / "linked").resolve(strict=False) == (
        initialized_root / installed["install-path"].lstrip("/")
    ).resolve(strict=False)


def test_repair_rebuilds_an_inconsistent_ref_target(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = _install_tracked(cli, initialized_root, source_repository)
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        installed["install-id"],
        "--target-dir",
        "/linked",
    )
    target = initialized_root / "linked"
    target.unlink()
    target.mkdir()
    (target / "old-content").write_text("replace me\n")

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert target.is_symlink()
    assert target.resolve(strict=False) == (
        initialized_root / installed["install-path"].lstrip("/")
    ).resolve(strict=False)


def test_repair_removes_stale_tool_worktree_ignore_pairs(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    (initialized_root / ".gitignore").write_text(
        (initialized_root / ".gitignore").read_text() + "# doctidex-git worktree: /old-work\n/old-work/\n"
    )

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert "# doctidex-git worktree: /old-work" not in (initialized_root / ".gitignore").read_text()


def test_repair_recreates_missing_worktree(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    work_path = created.payload["work-path"]
    shutil.rmtree(initialized_root / work_path.lstrip("/"))

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert (initialized_root / work_path.lstrip("/")).is_dir()
    assert cli.run("--repos-path", str(initialized_root), "validate").payload["valid"] is True


def test_repair_removes_a_ref_without_an_installation(initialized_root: Path, cache_home: Path, cli: CliRunner) -> None:
    write_json(
        initialized_root / ".doctidex-git" / "import-refs.json",
        [{"install-id": "missing", "src-sub-dir": "", "target-dir": "/obsolete"}],
    )
    (initialized_root / "obsolete").write_text("obsolete target\n")

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0
    assert not (initialized_root / "obsolete").exists()
    assert read_json(initialized_root / ".doctidex-git" / "import-refs.json") == []


def test_repair_discards_dirty_installation(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    installed = cli.run(
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
    assert installed.code == 0
    installed = installed.payload
    install_root = initialized_root / installed["install-path"].lstrip("/")
    expected_commit = git_head(source_repository)
    (install_root / "readme.md").write_text("dirty tracked\n")
    (install_root / "dirty-extra.md").write_text("dirty untracked\n")

    assert cli.run("--repos-path", str(initialized_root), "repair").code == 0

    assert git_head(install_root) == expected_commit
    assert git_status(install_root) == ""
    assert not (install_root / "dirty-extra.md").exists()
