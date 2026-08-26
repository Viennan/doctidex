from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, git_head, read_json


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
