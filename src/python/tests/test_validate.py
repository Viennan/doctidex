from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, write_json


def _write_markdown(root: Path, body: str = "") -> None:
    (root / "index.md").write_text(body)


def test_validate_uninitialized_is_a_diagnostic_result(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "validate")

    assert result.code == 1
    assert result.payload["status"] == "ok"
    assert result.payload["valid"] is False
    assert result.payload["diagnostics"][0]["details"]["violations"][0]["code"] == "workspace.uninitialized"


def test_validate_model_structure_reports_uninitialized_workspace(git_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(git_root), "validate", "--only-model-structure")

    assert result.code == 1
    assert {item["rule"] for item in result.payload["diagnostics"]} == {"work-model.valid"}


def test_validate_model_structure_skips_directory_tree_checks(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    _write_markdown(initialized_root, "[missing](/external/missing.md)\n")

    structure = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")
    complete = cli.run("--repos-path", str(initialized_root), "validate")

    assert structure.code == 0
    assert structure.payload["valid"] is True
    assert structure.payload["scope"] == {"repos-path": str(initialized_root), "subdir": "/"}
    assert complete.code == 1
    assert any(item["rule"] == "link.target.exists" for item in complete.payload["diagnostics"])


def test_validate_ignores_ordinary_missing_link(initialized_root: Path, cli: CliRunner) -> None:
    _write_markdown(initialized_root, "[missing](/missing.md)\n")

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_model_structure_ignores_index_document_content(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / "index.md").write_text("---\ntype: guide\n---\n")

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_valid_root_and_missing_link_include_scope_and_line(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    _write_markdown(initialized_root, "[missing](/external/missing.md)\n")

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 1
    assert result.payload["scope"] == {"repos-path": str(initialized_root), "subdir": "/"}
    diagnostic = next(item for item in result.payload["diagnostics"] if item["rule"] == "link.target.exists")
    assert diagnostic["path"] == "/index.md"
    assert diagnostic["line"] == 1
    assert diagnostic["details"]["target-path"] == "/external/missing.md"


def test_validate_extracts_each_link_annotation_from_its_own_comment_sequence(
    initialized_root: Path, cli: CliRunner
) -> None:
    (initialized_root / "first").mkdir()
    (initialized_root / "second").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/first", "--path", "/second")
    _write_markdown(
        initialized_root,
        "[first](/first) <!-- another comment --><!--\n"
        "  doctidex:\n"
        "    cross-boundary-point: /first\n"
        "--> [second](/second) <!-- doctidex: {cross-boundary-point: /second} -->\n",
    )

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_does_not_share_an_annotation_between_identical_links_on_one_line(
    initialized_root: Path, cli: CliRunner
) -> None:
    (initialized_root / "external").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    _write_markdown(
        initialized_root,
        "[same](/external) [same](/external) "
        "<!-- doctidex: {cross-boundary-point: /external} -->\n",
    )

    result = cli.run("--repos-path", str(initialized_root), "validate")

    annotations = [item for item in result.payload["diagnostics"] if item["rule"] == "link.annotation.required"]
    assert result.code == 1
    assert len(annotations) == 1


def test_validate_accepts_relative_cross_boundary_annotation(initialized_root: Path, cli: CliRunner) -> None:
    _write_markdown(initialized_root)
    (initialized_root / "external").mkdir()
    (initialized_root / "external" / "readme.md").write_text("external\n")
    (initialized_root / "guides").mkdir()
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "guides" / "intro.md").write_text(
        "[external](../external/readme.md) <!-- doctidex: {cross-boundary-point: ../external} -->\n"
    )

    result = cli.run("--repos-path", str(initialized_root), "validate")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_rejects_subdir_inside_boundary(initialized_root: Path, cli: CliRunner) -> None:
    _write_markdown(initialized_root)
    cli.run("--repos-path", str(initialized_root), "boundary-set", "add", "--path", "/external")
    (initialized_root / "external" / "docs").mkdir(parents=True)

    result = cli.run("--repos-path", str(initialized_root), "validate", "--subdir", "/external/docs")

    assert result.code == 2
    assert result.payload["message"]["code"] == "validation.scope.unavailable"
    assert result.payload["message"]["details"]["reason"] == "outside-current-tree"


def test_validate_rejects_subdir_inside_workspace(initialized_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(initialized_root), "validate", "--subdir", "/.doctidex-git")

    assert result.code == 2
    assert result.payload["message"]["code"] == "validation.scope.unavailable"
    assert result.payload["message"]["details"]["reason"] == "workspace-internal"


def test_validate_rejects_subdir_that_is_not_a_directory(initialized_root: Path, cli: CliRunner) -> None:
    result = cli.run("--repos-path", str(initialized_root), "validate", "--subdir", "/missing")

    assert result.code == 2
    assert result.payload["message"]["code"] == "validation.scope.unavailable"
    assert result.payload["message"]["details"]["reason"] == "not-directory"


def test_validate_reports_missing_workspace_artifact(initialized_root: Path, cli: CliRunner) -> None:
    (initialized_root / ".doctidex-git" / "runtime.json").unlink()

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 1
    violations = result.payload["diagnostics"][0]["details"]["violations"]
    assert any(item["code"] == "workspace.artifact.missing" for item in violations)


def test_validate_reports_dirty_installation(
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
    install_root = initialized_root / installed.payload["install-path"].lstrip("/")
    (install_root / "readme.md").write_text("dirty tracked\n")
    (install_root / "dirty-extra.md").write_text("dirty untracked\n")

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 1
    violations = [
        item
        for diagnostic in result.payload["diagnostics"]
        if diagnostic["rule"] == "work-model.valid"
        for item in diagnostic["details"]["violations"]
    ]
    dirty = next(item for item in violations if item["code"] == "installation.worktree.dirty")
    assert dirty["details"] == {
        "install-id": installed.payload["install-id"],
        "install-path": installed.payload["install-path"],
    }


def test_validate_does_not_physically_check_inactive_branch_snapshots(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    snapshot = {
        "imports": [
            {
                "tracked": False,
                "git-url": "https://example.test/repository.git",
                "commit-hash": "0123456789abcdef",
                "install-id": "inactive",
                "install-path": "/.doctidex-git/imports/example/inactive",
                "keys": ["repository"],
                "branch": "",
                "tag": "",
            }
        ],
        "worktrees": [],
        "installation-shares": [],
    }
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [],
            "branch-snapshots": {"feature": snapshot},
        },
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 0
    assert result.payload["valid"] is True


def test_validate_reports_duplicate_share_branch_refs(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [
                {
                    "git-url": "https://example.test/repository.git",
                    "commit-hash": "0123456789abcdef",
                    "install-path": "/.doctidex-git/imports/example/commit/0123456789abcdef",
                    "install-ids": [],
                    "context-references": [],
                    "branch-refs": ["main", "main"],
                }
            ],
            "branch-snapshots": {},
        },
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 1
    violations = [
        item
        for diagnostic in result.payload["diagnostics"]
        if diagnostic["rule"] == "work-model.valid"
        for item in diagnostic["details"]["violations"]
    ]
    assert any(
        item["code"] == "state-record.invalid"
        and item["details"]["identity-field"] == "installation-share-branch-ref"
        for item in violations
    )


def test_validate_reports_share_path_without_commit_kind(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [
                {
                    "git-url": "https://example.test/repository.git",
                    "commit-hash": "0123456789abcdef",
                    "install-path": "/.doctidex-git/imports/example/0123456789abcdef",
                    "install-ids": [],
                    "context-references": [],
                    "branch-refs": [],
                }
            ],
            "branch-snapshots": {},
        },
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 1
    violations = [
        item
        for diagnostic in result.payload["diagnostics"]
        if diagnostic["rule"] == "work-model.valid"
        for item in diagnostic["details"]["violations"]
    ]
    assert any(item["code"] == "installation.share.commit-path.invalid" for item in violations)


def test_validate_reports_missing_context_reference_owner(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [
                {
                    "git-url": "https://example.test/repository.git",
                    "commit-hash": "0123456789abcdef",
                    "install-path": "/.doctidex-git/imports/example/commit/0123456789abcdef",
                    "install-ids": [],
                    "context-references": [
                        {
                            "install-id": "sub-id",
                            "owner-install-id": "missing-owner-id",
                        }
                    ],
                    "branch-refs": [],
                }
            ],
            "branch-snapshots": {},
        },
    )

    result = cli.run("--repos-path", str(initialized_root), "validate", "--only-model-structure")

    assert result.code == 1
    violations = [
        item
        for diagnostic in result.payload["diagnostics"]
        if diagnostic["rule"] == "work-model.valid"
        for item in diagnostic["details"]["violations"]
    ]
    assert any(
        item["code"] == "installation.context-reference.owner.missing"
        for item in violations
    )
