from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from conftest import (
    CliRunner,
    commit_file,
    git,
    git_head,
    make_git_repository,
    read_json,
    write_json,
    write_residual_journal,
)

from whero.doctidex.errors import CommandFailure
from whero.doctidex.installation import (
    InstallationRuntimeStore,
    resolve_installation_context_by_id,
    resolve_owner_root_from_path,
)


def test_default_worktree_path_is_not_installation_context(
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
        "--tree-name",
        "managed",
    )
    worktree_root = initialized_root / created.payload["work-path"].lstrip("/")

    initialized = cli.run("--repos-path", str(worktree_root), "init")

    assert initialized.code == 0
    assert (worktree_root / ".doctidex-git").is_dir()


def test_custom_worktree_under_workspace_is_not_installation_context(
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
        "/.doctidex-git/custom-work",
    )
    worktree_root = initialized_root / created.payload["work-path"].lstrip("/")

    initialized = cli.run("--repos-path", str(worktree_root), "init")

    assert initialized.code == 0
    assert (worktree_root / ".doctidex-git").is_dir()


def test_worktree_path_with_invalid_owner_model_fails_without_initializing(
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
        "--tree-name",
        "invalid-owner",
    )
    worktree_root = initialized_root / created.payload["work-path"].lstrip("/")
    (initialized_root / ".doctidex-git" / "runtime.json").unlink()

    failed = cli.run("--repos-path", str(worktree_root), "init")

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "work-model.invalid"
    assert failed.payload["message"]["details"] == {
        "owner-path": str(initialized_root),
        "reason": "owner-work-model-invalid",
        "artifact": "runtime.json",
        "expected": "a required state file",
    }
    assert not (worktree_root / ".doctidex-git").exists()


def test_worktree_path_with_pending_owner_journal_fails_without_initializing(
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
        "--tree-name",
        "pending-owner",
    )
    worktree_root = initialized_root / created.payload["work-path"].lstrip("/")
    write_residual_journal(initialized_root, state="prepared")

    failed = cli.run("--repos-path", str(worktree_root), "init")

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "store.transaction.unavailable"
    assert not (worktree_root / ".doctidex-git").exists()


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
    install_id = installed.payload["install-id"]
    installation_root = initialized_root / installed.payload["install-path"].lstrip("/")

    forbidden = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        install_id,
        "init",
    )
    assert forbidden.code == 2
    assert forbidden.payload["message"]["code"] == "installation.context.forbidden"
    assert forbidden.payload["message"]["subject"] == {
        "kind": "installation",
        "install-path": installed.payload["install-path"],
    }
    assert not (installation_root / ".doctidex-git").exists()

    validated = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        install_id,
        "validate",
        "--only-model-structure",
    )
    assert validated.code == 1
    assert validated.payload["status"] == "ok"
    assert validated.payload["valid"] is False
    assert validated.payload["message"] == {}


def test_path_detected_installation_without_argument_requires_explicit_context(
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

    failed = cli.run("--repos-path", str(installation_root), "init")

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "installation.context.argument-required"
    assert failed.payload["message"]["details"]["required-argument"] == "--installation-context"
    assert not (installation_root / ".doctidex-git").exists()


def test_installation_runtime_store_exposes_only_read_only_transaction_surface(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    workspace = source_repository / ".doctidex-git"
    write_json(workspace / "boundary-set.json", [])
    write_json(workspace / "import-refs.json", [])
    write_json(
        workspace / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [], "branch-snapshots": {}},
    )
    write_json(workspace / "imports.json", [])
    assert git(source_repository, "add", ".doctidex-git").returncode == 0
    assert git(source_repository, "commit", "--quiet", "-m", "workspace").returncode == 0

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
    install_id = installed.payload["install-id"]

    context = resolve_installation_context_by_id(initialized_root, install_id)
    assert context.install_path == installed.payload["install-path"]

    store = InstallationRuntimeStore(context)
    with store.read_only_transaction() as transaction:
        assert transaction.model_view() is not None
    with pytest.raises(AttributeError):
        _ = store.write_transaction


def test_installation_context_by_id_works_for_shared_branch_tag_and_commit_paths(
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
    commit = cli.run(
        "--repos-path",
        str(initialized_root),
        "import",
        "install",
        "--untracked",
        "--url",
        str(source_repository),
        "--commit",
        git_head(source_repository),
    )

    for install_id in (
        branch.payload["install-id"],
        tag.payload["install-id"],
        commit.payload["install-id"],
    ):
        validated = cli.run(
            "--repos-path",
            str(initialized_root),
            "--installation-context",
            install_id,
            "validate",
            "--only-model-structure",
        )
        assert validated.code == 1
        assert validated.payload["valid"] is False


def test_unknown_installation_context_id_fails_before_mutation(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    failed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        "missing-id",
        "validate",
        "--only-model-structure",
    )

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "installation.not-found"
    assert failed.payload["message"]["details"]["install-id"] == "missing-id"


def test_installation_context_rejects_not_restored_tracked_installation(
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
        "--commit",
        git_head(source_repository),
    )
    install_path = initialized_root / installed.payload["install-path"].lstrip("/")
    shutil.rmtree(install_path)

    failed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed.payload["install-id"],
        "validate",
        "--only-model-structure",
    )

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "installation.restore.required"
    assert failed.payload["message"]["details"]["install-id"] == installed.payload["install-id"]


def test_installation_context_rejects_missing_untracked_installation(
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
        "--commit",
        git_head(source_repository),
    )
    install_path = initialized_root / installed.payload["install-path"].lstrip("/")
    shutil.rmtree(install_path)

    failed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed.payload["install-id"],
        "validate",
        "--only-model-structure",
    )

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "installation.context.unavailable"
    assert failed.payload["message"]["details"]["reason"] == "installation-missing"


