from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from whero.doctidex.errors import DoctidexError
from whero.doctidex.git.external import ExternalService
from whero.doctidex.git.source import RevisionSelector
from whero.doctidex.git.storage import RootStorage, directory_lock
from whero.doctidex.git.worktrees import WorktreeService
from whero.doctidex.protocol.root import root_at


def git(cwd: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(cwd), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    return process.stdout.strip()


def make_writable(path: Path) -> None:
    for item in [path, *path.rglob("*")]:
        if item.is_symlink():
            continue
        item.chmod(item.stat().st_mode | stat.S_IWUSR)


def run(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    *,
    expected: int = 0,
) -> dict:
    process = subprocess.run(
        [sys.executable, "-m", "whero.doctidex.cli.main", *command, "--json"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode == expected, process.stdout + process.stderr
    payload = json.loads(process.stdout)
    for field in (
        "schema_version",
        "operation",
        "status",
        "result",
        "root",
        "changed",
        "network",
        "findings",
        "next_actions",
        "affected",
        "requires_user",
        "collection",
    ):
        assert field in payload
    if payload["status"] != "blocked":
        required = {
            "validate": {
                "coverage",
                "scopes",
                "protocol_structure",
                "scan_complete",
                "semantic_review",
                "semantic_candidates",
            },
            "external_install": {
                "applied",
                "install_id",
                "install_role",
                "dependency_of",
                "manifest_included",
                "install_path",
                "working_path",
                "source_url",
                "source_relation",
                "revision_selector",
                "default_branch",
                "resolved_commit",
                "host_repository",
                "payload_tracking",
                "git_exclusion_file",
                "git_exclusion_state",
                "recovery_manifest",
                "recovery_manifest_state",
                "responsible_index",
                "frontmatter_changes",
                "planned_changes",
            },
            "external_link": {
                "applied",
                "install_id",
                "install_path",
                "source_path",
                "target_path",
                "presentation_path",
                "working_path",
                "repository_relative_path",
                "source_url",
                "source_relation",
                "revision_selector",
                "default_branch",
                "resolved_commit",
                "safe_state",
                "symlink_tracking",
                "responsible_index",
                "frontmatter_changes",
                "recovery_manifest",
                "recovery_manifest_state",
                "planned_changes",
            },
            "external_restore": {
                "applied",
                "recovery_manifest",
                "recovery_manifest_identity",
                "install_filter",
                "items",
            },
            "external_remove": {
                "applied",
                "install_id",
                "install_role",
                "install_path",
                "manifest_included",
                "state",
                "planned_changes",
            },
            "external_link_parse": {
                "managed",
                "mapping_origin",
                "created_by",
                "content_root",
                "input_path",
                "input_kind",
                "presentation_path",
                "install_id",
                "install_path",
                "install_role",
                "dependency_of",
                "dependency_parent_install_id",
                "target_state",
                "source_url",
                "source_relation",
                "revision_selector",
                "default_branch",
                "resolved_commit",
                "repository_relative_path",
                "working_path",
                "safe_state",
                "responsible_index",
            },
            "worktree_open": {"worktree", "reuse_candidate_count"},
            "worktree_list": {"items"},
            "worktree_close": {"worktree"},
            "cache_clean": {
                "applied",
                "source_url",
                "cache_source_id",
                "linked_worktree_count",
                "valid_worktree_count",
                "prunable_worktree_count",
                "state",
            },
        }.get(payload["operation"], set())
        assert required <= payload.keys()
    return payload


@pytest.fixture
def cli_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DOCTIDEX_GIT_CACHE"] = str(tmp_path / "cache")
    return env


@pytest.fixture
def symlink_capable(tmp_path: Path) -> None:
    target = tmp_path / "symlink-target"
    link = tmp_path / "symlink-probe"
    target.mkdir()
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("This environment cannot create directory symlinks")
    else:
        link.unlink()


def create_repository(path: Path, *, nested_root: str | None = None) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.email", "tests@example.invalid")
    git(path, "config", "user.name", "Tests")
    root = path / nested_root if nested_root else path
    root.mkdir(parents=True, exist_ok=True)
    unsafe_git = "" if nested_root else "  unsafe:\n    - path: .git\n"
    git_link = "" if nested_root else "\n[Git metadata](.git)\n<!-- doctidex: {unsafe: true} -->\n"
    (root / "index.md").write_text(
        f"""---
type: index
doctidex:
  type: index
  root: true
{unsafe_git}---
# Root
{git_link}
""",
        encoding="utf-8",
    )
    git(path, "add", ".")
    git(path, "commit", "-m", "initial")
    return root


def add_source_content(repository: Path, name: str = "guide.md") -> str:
    (repository / name).write_text(f"# {name}\n", encoding="utf-8")
    index = repository / "index.md"
    content = index.read_text(encoding="utf-8")
    content += f"\n[{name}]({name})\n"
    index.write_text(content, encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", f"add {name}")
    return git(repository, "rev-parse", "HEAD")


def test_parser_rejects_old_surface_with_json(cli_env: dict[str, str], tmp_path: Path) -> None:
    payload = run(["mount", "list"], tmp_path, cli_env, expected=2)
    assert payload["operation"] == "command"
    assert payload["findings"][0]["code"] == "argument_invalid"
    duplicate = run(["validate", "--json"], tmp_path, cli_env, expected=2)
    assert duplicate["findings"][0]["code"] == "argument_invalid"


def test_validate_cli_and_nested_host_gitignore(cli_env: dict[str, str], tmp_path: Path) -> None:
    host = tmp_path / "host"
    root = create_repository(host, nested_root="docs")
    source = create_repository(tmp_path / "source")
    add_source_content(source)

    result = run(["validate", str(root)], tmp_path, cli_env)
    assert result["operation"] == "validate"
    dry = run(["external", "install", "--url", str(source), "--root", str(root)], tmp_path, cli_env)
    assert dry["applied"] is False
    assert not (root / ".doctidex").exists()
    assert str(host / ".gitignore") in dry["planned_changes"]
    assert str(root / ".gitignore") not in dry["planned_changes"]
    applied = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    assert applied["applied"] is True
    assert applied["resolved_commit"] == git(source, "rev-parse", "HEAD")
    assert applied["install_path"].startswith("/.doctidex/git/installs/")
    assert Path(applied["working_path"]).is_dir()
    ignore = (host / ".gitignore").read_text(encoding="utf-8")
    assert "/docs/.doctidex/git/installs/" in ignore
    assert (root / ".doctidex" / "git" / "manifest.json").is_file()


def test_default_revision_is_fixed_and_self_dependency_is_bounded(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    first_commit = add_source_content(source, "first.md")
    first = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    add_source_content(source, "second.md")
    repeated = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    assert repeated["install_id"] == first["install_id"]
    assert repeated["resolved_commit"] == first_commit
    dependency = run(
        [
            "external",
            "install",
            "--url",
            str(source),
            "--root",
            str(root),
            "--dependency-of",
            first["install_id"],
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    assert dependency["install_id"] == first["install_id"]
    assert dependency["install_role"] == "direct"
    assert dependency["dependency_of"]["items"] == [first["install_id"]]


def test_explicit_branch_retry_stays_fixed_and_root_is_part_of_identity(
    cli_env: dict[str, str], tmp_path: Path
) -> None:
    first_root = create_repository(tmp_path / "first-host")
    second_root = create_repository(tmp_path / "second-host")
    source = create_repository(tmp_path / "source")
    first_commit = add_source_content(source, "first.md")
    command = ["external", "install", "--url", str(source), "--branch", "main"]
    first = run([*command, "--root", str(first_root), "--apply"], tmp_path, cli_env)
    add_source_content(source, "second.md")
    repeated = run([*command, "--root", str(first_root), "--apply"], tmp_path, cli_env)
    other_root = run([*command, "--root", str(second_root)], tmp_path, cli_env)
    assert repeated["install_id"] == first["install_id"]
    assert repeated["resolved_commit"] == first_commit
    assert repeated["network"] is False
    assert other_root["install_id"] != first["install_id"]
    assert not Path(first["working_path"]).stat().st_mode & stat.S_IWUSR


def test_different_selectors_keep_distinct_install_paths(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    git(source, "tag", "v1")

    branch = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--branch", "main", "--apply"],
        tmp_path,
        cli_env,
    )
    tag = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--tag", "v1", "--apply"],
        tmp_path,
        cli_env,
    )
    assert branch["resolved_commit"] == tag["resolved_commit"] == commit
    assert branch["install_id"] != tag["install_id"]
    assert branch["install_path"] != tag["install_path"]


def test_missing_revision_is_blocked_without_creating_root_state(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    result = run(
        [
            "external",
            "install",
            "--url",
            str(source),
            "--root",
            str(root),
            "--commit",
            "0" * 40,
        ],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert result["findings"][0]["code"] == "revision_not_found"
    assert not (root / ".doctidex").exists()


def test_install_blocks_an_ignored_recovery_manifest(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    (root / ".gitignore").write_text("/.doctidex/\n", encoding="utf-8")
    result = run(
        ["external", "install", "--url", str(source), "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert result["findings"][0]["code"] == "git_exclusion_conflict"
    assert not (root / ".doctidex").exists()


def test_link_restore_and_current_owner_parse(cli_env: dict[str, str], tmp_path: Path, symlink_capable: None) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    link = run(
        [
            "external",
            "link",
            install["working_path"],
            "external/source",
            "--root",
            str(root),
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    presentation = Path(link["presentation_path"])
    assert presentation.is_symlink()
    parsed = run(["external", "link-parse", str(presentation), "--root", str(root)], tmp_path, cli_env)
    assert parsed["mapping_origin"] == "owner_root"
    assert parsed["target_state"] == "available"

    cache_gitdir = Path(install["working_path"]) / ".git"
    common = Path(git(Path(install["working_path"]), "rev-parse", "--path-format=absolute", "--git-common-dir"))
    assert cache_gitdir.exists()
    make_writable(Path(install["working_path"]))
    git(common, "worktree", "remove", "--force", install["working_path"])
    assert presentation.is_symlink() and not presentation.exists()
    missing = run(["external", "link-parse", str(presentation), "--root", str(root)], tmp_path, cli_env)
    assert missing["target_state"] == "owner_install_missing"
    restored = run(["external", "restore", "--root", str(root), "--apply"], tmp_path, cli_env)
    assert restored["items"][0]["state"] == "restored"
    assert presentation.exists()
    restored_parse = run(["external", "link-parse", str(presentation), "--root", str(root)], tmp_path, cli_env)
    assert restored_parse["mapping_origin"] == "owner_root"
    assert restored_parse["target_state"] == "available"


def test_external_remove_direct_dry_run_apply_and_cache(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", source.as_uri(), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    cache = Path(cli_env["DOCTIDEX_GIT_CACHE"]) / "sources"
    assert any(cache.iterdir())
    parsed = run(["external", "link-parse", install["working_path"], "--root", str(root)], tmp_path, cli_env)
    assert parsed["install_id"] == install["install_id"]

    index_before = (root / "index.md").read_bytes()
    ignore_before = (root / ".gitignore").read_bytes()
    planned = run(
        ["external", "remove", parsed["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
    )
    assert planned["state"] == "planned"
    assert planned["applied"] is False
    assert Path(install["working_path"]).is_dir()
    assert install["install_id"] in RootStorage(root).read_runtime()["installs"]

    removed = run(
        ["external", "remove", parsed["install_id"], "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    assert removed["state"] == "removed"
    assert removed["manifest_included"] is True
    assert not Path(install["working_path"]).exists()
    assert install["install_id"] not in RootStorage(root).read_runtime()["installs"]
    assert install["install_id"] not in RootStorage(root).read_manifest()["installs"]
    assert (root / "index.md").read_bytes() == index_before
    assert (root / ".gitignore").read_bytes() == ignore_before
    assert any(cache.iterdir())

    unknown = run(
        ["external", "remove", "i-missing", "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert unknown["findings"][0]["code"] == "install_not_found"
    assert "link-parse" in unknown["findings"][0]["actions"][0]


def test_external_remove_dependency_and_reference_blocks(
    cli_env: dict[str, str], tmp_path: Path, symlink_capable: None
) -> None:
    root = create_repository(tmp_path / "host")
    parent_source = create_repository(tmp_path / "parent-source")
    dependency_source = create_repository(tmp_path / "dependency-source")
    add_source_content(parent_source)
    add_source_content(dependency_source)
    parent = run(
        ["external", "install", "--url", str(parent_source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    dependency = run(
        [
            "external",
            "install",
            "--url",
            str(dependency_source),
            "--root",
            str(root),
            "--dependency-of",
            parent["install_id"],
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    dependency_removed = run(
        ["external", "remove", dependency["install_id"], "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    assert dependency_removed["manifest_included"] is False
    assert dependency["install_id"] not in RootStorage(root).read_runtime()["installs"]
    assert parent["install_id"] in RootStorage(root).read_runtime()["installs"]

    mapped_source = create_repository(tmp_path / "mapped-source")
    add_source_content(mapped_source)
    mapped = run(
        ["external", "install", "--url", str(mapped_source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    run(
        [
            "external",
            "link",
            mapped["working_path"],
            "external/mapped",
            "--root",
            str(root),
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    mapping_blocked = run(
        ["external", "remove", mapped["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert {item["code"] for item in mapping_blocked["findings"]} == {"install_referenced"}
    assert any("runtime.json#links/external/mapped" in value for value in mapping_blocked["affected"])
    assert Path(mapped["working_path"]).is_dir()

    markdown_source = create_repository(tmp_path / "markdown-source")
    add_source_content(markdown_source)
    markdown = run(
        ["external", "install", "--url", str(markdown_source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    with (root / "index.md").open("a", encoding="utf-8") as index:
        index.write(f"\n[Managed payload]({markdown['install_path']}/guide.md)\n")
    markdown_blocked = run(
        ["external", "remove", markdown["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert str(root / "index.md") in markdown_blocked["affected"]
    assert Path(markdown["working_path"]).is_dir()

    symlink_source = create_repository(tmp_path / "symlink-source")
    add_source_content(symlink_source)
    symlinked = run(
        ["external", "install", "--url", str(symlink_source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    manual = root / "manual-payload"
    manual.symlink_to(Path(symlinked["working_path"]), target_is_directory=True)
    symlink_blocked = run(
        ["external", "remove", symlinked["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert str(manual) in symlink_blocked["affected"]
    assert Path(symlinked["working_path"]).is_dir()

    parent_edge_source = create_repository(tmp_path / "parent-edge-source")
    child_source = create_repository(tmp_path / "child-source")
    add_source_content(parent_edge_source)
    add_source_content(child_source)
    parent_edge = run(
        ["external", "install", "--url", str(parent_edge_source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    run(
        [
            "external",
            "install",
            "--url",
            str(child_source),
            "--root",
            str(root),
            "--dependency-of",
            parent_edge["install_id"],
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    parent_blocked = run(
        ["external", "remove", parent_edge["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert any("/parents" in value for value in parent_blocked["affected"])


def test_external_remove_excludes_unsafe_boundary_and_install_payload(
    cli_env: dict[str, str], tmp_path: Path, symlink_capable: None
) -> None:
    root = create_repository(tmp_path / "host")
    index = root / "index.md"
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "  unsafe:\n    - path: .git\n",
            "  boundary-set:\n    - path: boundary\n"
            "  unsafe:\n    - path: .git\n    - path: unsafe\n",
        ),
        encoding="utf-8",
    )
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    for name in ("unsafe", "boundary"):
        directory = root / name
        directory.mkdir()
        (directory / "reference.md").write_text(
            f"[Managed payload]({install['install_path']}/guide.md)\n", encoding="utf-8"
        )
        (directory / "manual-payload").symlink_to(Path(install["working_path"]), target_is_directory=True)

    removed = run(
        ["external", "remove", install["install_id"], "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    assert removed["state"] == "removed"
    assert not Path(install["working_path"]).exists()


def test_external_remove_retry_completes_after_payload_deletion(
    cli_env: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCTIDEX_GIT_CACHE", cli_env["DOCTIDEX_GIT_CACHE"])
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    context = root_at(root)
    assert context is not None
    service = ExternalService(context)

    def interrupted(callback: object) -> dict:
        raise KeyboardInterrupt

    monkeypatch.setattr(service.storage, "update_runtime", interrupted)
    with pytest.raises(KeyboardInterrupt):
        service.remove(install["install_id"], apply=True)
    assert not Path(install["working_path"]).exists()
    assert install["install_id"] in RootStorage(root).read_runtime()["installs"]
    assert install["install_id"] not in RootStorage(root).read_manifest()["installs"]

    retried = ExternalService(context).remove(install["install_id"], apply=True)
    assert retried["state"] == "removed"
    assert install["install_id"] not in RootStorage(root).read_runtime()["installs"]


def test_external_remove_preserves_a_damaged_direct_manifest(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    manifest_path = root / ".doctidex" / "git" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["installs"][install["install_id"]]["resolved_commit"] = "f" * 40
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    blocked = run(
        ["external", "remove", install["install_id"], "--root", str(root)],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert blocked["operation"] == "external_remove"
    assert blocked["findings"][0]["code"] == "mapping_damaged"
    assert Path(install["working_path"]).is_dir()


@pytest.mark.parametrize("explicit_selector", [False, True])
def test_restore_rebuilds_requested_default_provenance(
    cli_env: dict[str, str], tmp_path: Path, explicit_selector: bool
) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    original_commit = add_source_content(source)
    install_command = ["external", "install", "--url", str(source), "--root", str(root)]
    if explicit_selector:
        install_command.extend(["--commit", original_commit])
    install = run([*install_command, "--apply"], tmp_path, cli_env)

    install_path = Path(install["working_path"])
    common = Path(git(install_path, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    make_writable(install_path)
    git(common, "worktree", "remove", "--force", str(install_path))

    restored = run(["external", "restore", "--root", str(root), "--apply"], tmp_path, cli_env)
    assert restored["items"][0]["state"] == "restored"
    runtime_install = RootStorage(root).read_runtime()["installs"][install["install_id"]]
    assert runtime_install["requested_default"] is not explicit_selector
    assert runtime_install["revision_selector"] == install["revision_selector"]
    assert runtime_install["resolved_commit"] == original_commit

    if not explicit_selector:
        add_source_content(source, "later.md")
    retried = run(install_command, tmp_path, cli_env)
    assert retried["install_id"] == install["install_id"]
    assert retried["resolved_commit"] == original_commit


def test_portable_broken_link_dependency_can_be_flattened(
    cli_env: dict[str, str], tmp_path: Path, symlink_capable: None
) -> None:
    dependency = create_repository(tmp_path / "dependency")
    dependency_commit = add_source_content(dependency, "dependency.md")
    parent = create_repository(tmp_path / "parent")
    parent_install = run(
        ["external", "install", "--url", str(dependency), "--root", str(parent), "--apply"],
        tmp_path,
        cli_env,
    )
    run(
        [
            "external",
            "link",
            parent_install["working_path"],
            "external/dependency",
            "--root",
            str(parent),
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    git(parent, "add", "index.md", ".gitignore", ".doctidex/git/manifest.json", "external/dependency")
    git(parent, "commit", "-m", "record portable dependency")

    host = create_repository(tmp_path / "host")
    host_parent = run(
        ["external", "install", "--url", str(parent), "--root", str(host), "--apply"],
        tmp_path,
        cli_env,
    )
    portable_link = Path(host_parent["working_path"]) / "external" / "dependency"
    assert portable_link.is_symlink() and not portable_link.exists()
    wrong_root = run(
        ["external", "link-parse", str(portable_link), "--root", host_parent["working_path"]],
        tmp_path,
        cli_env,
        expected=2,
    )
    assert wrong_root["findings"][0]["code"] == "root_mismatch"
    missing = run(["external", "link-parse", str(portable_link), "--root", str(host)], tmp_path, cli_env)
    assert missing["mapping_origin"] == "installed_repository"
    assert missing["target_state"] == "dependency_not_installed"
    assert missing["resolved_commit"] == dependency_commit

    run(
        [
            "external",
            "install",
            "--url",
            missing["source_url"],
            "--root",
            str(host),
            "--commit",
            missing["resolved_commit"],
            "--dependency-of",
            missing["dependency_parent_install_id"],
            "--apply",
        ],
        tmp_path,
        cli_env,
    )
    available = run(["external", "link-parse", str(portable_link), "--root", str(host)], tmp_path, cli_env)
    assert available["target_state"] == "available"
    assert Path(available["working_path"]).is_dir()
    assert portable_link.is_symlink() and not portable_link.exists()


def test_worktree_dirty_preservation_and_close(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    opened = run(
        ["worktree", "open", str(source), "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    path = Path(opened["worktree"]["worktree_path"])
    assert path.is_dir()
    (path / "changed.md").write_text("changed", encoding="utf-8")
    listed = run(["worktree", "list", "--root", str(root)], tmp_path, cli_env)
    assert listed["items"][0]["state"] == "changed"
    blocked = run(["worktree", "close", str(path)], tmp_path, cli_env, expected=2)
    assert blocked["findings"][0]["code"] == "worktree_changed"
    assert blocked["worktree"]["state"] == "changed"
    assert path.is_dir()
    (path / "changed.md").unlink()
    closed = run(["worktree", "close", str(path)], tmp_path, cli_env)
    assert str(path) in closed["changed"]
    assert not path.exists()


def test_cache_cleanup_preserves_active_then_removes_eligible(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    opened = run(
        ["worktree", "open", str(source), "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    # Local working-tree sources do not use the shared cache; open the same source as a file URL.
    url = source.as_uri()
    remote_open = run(
        ["worktree", "open", url, "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    active = run(["cache", "clean", "--url", url], tmp_path, cli_env)
    assert active["state"] == "preserved"
    assert active["valid_worktree_count"] == 1
    run(["worktree", "close", remote_open["worktree"]["worktree_path"]], tmp_path, cli_env)
    planned = run(["cache", "clean", "--url", url], tmp_path, cli_env)
    assert planned["state"] == "planned"
    removed = run(["cache", "clean", "--url", url, "--apply"], tmp_path, cli_env)
    assert removed["state"] == "removed"
    assert removed["changed"] == []
    repeated = run(["cache", "clean", "--url", url], tmp_path, cli_env, expected=2)
    assert repeated["findings"][0]["code"] == "cache_source_not_found"
    run(["worktree", "close", opened["worktree"]["worktree_path"]], tmp_path, cli_env)


def test_cache_cleanup_accepts_prunable_registration(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    url = source.as_uri()
    opened = run(
        ["worktree", "open", url, "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    shutil.rmtree(opened["worktree"]["worktree_path"])
    planned = run(["cache", "clean", "--url", url], tmp_path, cli_env)
    assert planned["state"] == "planned"
    assert planned["linked_worktree_count"] == planned["prunable_worktree_count"] == 1


def test_manifest_rejects_duplicate_and_inconsistent_portable_facts(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    manifest = root / ".doctidex" / "git" / "manifest.json"
    original = manifest.read_text(encoding="utf-8")
    manifest.write_text('{"schema_version":"1.0","schema_version":"1.0","installs":{},"links":{}}\n')
    duplicate = run(["external", "restore", "--root", str(root)], tmp_path, cli_env, expected=2)
    assert duplicate["findings"][0]["code"] == "recovery_manifest_invalid"

    payload = json.loads(original)
    payload["installs"][install["install_id"]]["install_path"] = "/.doctidex/git/installs/other"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    inconsistent = run(["external", "restore", "--root", str(root)], tmp_path, cli_env, expected=2)
    assert inconsistent["findings"][0]["code"] == "recovery_manifest_invalid"


def test_link_retry_rejects_a_changed_symlink_target(
    cli_env: dict[str, str], tmp_path: Path, symlink_capable: None
) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    command = [
        "external",
        "link",
        install["working_path"],
        "external/source",
        "--root",
        str(root),
        "--apply",
    ]
    linked = run(command, tmp_path, cli_env)
    presentation = Path(linked["presentation_path"])
    presentation.unlink()
    presentation.symlink_to("../wrong", target_is_directory=True)

    damaged = run(command, tmp_path, cli_env, expected=2)
    assert damaged["findings"][0]["code"] == "mapping_damaged"
    assert os.readlink(presentation) == "../wrong"


def test_link_classifies_only_a_complete_doctidex_root_as_safe(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    (source / "section").mkdir()
    (source / "section" / "readme.md").write_text("section\n", encoding="utf-8")
    with (source / "index.md").open("a", encoding="utf-8") as index:
        index.write("\n[Section](section/readme.md)\n")
    git(source, "add", "index.md", "section")
    git(source, "commit", "-m", "add section")
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    safe = run(
        ["external", "link", install["working_path"], "external/root", "--root", str(root)],
        tmp_path,
        cli_env,
    )
    unsafe = run(
        [
            "external",
            "link",
            str(Path(install["working_path"]) / "section"),
            "external/section",
            "--root",
            str(root),
        ],
        tmp_path,
        cli_env,
    )
    assert safe["safe_state"] == "safe"
    assert unsafe["safe_state"] == "unsafe"
    assert unsafe["repository_relative_path"] == "section"


def test_restore_preserves_blocked_item_and_restores_other_item(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    installs = []
    for name in ("first", "second"):
        source = create_repository(tmp_path / name)
        add_source_content(source)
        installs.append(
            run(
                ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
                tmp_path,
                cli_env,
            )
        )
    for install in installs:
        path = Path(install["working_path"])
        common = Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        make_writable(path)
        git(common, "worktree", "remove", "--force", str(path))

    conflict = Path(installs[0]["working_path"])
    conflict.mkdir(parents=True)
    (conflict / "owned.txt").write_text("preserve", encoding="utf-8")
    restored = run(["external", "restore", "--root", str(root), "--apply"], tmp_path, cli_env)
    states = {item["install_id"]: item["state"] for item in restored["items"]}
    assert states[installs[0]["install_id"]] == "blocked"
    assert states[installs[1]["install_id"]] == "restored"
    assert restored["status"] == "warning"
    assert (conflict / "owned.txt").read_text(encoding="utf-8") == "preserve"
    assert Path(installs[1]["working_path"]).is_dir()


def test_worktree_open_accepts_a_linked_worktree_gitfile(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    linked = tmp_path / "linked-source"
    git(source, "worktree", "add", "--detach", str(linked), commit)
    assert (linked / ".git").is_file()

    opened = run(
        ["worktree", "open", str(linked / ".git"), "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    assert opened["worktree"]["source_kind"] == "gitfile"
    assert Path(opened["worktree"]["worktree_path"]).is_dir()
    run(["worktree", "close", opened["worktree"]["worktree_path"]], tmp_path, cli_env)


def test_unrecorded_worktree_namespace_path_is_preserved(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    orphan = root / ".doctidex" / "git" / "worktrees" / "w-orphan"
    orphan.mkdir(parents=True)

    listed = run(["worktree", "list", "--root", str(root)], tmp_path, cli_env)
    assert listed["items"] == []
    blocked = run(["worktree", "close", str(orphan)], tmp_path, cli_env, expected=2)
    assert blocked["findings"][0]["code"] == "worktree_unmanaged"
    assert orphan.is_dir()


def test_link_reports_symlink_unsupported_before_persistent_changes(
    cli_env: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    index = root / "index.md"
    manifest = root / ".doctidex" / "git" / "manifest.json"
    before_index = index.read_bytes()
    before_manifest = manifest.read_bytes()
    context = root_at(root)
    assert context is not None

    def unsupported(*args: object, **kwargs: object) -> None:
        raise OSError("symlinks disabled")

    monkeypatch.setattr(Path, "symlink_to", unsupported)
    with pytest.raises(DoctidexError) as caught:
        ExternalService(context).link(Path(install["working_path"]), "external/source", apply=True)
    assert getattr(caught.value, "code", None) == "symlink_unsupported"
    assert index.read_bytes() == before_index
    assert manifest.read_bytes() == before_manifest
    assert not (root / "external" / "source").exists()


def test_root_lock_conflict_is_bounded_and_preserves_owner(tmp_path: Path) -> None:
    lock = tmp_path / "mutation.lock"
    with directory_lock(lock, operation="first", timeout=0.01):
        with pytest.raises(DoctidexError) as caught:
            with directory_lock(lock, operation="second", timeout=0.01):
                pass
        assert caught.value.code == "index_update_conflict"
        assert lock.is_dir()
    assert not lock.exists()


def test_interrupted_worktree_publication_leaves_orphan_evidence(
    cli_env: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOCTIDEX_GIT_CACHE", cli_env["DOCTIDEX_GIT_CACHE"])
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    context = root_at(root)
    assert context is not None
    service = WorktreeService(context)

    def interrupted(callback: object) -> dict:
        raise KeyboardInterrupt

    monkeypatch.setattr(service.storage, "update_runtime", interrupted)
    with pytest.raises(KeyboardInterrupt):
        service.open(str(source), RevisionSelector("commit", commit))

    orphans = list(RootStorage(root).worktree_directory.glob("w-*"))
    assert len(orphans) == 1
    assert orphans[0].is_dir()
    assert RootStorage(root).read_runtime()["worktrees"] == {}
    common = Path(git(source, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    git(common, "worktree", "remove", "--force", str(orphans[0]))


def test_worktree_source_kinds_managed_bare_and_submodule(cli_env: dict[str, str], tmp_path: Path) -> None:
    root = create_repository(tmp_path / "host")
    source = create_repository(tmp_path / "source")
    commit = add_source_content(source)
    install = run(
        ["external", "install", "--url", str(source), "--root", str(root), "--apply"],
        tmp_path,
        cli_env,
    )
    managed = run(
        ["worktree", "open", install["working_path"], "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    assert managed["worktree"]["source_kind"] == "managed_path"

    bare = tmp_path / "source.git"
    git(tmp_path, "clone", "--bare", str(source), str(bare))
    bare_open = run(
        ["worktree", "open", str(bare), "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    assert bare_open["worktree"]["source_kind"] == "bare_gitdir"

    parent = create_repository(tmp_path / "parent")
    git(parent, "-c", "protocol.file.allow=always", "submodule", "add", str(source), "dependency")
    git(parent, "commit", "-am", "add submodule")
    submodule_open = run(
        ["worktree", "open", str(parent / "dependency"), "--root", str(root), "--commit", commit],
        tmp_path,
        cli_env,
    )
    assert submodule_open["worktree"]["source_kind"] == "working_tree"

    for opened in (managed, bare_open, submodule_open):
        run(["worktree", "close", opened["worktree"]["worktree_path"]], tmp_path, cli_env)
