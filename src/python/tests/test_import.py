from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, commit_file, git, git_head, read_json


def test_import_track_ref_query_unref_and_remove(
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
        "--key",
        "topic",
    )
    assert installed.code == 0
    install_id = installed.payload["install-id"]

    tracked = cli.run("--repos-path", str(initialized_root), "import", "track", "--install-id", install_id)
    assert tracked.code == 0
    assert tracked.payload["install-id"] == install_id

    ref = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        install_id,
        "--target-dir",
        "/linked",
    )
    assert ref.code == 0
    assert (initialized_root / "linked").is_symlink()

    candidates = cli.run("--repos-path", str(initialized_root), "import", "query", "--key", "topic")
    assert candidates.code == 0
    assert candidates.payload["candidates"][0]["install-id"] == install_id
    assert candidates.payload["candidates"][0]["refs"] == [{"src-sub-dir": "", "target-dir": "/linked"}]

    blocked = cli.run("--repos-path", str(initialized_root), "import", "remove", "--install-id", install_id)
    assert blocked.code == 2
    assert blocked.payload["message"]["code"] == "installation.remove.blocked"
    assert blocked.payload["message"]["details"]["blocked-installations"][0]["blocking-ref-target-dirs"] == ["/linked"]

    cli.run("--repos-path", str(initialized_root), "import", "unref", "--target-dir", "/linked")
    cli.run("--repos-path", str(initialized_root), "import", "remove", "--install-id", install_id)

    assert read_json(initialized_root / ".doctidex-git" / "imports.json") == []
    assert read_json(initialized_root / ".doctidex-git" / "import-refs.json") == []
    assert read_json(initialized_root / ".doctidex-git" / "runtime.json")["imports"] == []
    empty = cli.run("--repos-path", str(initialized_root), "import", "query", "--key", "topic")
    assert empty.payload["candidates"] == []


def test_import_remove_is_blocked_by_link_outside_boundary(
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
    (initialized_root / "index.md").write_text(f"[external]({install_path}/readme.md)\n")

    blocked = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "remove",
        "--install-id",
        installed.payload["install-id"],
    )

    assert blocked.code == 2
    links = blocked.payload["message"]["details"]["blocked-installations"][0]["blocking-links"]
    assert links == [{"path": "/index.md", "line": 1, "link-path": f"{install_path}/readme.md"}]


def test_import_ref_links_block_unref_and_installation_removal(
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
    install_id = installed.payload["install-id"]
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        install_id,
        "--target-dir",
        "/linked",
    )
    (initialized_root / "index.md").write_text("[linked](/linked/readme.md)\n")

    blocked_install = cli.run("--repos-path", str(initialized_root), "import", "remove", "--install-id", install_id)
    details = blocked_install.payload["message"]["details"]["blocked-installations"][0]
    assert details["blocking-links"] == [{"path": "/index.md", "line": 1, "link-path": "/linked/readme.md"}]
    assert details["blocking-ref-target-dirs"] == ["/linked"]

    blocked_ref = cli.run("--repos-path", str(initialized_root), "import", "unref", "--target-dir", "/linked")
    assert blocked_ref.code == 2
    assert blocked_ref.payload["message"]["code"] == "ref.remove.blocked"

    (initialized_root / "index.md").write_text("")
    cli.run("--repos-path", str(initialized_root), "import", "unref", "--target-dir", "/linked")
    cli.run("--repos-path", str(initialized_root), "import", "remove", "--install-id", install_id)


def test_import_restore_uses_the_recorded_commit(
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
        "--tag",
        "v1",
    )
    install_directory = initialized_root / installed.payload["install-path"].lstrip("/")
    removed = git(install_directory, "worktree", "remove", "--force", str(install_directory))
    assert removed.returncode == 0
    assert not install_directory.exists()

    commit_file(source_repository, "other.md", "other\n")
    git(source_repository, "tag", "--force", "v1")
    restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "restore",
        "--install-id",
        installed.payload["install-id"],
    )

    assert restored.code == 0
    assert install_directory.is_dir()
    assert git_head(install_directory) == commit


def test_import_branch_revision_replacement_retains_managed_ref(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    initial = cli.run(
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
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        initial.payload["install-id"],
        "--target-dir",
        "/linked",
    )

    new_commit = commit_file(source_repository, "next.md", "next\n")
    updated = cli.run(
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

    assert updated.payload["install-path"] == initial.payload["install-path"]
    assert updated.payload["install-id"] != initial.payload["install-id"]
    assert git_head(initialized_root / updated.payload["install-path"].lstrip("/")) == new_commit
    imports = read_json(initialized_root / ".doctidex-git" / "imports.json")
    refs = read_json(initialized_root / ".doctidex-git" / "import-refs.json")
    assert imports[0]["install-id"] == updated.payload["install-id"]
    assert imports[0]["tracked"] is True
    assert refs[0]["install-id"] == updated.payload["install-id"]


def test_import_tag_revision_replacement(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    initial = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        "--tag",
        "v1",
    )
    repeated = cli.run(
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
    assert repeated.payload == initial.payload

    new_commit = commit_file(source_repository, "next.md", "next\n")
    git(source_repository, "tag", "--force", "v1")
    updated = cli.run(
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

    assert updated.payload["install-path"] == initial.payload["install-path"]
    assert updated.payload["install-id"] != initial.payload["install-id"]
    assert git_head(initialized_root / updated.payload["install-path"].lstrip("/")) == new_commit


def test_import_commit_install_reuses_same_source_and_commit(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)
    initial = cli.run(
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
    repeated = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--commit",
        commit,
    )

    assert repeated.payload == initial.payload
    assert initial.payload["install-path"].endswith(f"/{commit}")


def test_import_query_by_install_path_and_ref_path(
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
    install_id = installed.payload["install-id"]
    install_path = installed.payload["install-path"]
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        install_id,
        "--target-dir",
        "/linked",
    )

    by_path = cli.run("--repos-path", str(initialized_root), "import", "query", "--install-path", install_path)
    assert by_path.payload["candidates"][0]["install-id"] == install_id
    by_ref = cli.run("--repos-path", str(initialized_root), "import", "query", "--ref-path", "/linked")
    assert by_ref.payload["candidates"][0]["install-id"] == install_id


def test_import_track_reports_missing_installation(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    result = cli.run("--repos-path", str(initialized_root), "import", "track", "--install-id", "missing")

    assert result.code == 2
    assert result.payload["message"]["code"] == "installation.not-found"


def test_import_ref_rejects_missing_installation(
    initialized_root: Path, cache_home: Path, cli: CliRunner
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        "missing",
        "--target-dir",
        "/linked",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "installation.not-found"


def test_import_restore_rejects_untracked_installation(
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

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "restore",
        "--install-id",
        installed.payload["install-id"],
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "installation.tracking-state.invalid"


def test_import_ref_rejects_occupied_target(
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
    (initialized_root / "occupied").write_text("occupied\n")

    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "ref",
        "--install-id",
        installed.payload["install-id"],
        "--target-dir",
        "/occupied",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "ref.target.unavailable"