def test_available_installation_with_missing_local_workspace_reports_context_unavailable(
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

    failed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed.payload["install-id"],
        "import",
        "query",
        "--install-id",
        "missing-local",
    )

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "installation.context.unavailable"
    assert failed.payload["message"]["details"]["reason"] == "declarations-invalid"


def test_available_installation_with_malformed_local_workspace_reports_work_model_invalid(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    workspace = source_repository / ".doctidex-git"
    write_json(workspace / "boundary-set.json", [])
    write_json(workspace / "import-refs.json", [])
    write_json(
        workspace / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [], "branch-snapshots": {}},
    )
    write_json(workspace / "imports.json", [])
    assert git(source_repository, "add", ".doctidex-git").returncode == 0
    assert git(source_repository, "commit", "--quiet", "-m", "workspace").returncode == 0

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
    (installation_root / ".doctidex-git" / "runtime.json").write_text("{not valid json\n")

    failed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed.payload["install-id"],
        "import",
        "query",
        "--install-id",
        "missing-local",
    )

    assert failed.code == 2
    assert failed.payload["message"]["code"] == "work-model.invalid"


def test_installation_context_id_discovers_owner_root_from_current_directory(
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
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
    monkeypatch.chdir(installation_root)

    validated = cli.run(
        "--installation-context",
        installed.payload["install-id"],
        "validate",
        "--only-model-structure",
    )

    assert validated.code == 1
    assert validated.payload["valid"] is False


def test_owner_root_candidate_rule_rejects_zero_and_multiple_candidates(tmp_path: Path) -> None:
    zero_candidates = tmp_path / "plain" / "directory"
    zero_candidates.mkdir(parents=True)
    with pytest.raises(CommandFailure) as zero_error:
        resolve_owner_root_from_path(zero_candidates)
    assert zero_error.value.code == "installation.context.owner-required"

    multiple_candidates = (
        tmp_path / "outer" / ".doctidex-git" / "inner" / ".doctidex-git" / "leaf"
    )
    multiple_candidates.mkdir(parents=True)
    with pytest.raises(CommandFailure) as multiple_error:
        resolve_owner_root_from_path(multiple_candidates)
    assert multiple_error.value.code == "installation.owner.ambiguous"


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
    write_json(
        workspace / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [], "branch-snapshots": {}},
    )
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
    installed_id = installed.payload["install-id"]

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed_id,
        "boundary-set",
        "parse",
        "--path",
        "/readme.md",
    )
    assert parsed.code == 0
    assert parsed.payload["results"] == [{"path": "/readme.md", "has-boundary": False}]

    queried = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed_id,
        "import",
        "query",
        "--install-id",
        "nested-id",
    )
    candidate = queried.payload["candidates"][0]
    assert candidate["install-id"] == "nested-id"
    assert candidate["install-path"] == "/.doctidex-git/imports/nested"
    assert "presentation-path" not in candidate
    assert candidate["restore-state"] == "restore-required"

    restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed_id,
        "import",
        "restore",
        "--install-id",
        "nested-id",
    )
    assert restored.code == 0
    assert restored.payload["install-id"] == "nested-id"
    assert restored.payload["install-path"] == "/.doctidex-git/imports/nested"
    assert Path(restored.payload["presentation-path"]).is_dir()
    assert restored.payload["presentation-install-id"] == owner_nested.payload["install-id"]

    queried_after_restore = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        installed_id,
        "import",
        "query",
        "--install-id",
        "nested-id",
    )
    restored_candidate = queried_after_restore.payload["candidates"][0]
    assert restored_candidate["presentation-path"] == str(
        initialized_root / owner_nested.payload["install-path"].lstrip("/")
    )
    assert restored_candidate["presentation-install-id"] == owner_nested.payload["install-id"]
    assert restored_candidate["restore-state"] == "available"

    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert all(item["install-id"] != "nested-id" for item in runtime["imports"])
    share = runtime["installation-shares"][0]
    assert "nested-id" not in share["install-ids"]
    assert any(
        reference["install-id"] == "nested-id"
        and reference["owner-install-id"] == installed_id
        for reference in share["context-references"]
    )


