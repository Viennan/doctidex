from __future__ import annotations

from pathlib import Path

from conftest import CliRunner, git_head, read_json

from whero.doctidex.model import RuntimeState


def _load_state(root: Path) -> RuntimeState:
    return RuntimeState.from_documents(
        boundary_set=read_json(root / ".doctidex-git" / "boundary-set.json"),
        imports=read_json(root / ".doctidex-git" / "imports.json"),
        import_refs=read_json(root / ".doctidex-git" / "import-refs.json"),
        runtime=read_json(root / ".doctidex-git" / "runtime.json"),
    )


def test_branch_install_persists_selector_installation_and_derives_presentation(
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

    assert installed.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert len(runtime["imports"]) == 1
    assert runtime["imports"][0]["branch"] == "main"
    assert runtime["imports"][0]["tag"] == ""
    assert runtime["imports"][0]["install-id"] == installed.payload["install-id"]
    assert runtime["installation-shares"][0]["install-ids"] == [installed.payload["install-id"]]

    state = _load_state(initialized_root)
    assert len(state.presentation_installations) == 1
    presentation = state.presentation_installations[0]
    assert presentation.branch == ""
    assert presentation.tag == ""
    assert presentation.install_id not in runtime["installation-shares"][0]["install-ids"]


def test_commit_install_persists_normal_commit_installation_without_derived_duplicate(
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

    assert installed.code == 0
    runtime = read_json(initialized_root / ".doctidex-git" / "runtime.json")
    assert len(runtime["imports"]) == 1
    assert runtime["imports"][0]["branch"] == ""
    assert runtime["imports"][0]["tag"] == ""
    assert runtime["installation-shares"][0]["install-ids"] == [installed.payload["install-id"]]

    state = _load_state(initialized_root)
    assert state.presentation_installations == ()
