from __future__ import annotations

import json

import pytest

from whero.doctidex.cli.main import main, parse_args
from whero.doctidex.cli.results import success


def test_common_success_result_has_the_documented_shape() -> None:
    assert success(command="init") == {"status": "ok", "message": {}}


def test_common_repos_path_is_available_to_every_command() -> None:
    args = parse_args(["--repos-path", "/repo", "repair"])

    assert args.repos_path == "/repo"
    assert args.command == "repair"


def test_revision_contract_allows_branch_and_commit() -> None:
    args = parse_args(
        [
            "import",
            "install",
            "--tracked",
            "--url",
            "https://example.test/repo.git",
            "--branch",
            "main",
            "--commit",
            "abc123",
        ]
    )

    assert args.branch == "main"
    assert args.commit == "abc123"


def test_revision_contract_rejects_branch_and_tag() -> None:
    result = _run(["import", "install", "--tracked", "--url", "url", "--branch", "main", "--tag", "v1"])

    assert result.code == 2
    assert result.payload["status"] == "error"
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["details"]["parameter"] == "--branch/--tag"


def test_missing_required_argument_is_structured_json() -> None:
    result = _run(["boundary-set", "add"])

    assert result.code == 2
    assert result.payload["message"]["code"] == "argument.invalid"
    assert result.payload["message"]["context"]["command"] == "boundary-set add"
    assert result.payload["message"]["details"]["parameter"] == "--path"


def test_argument_error_context_does_not_treat_an_unknown_value_as_a_subcommand() -> None:
    result = _run(["repair", "unexpected"])

    assert result.code == 2
    assert result.payload["message"]["context"]["command"] == "repair"


def test_registered_command_has_explicit_phase_boundary() -> None:
    result = _run(["--repos-path", "/repo", "repair"])

    assert result.code == 2
    assert result.payload["message"]["code"] == "command.phase-unavailable"
    assert result.payload["message"]["context"] == {"command": "repair", "repos-path": "/repo"}


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        (["init"], "init"),
        (["boundary-set", "parse", "--path", "/docs"], "boundary-set parse"),
        (["import", "query", "--key", "topic"], "import query"),
        (["worktree", "query", "--work-path", "/work"], "worktree query"),
        (["validate"], "validate"),
        (["repair"], "repair"),
    ],
)
def test_every_command_cluster_reaches_the_dispatch_boundary(argv: list[str], command: str) -> None:
    result = _run(argv)

    assert result.code == 2
    assert result.payload["message"]["code"] == "command.phase-unavailable"
    assert result.payload["message"]["context"]["command"] == command


class _RunResult:
    def __init__(self, code: int, payload: dict[str, object]) -> None:
        self.code = code
        self.payload = payload


def _run(argv: list[str]) -> _RunResult:
    # main writes exactly one JSON result for command execution paths.
    import contextlib
    import io

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(argv)
    return _RunResult(code, json.loads(output.getvalue()))