def test_installation_context_crosses_presentation_installation_owner(
    tmp_path: Path,
    initialized_root: Path,
    source_repository: Path,
    cache_home: Path,
    cli: CliRunner,
) -> None:
    grandchild_source = make_git_repository(tmp_path / "grandchild-source")
    grandchild_commit = commit_file(grandchild_source, "readme.md", "grandchild\n")

    child_source = make_git_repository(tmp_path / "child-source")
    child_workspace = child_source / ".doctidex-git"
    write_json(child_workspace / "boundary-set.json", [])
    write_json(child_workspace / "import-refs.json", [])
    write_json(
        child_workspace / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [], "branch-snapshots": {}},
    )
    write_json(
        child_workspace / "imports.json",
        [
            {
                "tracked": True,
                "git-url": str(grandchild_source),
                "commit-hash": grandchild_commit,
                "install-id": "grandchild-id",
                "install-path": "/.doctidex-git/imports/grandchild",
                "keys": ["grandchild"],
                "branch": "main",
                "tag": "",
            }
        ],
    )
    assert git(child_source, "add", ".doctidex-git").returncode == 0
    assert git(child_source, "commit", "--quiet", "-m", "child workspace").returncode == 0

    parent_workspace = source_repository / ".doctidex-git"
    write_json(parent_workspace / "boundary-set.json", [])
    write_json(parent_workspace / "import-refs.json", [])
    write_json(
        parent_workspace / "runtime.json",
        {"imports": [], "worktrees": [], "installation-shares": [], "branch-snapshots": {}},
    )
    write_json(
        parent_workspace / "imports.json",
        [
            {
                "tracked": True,
                "git-url": str(child_source),
                "commit-hash": git_head(child_source),
                "install-id": "child-id",
                "install-path": "/.doctidex-git/imports/child",
                "keys": ["child"],
                "branch": "main",
                "tag": "",
            }
        ],
    )
    assert git(source_repository, "add", ".doctidex-git").returncode == 0
    assert git(source_repository, "commit", "--quiet", "-m", "parent workspace").returncode == 0

    parent = cli.run(
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
    parent_id = parent.payload["install-id"]

    child_restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        parent_id,
        "import",
        "restore",
        "--install-id",
        "child-id",
    )
    assert child_restored.code == 0
    child_presentation_id = child_restored.payload["presentation-install-id"]
    assert Path(child_restored.payload["presentation-path"]).is_dir()

    grandchild_restored = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        child_presentation_id,
        "import",
        "restore",
        "--install-id",
        "grandchild-id",
    )
    assert grandchild_restored.code == 0
    assert grandchild_restored.payload["install-id"] == "grandchild-id"
    assert Path(grandchild_restored.payload["presentation-path"]).is_dir()
    grandchild_presentation_id = grandchild_restored.payload["presentation-install-id"]

    queried_after_restore = cli.run(
        "--repos-path",
        str(initialized_root),
        "--installation-context",
        child_presentation_id,
        "import",
        "query",
        "--install-id",
        "grandchild-id",
    )
    queried_candidate = queried_after_restore.payload["candidates"][0]
    assert queried_candidate["presentation-install-id"] == grandchild_presentation_id
    assert queried_candidate["presentation-path"] == grandchild_restored.payload["presentation-path"]

    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert all(item["install-id"] != "child-id" for item in runtime["imports"])
    assert all(item["install-id"] != "grandchild-id" for item in runtime["imports"])

    child_share = next(
        share
        for share in runtime["installation-shares"]
        if any(reference["install-id"] == "child-id" for reference in share["context-references"])
    )
    assert child_share["install-ids"] == []

    grandchild_share = next(
        share
        for share in runtime["installation-shares"]
        if any(reference["install-id"] == "grandchild-id" for reference in share["context-references"])
    )
    assert grandchild_share["install-ids"] == []
    assert any(
        reference["install-id"] == "grandchild-id"
        and reference["owner-install-id"] == child_presentation_id
        for reference in grandchild_share["context-references"]
    )
