from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, read_json, write_json

EXPECTED_ROOT_INDEX = "---\ntype: index\ndoctidex:\n  type: index\n  root: true\n---\n"
RUNTIME_IGNORE_PATHS = (
    "/.doctidex-git/.lock",
    "/.doctidex-git/.command.lock",
    "/.doctidex-git/runtime.json",
    "/.doctidex-git/.transactions/",
    "/.doctidex-git/imports/",
    "/.doctidex-git/worktrees/",
)


def test_init_creates_a_complete_ignored_workspace(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    workspace = git_root / ".doctidex-git"
    assert read_json(workspace / "boundary-set.json") == []
    assert read_json(workspace / "imports.json") == []
    assert read_json(workspace / "import-refs.json") == []
    assert read_json(workspace / "runtime.json") == {
        "imports": [],
        "worktrees": [],
        "installation-shares": [],
    }
    assert (workspace / "config.toml").read_text() == ""
    assert (git_root / "index.md").read_text() == EXPECTED_ROOT_INDEX
    assert not list(git_root.glob(".*doctidex-git.initializing-*"))

    ignored_lines = (git_root / ".gitignore").read_text().splitlines()
    for path in RUNTIME_IGNORE_PATHS:
        assert path in ignored_lines


def test_init_reports_existing_workspace_and_keeps_its_state(initialized_root: Path, cli: CliRunner) -> None:
    workspace = initialized_root / ".doctidex-git"
    boundary_set = [{"type": "custom", "path": "/external"}]
    imports = [
        {
            "tracked": True,
            "git-url": "https://example.test/repository.git",
            "commit-hash": "0123456789abcdef",
            "install-id": "tracked",
            "install-path": "/imports/tracked",
            "keys": ["documentation"],
            "branch": "main",
            "tag": "",
        }
    ]
    runtime = {
        "imports": [],
        "worktrees": [
            {
                "url": "https://example.test/work.git",
                "install-id": None,
                "base-commit-hash": "0123456789abcdef",
                "work-path": "/work",
            }
        ],
        "installation-shares": [],
    }
    write_json(workspace / "boundary-set.json", boundary_set)
    write_json(workspace / "imports.json", imports)
    write_json(workspace / "import-refs.json", [])
    write_json(workspace / "runtime.json", runtime)

    result = cli.run("--repos-path", str(initialized_root), "init")

    assert result.code == 0
    assert result.payload["message"]["code"] == "workspace.already-initialized"
    assert result.payload["message"]["details"]["next-command"] == "validate --model-structure"
    assert read_json(workspace / "boundary-set.json") == boundary_set
    assert read_json(workspace / "imports.json") == imports
    assert read_json(workspace / "import-refs.json") == []
    assert read_json(workspace / "runtime.json") == runtime


def test_init_does_not_validate_existing_workspace(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / "index.md").write_text(
        "---\ntype: index\ndoctidex:\n  type: index\n  root: true\n---\n[missing](/missing.md)\n"
    )

    result = cli.run("--repos-path", str(initialized_root), "init")

    assert result.code == 0
    assert result.payload["message"]["code"] == "workspace.already-initialized"
    assert cli.run("--repos-path", str(initialized_root), "validate").payload["valid"] is False
    assert cli.run("--repos-path", str(initialized_root), "validate", "--model-structure").payload["valid"] is True


def test_init_supplements_existing_root_index_frontmatter(git_root: Path, cli: CliRunner) -> None:
    index = git_root / "index.md"
    index.write_text("---\ntitle: Overview\ndoctidex:\n  type: index\n---\nExisting body.\n")

    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    content = index.read_text()
    assert "title: Overview" in content
    assert "type: index" in content
    assert "root: true" in content
    assert content.endswith("Existing body.\n")


def test_init_rejects_conflicting_root_index_frontmatter(git_root: Path, cli: CliRunner) -> None:
    index = git_root / "index.md"
    original = "---\ntype: guide\n---\nExisting body.\n"
    index.write_text(original)

    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 2
    assert result.payload["message"]["code"] == "root-index.frontmatter.conflict"
    assert result.payload["message"]["subject"] == {"kind": "root-index", "path": "/index.md"}
    assert result.payload["message"]["details"] == {"field": "type", "expected": "index", "actual": "guide"}
    assert index.read_text() == original
    assert not (git_root / ".doctidex-git").exists()


def test_init_rejects_a_non_mapping_doctidex_frontmatter_field(git_root: Path, cli: CliRunner) -> None:
    (git_root / "index.md").write_text("---\ndoctidex: null\n---\n")

    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 2
    assert result.payload["message"]["code"] == "root-index.frontmatter.conflict"
    assert result.payload["message"]["details"] == {"field": "doctidex", "expected": "mapping", "actual": None}


def test_init_reports_an_unresolved_explicit_git_root(tmp_path: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(tmp_path), "init")

    assert result.code == 2
    assert result.payload["message"]["code"] == "git-root.unresolved"
    assert result.payload["message"]["details"]["requested-repos-path"] == str(tmp_path)


def test_init_reports_incomplete_existing_workspace_without_modifying_it(git_root: Path, cli: CliRunner) -> None:
    workspace = git_root / ".doctidex-git"
    workspace.mkdir()
    (workspace / "imports.json").write_text("[]\n")

    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    assert result.payload["message"]["code"] == "workspace.already-initialized"
    assert result.payload["message"]["details"]["next-command"] == "validate --model-structure"
    assert not (workspace / "runtime.json").exists()
    validation = cli.run("--repos-path", str(git_root), "validate", "--model-structure")
    assert validation.code == 1
    assert validation.payload["diagnostics"][0]["rule"] == "work-model.valid"


def test_init_reports_existing_workspace_without_recovering_pending_transactions(
    initialized_root: Path, cli: CliRunner
) -> None:
    directory = initialized_root / ".doctidex-git" / ".transactions" / "pending-init"
    directory.mkdir(parents=True)
    (directory / "journal.json").write_text("{}\n")

    result = cli.run("--repos-path", str(initialized_root), "init")

    assert result.code == 0
    assert result.payload["message"]["code"] == "workspace.already-initialized"
    assert directory.exists()


def test_init_completes_an_existing_empty_workspace(git_root: Path, cli: CliRunner) -> None:
    (git_root / ".doctidex-git").mkdir()

    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}
    assert (git_root / ".doctidex-git" / "runtime.json").exists()
