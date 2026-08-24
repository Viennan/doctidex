from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, commit_file, git, make_git_repository, read_json, write_json


def test_installation_context_rejects_forbidden_commands_and_allows_read_only_commands(
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
    installation_root = initialized_root / installed.payload["install-path"].lstrip("/")

    forbidden = cli.run("--repos-path", str(installation_root), "init")
    assert forbidden.code == 2
    assert forbidden.payload["message"]["code"] == "installation.context.forbidden"
    assert forbidden.payload["message"]["subject"] == {
        "kind": "installation",
        "install-path": installed.payload["install-path"],
    }
    assert not (installation_root / ".doctidex-git").exists()

    validated = cli.run("--repos-path", str(installation_root), "validate", "--model-structure")
    assert validated.code == 1
    assert validated.payload["status"] == "ok"
    assert validated.payload["valid"] is False
    assert validated.payload["message"] == {}


def test_installation_context_queries_local_install_and_restores_to_owner(
    tmp_path: Path,
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    nested_source = make_git_repository(tmp_path / "nested-source")
    nested_commit = commit_file(nested_source, "readme.md", "nested\n")

    workspace = source_repository / ".doctidex-git"
    write_json(workspace / "boundary-set.json", [])
    write_json(workspace / "import-refs.json", [])
    write_json(workspace / "runtime.json", {"imports": [], "worktrees": []})
    write_json(
        workspace / "imports.json",
        [
            {
                "tracked": True,
                "git-url": str(nested_source),
                "commit-hash": nested_commit,
                "install-id": "nested-id",
                "install-path": "/.doctidex-git/imports/nested",
                "keys": ["nested"],
                "branch": "main",
                "tag": "",
            }
        ],
    )
    assert git(source_repository, "add", ".doctidex-git").returncode == 0
    assert git(source_repository, "commit", "--quiet", "-m", "workspace").returncode == 0

    owner_nested = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(nested_source),
        "--commit",
        nested_commit,
    )
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
    installation_root = initialized_root / installed.payload["install-path"].lstrip("/")

    parsed = cli.run("--repos-path", str(installation_root), "boundary-set", "parse", "--path", "/readme.md")
    assert parsed.code == 0
    assert parsed.payload["results"] == [{"path": "/readme.md", "has-boundary": False}]

    queried = cli.run(
        "--repos-path",
        str(installation_root),
        "import",
        "query",
        "--install-id",
        "nested-id",
    )
    candidate = queried.payload["candidates"][0]
    assert candidate["install-id"] == "nested-id"
    assert candidate["install-path"] == "/.doctidex-git/imports/nested"
    assert candidate["presentation-path"] == str(initialized_root / owner_nested.payload["install-path"].lstrip("/"))

    restored = cli.run(
        "--repos-path",
        str(installation_root),
        "import",
        "restore",
        "--install-id",
        "nested-id",
    )
    assert restored.code == 0
    assert restored.payload["install-id"] == "nested-id"
    assert restored.payload["install-path"] == "/.doctidex-git/imports/nested"
    assert Path(restored.payload["presentation-path"]).is_dir()
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    matching = [
        item
        for item in runtime["imports"]
        if item["git-url"] == str(nested_source) and item["commit-hash"] == nested_commit
    ]
    assert len(matching) == 1
    assert matching[0]["tracked"] is False
