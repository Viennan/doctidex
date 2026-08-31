from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, read_json


def _install_tracked(
    cli: CliRunner,
    initialized_root: Path,
    source_repository: Path,
    *,
    selector: str,
    value: str,
) -> object:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--tracked",
        "--url",
        str(source_repository),
        selector,
        value,
    )
    assert result.code == 0, result.payload
    return result.payload


def test_import_unload_detaches_multiple_tracked_installations_and_keeps_records(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    branch = _install_tracked(cli, initialized_root, source_repository, selector="--branch", value="main")
    tag = _install_tracked(cli, initialized_root, source_repository, selector="--tag", value="v1")
    install_ids = [branch["install-id"], tag["install-id"]]
    install_paths = [branch["install-path"], tag["install-path"]]

    unloaded = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        install_ids[0],
        "--install-id",
        install_ids[1],
    )

    assert unloaded.code == 0
    assert unloaded.payload == {"status": "ok", "message": {}}
    imports = read_json(initialized_root / ".doctidex-git" / "imports.json")
    assert [item["install-id"] for item in imports] == install_ids
    assert all(item["tracked"] is True for item in imports)
    assert read_json(initialized_root / ".doctidex-git" / "runtime.json")["installation-shares"] == []

    for install_path in install_paths:
        assert not (initialized_root / install_path.lstrip("/")).exists()

    for install_id in install_ids:
        queried = cli.run(
            "--repos-path",
            str(initialized_root),
            "import",
            "query",
            "--install-id",
            install_id,
        )
        assert queried.payload["candidates"][0]["restore-state"] == "restore-required"


def test_import_unload_keeps_shared_worktree_while_another_install_id_remains(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    branch = _install_tracked(cli, initialized_root, source_repository, selector="--branch", value="main")
    tag = _install_tracked(cli, initialized_root, source_repository, selector="--tag", value="v1")

    unloaded = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        branch["install-id"],
    )

    assert unloaded.code == 0
    assert not (initialized_root / branch["install-path"].lstrip("/")).exists()
    tag_path = initialized_root / tag["install-path"].lstrip("/")
    assert tag_path.is_symlink()

    shares = read_json(initialized_root / ".doctidex-git" / "runtime.json")["installation-shares"]
    assert len(shares) == 1
    assert shares[0]["install-ids"] == [tag["install-id"]]

    branch_query = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "query",
        "--install-id",
        branch["install-id"],
    )
    tag_query = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "query",
        "--install-id",
        tag["install-id"],
    )
    assert branch_query.payload["candidates"][0]["restore-state"] == "restore-required"
    assert tag_query.payload["candidates"][0]["restore-state"] == "available"


def test_import_unload_deletes_orphaned_share_and_is_idempotent(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = _install_tracked(cli, initialized_root, source_repository, selector="--branch", value="main")
    install_path = initialized_root / installed["install-path"].lstrip("/")
    backing_path = install_path.resolve()

    first = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        installed["install-id"],
    )

    assert first.code == 0
    assert not install_path.exists()
    assert not backing_path.exists()
    assert read_json(initialized_root / ".doctidex-git" / "runtime.json")["installation-shares"] == []

    second = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        installed["install-id"],
    )
    assert second.code == 0


def test_import_unload_rejects_untracked_installation(
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
        "unload",
        "--install-id",
        installed.payload["install-id"],
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "installation.tracking-state.invalid"


def test_import_unload_rejects_unknown_installation(
    initialized_root: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    result = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        "missing",
    )

    assert result.code == 2
    assert result.payload["message"]["code"] == "installation.not-found"


def test_import_unload_requires_install_id(
    initialized_root: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    result = cli.run("--repos-path", str(initialized_root), "import", "unload")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"


def test_import_unload_leaves_ref_and_validate_accepts_restore_required(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = _install_tracked(cli, initialized_root, source_repository, selector="--branch", value="main")
    install_id = installed["install-id"]
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
    (initialized_root / "index.md").write_text(
        "[linked](/linked/readme.md)\n"
        "<!-- doctidex: {cross-boundary-point: /linked} -->\n"
    )

    before = cli.run("--repos-path", str(initialized_root), "validate")
    assert before.code == 0
    assert before.payload["valid"] is True

    unloaded = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        install_id,
    )
    assert unloaded.code == 0
    assert (initialized_root / "linked").is_symlink()

    after = cli.run("--repos-path", str(initialized_root), "validate")
    assert after.code == 0
    assert after.payload["valid"] is True


def test_import_unload_restore_recreates_ref_target(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    installed = _install_tracked(cli, initialized_root, source_repository, selector="--branch", value="main")
    install_id = installed["install-id"]
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
    cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "unload",
        "--install-id",
        install_id,
    )

    restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "restore",
        "--install-id",
        install_id,
    )

    assert restored.code == 0
    assert (initialized_root / "linked" / "readme.md").is_file()
