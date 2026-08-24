from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, git_head


def test_boundary_set_add_parse_remove_and_derived_import_point(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    commit = git_head(source_repository)

    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/docs/../guides")
    parsed = cli.run("--repos-path", str(initialized_root), "boundary-set", "parse", "--path", "/guides/topic.md")
    assert parsed.payload["results"] == [
        {
            "path": "/guides/topic.md",
            "has-boundary": True,
            "boundary-point": "/guides",
            "boundary-type": "custom",
        }
    ]

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
        "guide",
    )
    assert installed.code == 0
    install_path = installed.payload["install-path"]
    assert (initialized_root / install_path.lstrip("/") / "readme.md").is_file()
    assert git_head(initialized_root / install_path.lstrip("/")) == commit

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        f"{install_path}/readme.md",
    )
    assert parsed.payload["results"][0]["boundary-type"] == "import"
    assert parsed.payload["results"][0]["boundary-point"] == install_path

    cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "remove",
        "--path",
        "/guides",
        "--path",
        "/guides",
    )
    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        "/guides/topic.md",
    )
    assert parsed.payload["results"] == [{"path": "/guides/topic.md", "has-boundary": False}]
    not_recorded = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "remove",
        "--path",
        "/not-recorded",
    )
    assert not_recorded.payload == {"status": "ok", "message": {}}
    derived = cli.run("--repos-path", str(initialized_root), "boundary-set", "remove", "--path", install_path)
    assert derived.code == 2
    assert derived.payload["message"]["code"] == "boundary-point.remove.prohibited"


def test_boundary_set_parse_reports_worktree_boundary(
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
        "/projects/source",
    )
    assert created.code == 0
    work_path = created.payload["work-path"]

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        f"{work_path}/readme.md",
    )

    assert parsed.payload["results"] == [
        {
            "path": f"{work_path}/readme.md",
            "has-boundary": True,
            "boundary-point": work_path,
            "boundary-type": "worktree",
        }
    ]


def test_boundary_set_parse_reports_ref_boundary(
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
    assert installed.code == 0
    install_id = installed.payload["install-id"]

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

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        "/linked/readme.md",
    )
    assert parsed.payload["results"] == [
        {
            "path": "/linked/readme.md",
            "has-boundary": True,
            "boundary-point": "/linked",
            "boundary-type": "import-ref",
        }
    ]

    derived = cli.run("--repos-path", str(initialized_root), "boundary-set", "remove", "--path", "/linked")
    assert derived.code == 2
    assert derived.payload["message"]["code"] == "boundary-point.remove.prohibited"
