from __future__ import annotations

import pytest
from conftest import CliRunner

from whero.doctidex import __version__
from whero.doctidex.cli.main import main


def test_success_result_envelope(cli: CliRunner, git_root) -> None:
    result = cli.run("--repos-path", str(git_root), "init")

    assert result.code == 0
    assert result.payload == {"status": "ok", "message": {}}


def test_version_flag_prints_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--version"])

    assert code == 0
    assert capsys.readouterr().out == f"doctidex-git {__version__}\n"


@pytest.mark.parametrize(
    "selectors",
    (
        ("--branch", "main", "--tag", "v1"),
        ("--branch", "main", "--commit", "abc123"),
        ("--tag", "v1", "--commit", "abc123"),
        (),
    ),
)
def test_revision_contract_rejects_any_selector_combination(cli: CliRunner, selectors: tuple[str, ...]) -> None:
    result = cli.run("import", "install", "--tracked", "--url", "url", *selectors)

    assert result.code == 2
    assert result.payload["status"] == "error"
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["details"]["parameter"] == "--branch/--tag/--commit"


def test_missing_required_argument_is_structured_json(cli: CliRunner) -> None:
    result = cli.run("boundary-set", "add")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["context"]["command"] == "boundary-set add"
    assert result.payload["message"]["details"]["parameter"] == "--path"


def test_validate_model_structure_is_mutually_exclusive_with_subdir(cli: CliRunner) -> None:
    result = cli.run("validate", "--subdir", "/docs", "--only-model-structure")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"


def test_argument_error_context_does_not_treat_an_unknown_value_as_a_subcommand(cli: CliRunner) -> None:
    result = cli.run("repair", "unexpected")

    assert result.code == 2
    assert result.payload["message"]["context"]["command"] == "repair"


@pytest.mark.parametrize(
    "argv",
    (
        ("--installation-context", "id", "--repos-path", "/repo", "init"),
        ("--installation-context", "id", "--repos-path", "/repo", "boundary-set", "parse", "--path", "/x"),
        ("--installation-context", "id", "--repos-path", "/repo", "import", "query", "--install-id", "x"),
        ("--installation-context", "id", "--repos-path", "/repo", "worktree", "query", "--work-path", "/x"),
        ("--installation-context", "id", "--repos-path", "/repo", "validate", "--only-model-structure"),
        ("--installation-context", "id", "--repos-path", "/repo", "repair"),
    ),
)
def test_installation_context_argument_is_accepted_for_every_command(
    cli: CliRunner, argv: tuple[str, ...]
) -> None:
    result = cli.run(*argv)

    assert result.code == 2
    assert result.payload["message"]["code"] == "git-root.unresolved"


def test_installation_context_rejects_empty_value(cli: CliRunner) -> None:
    result = cli.run("--installation-context", "", "repair")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["details"]["parameter"] == "--installation-context"


def test_argument_error_does_not_treat_installation_context_value_as_command(cli: CliRunner) -> None:
    result = cli.run("--installation-context", "validate", "boundary-set", "add")

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["context"]["command"] == "boundary-set add"


def test_repair_resolves_its_git_root_before_accessing_the_model(cli: CliRunner) -> None:
    result = cli.run("--repos-path", "/repo", "repair")

    assert result.code == 2
    assert result.payload["message"]["code"] == "git-root.unresolved"
    assert result.payload["message"]["context"] == {"command": "repair", "repos-path": "/repo"}


@pytest.mark.parametrize(
    "argv",
    (
        ("worktree", "create", "--url", "url"),
        ("worktree", "create", "--url", "url", "--branch", "main", "--tag", "v1"),
        ("worktree", "create", "--install-id", "id", "--branch", "main"),
        ("worktree", "create", "--url", "url", "--commit", "abc", "--work-path", "/work", "--tree-name", "x"),
    ),
)
def test_worktree_rejects_invalid_source_and_path_option_combinations(
    cli: CliRunner, argv: tuple[str, ...]
) -> None:
    result = cli.run(*argv)

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
