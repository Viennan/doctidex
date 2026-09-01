from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, write_json

from whero.doctidex.installation import resolve_installation_context_by_id
from whero.doctidex.model import InstallationShare
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.store.runtime import RuntimeStore


def test_resolve_installation_context_accepts_derived_presentation_install_id(
    initialized_root: Path,
) -> None:
    share = InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
        install_ids=(),
        context_references=(),
        branch_refs=("main",),
    )
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [share.to_json()],
            "branch-snapshots": {},
        },
    )
    repo_path_to_fs(initialized_root, share.install_path).mkdir(parents=True)

    presentation = RuntimeStore(initialized_root).read_state().presentation_installations[0]
    context = resolve_installation_context_by_id(initialized_root, presentation.install_id)

    assert context.owner_root == initialized_root
    assert context.install_path == share.install_path


def test_boundary_set_parse_reports_presentation_install_path(
    initialized_root: Path,
    cli: CliRunner,
) -> None:
    share = InstallationShare(
        git_url="https://example.test/repository.git",
        commit_hash="0123456789abcdef",
        install_path="/.doctidex-git/imports/example/commit/0123456789abcdef",
        install_ids=(),
        context_references=(),
        branch_refs=("main",),
    )
    write_json(
        initialized_root / ".doctidex-git" / "runtime.json",
        {
            "imports": [],
            "worktrees": [],
            "installation-shares": [share.to_json()],
            "branch-snapshots": {},
        },
    )

    parsed = cli.run(
        "--repos-path",
        str(initialized_root),
        "boundary-set",
        "parse",
        "--path",
        f"{share.install_path}/readme.md",
    )

    assert parsed.code == 0
    assert parsed.payload["results"] == [
        {
            "path": f"{share.install_path}/readme.md",
            "has-boundary": True,
            "boundary-point": share.install_path,
            "boundary-type": "import",
        }
    ]
