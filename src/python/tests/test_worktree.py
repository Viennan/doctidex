from __future__ import annotations

import shutil
from pathlib import Path

from conftest import CliRunner, commit_file, git_head, git_ignored, read_json


def test_worktree_create_from_url_manages_custom_path_ignore_and_removal(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / ".gitignore").write_text("/kept/\n/projects/source/\n")

    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        "/projects/source",
    )

    assert created.code == 0
    assert created.payload == {"status": "ok", "message": {}, "work-path": "/projects/source"}
    target = initialized_root / "projects/source"
    assert target.is_dir()
    assert git_head(target) == git_head(source_repository)
    assert git_ignored(initialized_root, "projects/source/readme.md")
    assert cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "query",
        "--work-path",
        "/projects/source",
    ).payload == {"status": "ok", "message": {}}

    removed = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "remove",
        "--work-path",
        "/projects/source",
    )
    assert removed.code == 0
    assert not target.exists()
    assert (initialized_root / ".gitignore").read_text() == "/kept/\n/projects/source/\n"


def test_worktree_create_from_installation_uses_recorded_commit_and_default_path(
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
        "--branch",
        "main",
    )
    commit_file(source_repository, "later.md", "later\n")

    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--install-id",
        installed.payload["install-id"],
    )

    work_path = created.payload["work-path"]
    assert work_path.startswith(f"/.doctidex-git/worktrees/local/{source_repository.as_posix().lstrip('/')}/")
    assert len(work_path.rsplit("/", maxsplit=1)[-1]) == 7
    assert git_head(initialized_root / work_path.lstrip("/")) == commit
    assert git_ignored(initialized_root, work_path)
    queried = cli.run("--repos-path", str(initialized_root), "worktree", "query", "--work-path", work_path)
    assert queried.payload["install-id"] == installed.payload["install-id"]
    assert read_json(initialized_root / ".doctidex-git" / "runtime.json")["worktrees"][0]["base-commit-hash"] == commit


def test_worktree_url_selectors_use_and_record_the_resolved_base_commit(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    first_commit = git_head(source_repository)
    current_commit = commit_file(source_repository, "later.md", "later\n")

    branch = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--tree-name",
        "branch",
    )
    tag = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--tag",
        "v1",
        "--tree-name",
        "tag",
    )
    commit = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--commit",
        first_commit,
        "--tree-name",
        "commit",
    )

    assert git_head(initialized_root / branch.payload["work-path"].lstrip("/")) == current_commit
    assert git_head(initialized_root / tag.payload["work-path"].lstrip("/")) == first_commit
    assert git_head(initialized_root / commit.payload["work-path"].lstrip("/")) == first_commit
    records = read_json(initialized_root / ".doctidex-git" / "runtime.json")["worktrees"]
    assert {item["work-path"]: item["base-commit-hash"] for item in records} == {
        branch.payload["work-path"]: current_commit,
        tag.payload["work-path"]: first_commit,
        commit.payload["work-path"]: first_commit,
    }


def test_worktree_default_path_uses_git_url_hierarchy_and_nested_tree_name(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--commit",
        commit,
        "--tree-name",
        "review\\topic",
    )

    expected_path = f"/.doctidex-git/worktrees/local/{source_repository.as_posix().lstrip('/')}/review/topic"
    assert created.payload["work-path"] == expected_path
    assert git_head(initialized_root / expected_path.lstrip("/")) == commit


def test_worktree_remove_missing_and_dirty_paths(
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
        "--work-path",
        "/work",
    )
    target = initialized_root / created.payload["work-path"].lstrip("/")
    (target / "dirty.md").write_text("dirty\n")

    blocked = cli.run("--repos-path", str(initialized_root), "worktree", "remove", "--work-path", "/work")
    assert blocked.code == 2
    assert blocked.payload["message"]["code"] == "worktree.remove.blocked"
    assert target.exists()

    forced = cli.run("--repos-path", str(initialized_root), "worktree", "remove", "--work-path", "/work", "--force")
    assert forced.code == 0
    assert not target.exists()

    created = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        "/missing",
    )
    shutil.rmtree(initialized_root / created.payload["work-path"].lstrip("/"))
    cli.run("--repos-path", str(initialized_root), "worktree", "remove", "--work-path", "/missing")
    missing = cli.run("--repos-path", str(initialized_root), "worktree", "query", "--work-path", "/missing")
    assert missing.payload["message"]["code"] == "worktree.not-found"


def test_worktree_create_rejects_occupied_paths_and_unknown_installation(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    (initialized_root / "occupied").mkdir()

    occupied = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        "/occupied",
    )
    assert occupied.code == 2
    assert occupied.payload["message"]["code"] == "worktree.target.unavailable"
    assert occupied.payload["message"]["details"] == {"operation": "create", "occupant": "existing-path"}

    unavailable = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--install-id",
        "missing",
        "--work-path",
        "/work",
    )
    assert unavailable.code == 2
    assert unavailable.payload["message"]["code"] == "worktree.source.unavailable"


def test_worktree_create_rejects_managed_imports_paths_as_worktree(
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
        "--tracked",
        "--url",
        str(source_repository),
        "--branch",
        "main",
    )
    install_path = installed.payload["install-path"]
    install_root = initialized_root / install_path.lstrip("/")

    existing = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        install_path,
    )
    assert existing.code == 2
    assert existing.payload["message"]["code"] == "worktree.target.unavailable"
    assert existing.payload["message"]["details"] == {"operation": "create", "occupant": "managed-imports-directory"}

    if install_root.is_symlink():
        install_root.unlink()
    else:
        shutil.rmtree(install_root)
    absent = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        install_path,
    )
    assert absent.code == 2
    assert absent.payload["message"]["code"] == "worktree.target.unavailable"
    assert absent.payload["message"]["details"] == {"operation": "create", "occupant": "managed-imports-directory"}
    assert not install_root.exists()

    for work_path in ("/.doctidex-git/imports", "/.doctidex-git/imports/new/path"):
        rejected = cli.run(
            "--repos-path",
            str(initialized_root),
            "worktree",
            "create",
            "--url",
            str(source_repository),
            "--branch",
            "main",
            "--work-path",
            work_path,
        )
        assert rejected.code == 2
        assert rejected.payload["message"]["code"] == "worktree.target.unavailable"
        assert rejected.payload["message"]["details"] == {
            "operation": "create",
            "occupant": "managed-imports-directory",
        }
    assert not (initialized_root / ".doctidex-git" / "imports" / "new" / "path").exists()
    assert read_json(initialized_root / ".doctidex-git" / "runtime.json")["worktrees"] == []
    gitignore = (initialized_root / ".gitignore").read_text()
    assert "# doctidex-git worktree: /.doctidex-git/imports" not in gitignore


def test_worktree_create_rejects_path_below_existing_boundary_point(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")

    rejected = cli.run(
        "--repos-path",
        str(initialized_root),
        "worktree",
        "create",
        "--url",
        str(source_repository),
        "--branch",
        "main",
        "--work-path",
        "/external/project",
    )

    assert rejected.code == 2
    assert rejected.payload["message"]["code"] == "worktree.target.unavailable"
    assert rejected.payload["message"]["details"] == {"operation": "create", "occupant": "existing-boundary"}
    assert not (initialized_root / "external" / "project").exists()
