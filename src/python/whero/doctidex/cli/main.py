"""CLI entry point and argument contract for doctidex-git v2."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import NoReturn

from .results import argument_error, error

COMMANDS = ("init", "boundary-set", "import", "worktree", "validate", "repair")
SUBCOMMANDS = {
    "boundary-set": {"add", "remove", "parse"},
    "import": {"install", "restore", "track", "remove", "ref", "unref", "query"},
    "worktree": {"create", "remove", "query"},
}


class UsageError(Exception):
    """Raised when command arguments do not satisfy the CLI contract."""

    def __init__(self, message: str, *, parameter: str | None = None) -> None:
        super().__init__(message)
        self.parameter = parameter


class HelpRequested(Exception):
    """Raised to let ``main`` render argparse help without a traceback."""

    def __init__(self, message: str | None) -> None:
        super().__init__()
        self.message = message or ""


class CliArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that exposes errors through the structured CLI result."""

    def error(self, message: str) -> NoReturn:
        raise UsageError(message, parameter=_parameter_from_message(message))

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if status == 0:
            raise HelpRequested(message)
        raise UsageError(message or "argument parsing failed")


@dataclass(frozen=True, slots=True)
class ParsedInvocation:
    """The small dispatch contract shared by all phase-one command registrations."""

    command: str
    repos_path: str | None


def build_parser() -> CliArgumentParser:
    """Build the v2 command parser from the documented CLI contract."""

    parser = CliArgumentParser(
        prog="doctidex-git",
        description="Manage doctidex v2 Git work models.",
    )
    parser.add_argument(
        "--repos-path",
        metavar="REPOSITORY-ROOT-PATH",
        help="Git root to operate on; omitted to discover it from the current path.",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    commands.add_parser("init", help="Initialize the doctidex-git work model.")
    _add_boundary_set_parser(commands)
    _add_import_parser(commands)
    _add_worktree_parser(commands)
    _add_validate_parser(commands)
    commands.add_parser("repair", help="Align physical state with the JSON work model.")
    return parser


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse and validate command arguments."""

    args = build_parser().parse_args(argv)
    _validate_revision_arguments(args)
    return args


def dispatch(args: argparse.Namespace) -> ParsedInvocation:
    """Dispatch a parsed command to its phase-one registration.

    Later implementation phases replace this registration with command workflows. Keeping the
    dispatch contract explicit now ensures every command shares root selection and result handling.
    """

    return ParsedInvocation(command=_command_path(args), repos_path=args.repos_path)


def main(argv: list[str] | None = None) -> int:
    """Run doctidex-git and emit one machine-readable result."""

    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parse_args(raw)
        invocation = dispatch(args)
    except HelpRequested as exc:
        if exc.message:
            print(exc.message, end="")
        return 0
    except UsageError as exc:
        payload = argument_error(
            command=_command_from_argv(raw),
            received=raw,
            constraint=str(exc),
            parameter=exc.parameter,
            repos_path=_repos_path_from_argv(raw),
        )
        print(_json(payload))
        return 2

    payload = error(
        command=invocation.command,
        code="command.phase-unavailable",
        summary="The command is registered, but its workflow is implemented in a later phase.",
        details={"implementation-phase": 1},
        repos_path=invocation.repos_path,
    )
    print(_json(payload))
    return 2


def _add_boundary_set_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    boundary = commands.add_parser("boundary-set", help="Manage doctidex boundary points.")
    subcommands = boundary.add_subparsers(dest="boundary_command", required=True, metavar="COMMAND")
    for name, help_text in (
        ("add", "Add custom boundary points."),
        ("remove", "Remove custom boundary points."),
        ("parse", "Resolve boundary points for paths."),
    ):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--path", action="append", required=True, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")


def _add_import_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    import_command = commands.add_parser("import", help="Manage external Git installations and refs.")
    subcommands = import_command.add_subparsers(dest="import_command", required=True, metavar="COMMAND")

    install = subcommands.add_parser("install", help="Install an external Git repository.")
    tracking = install.add_mutually_exclusive_group(required=True)
    tracking.add_argument("--tracked", action="store_true", help="Track installation metadata in Git.")
    tracking.add_argument("--untracked", action="store_true", help="Keep installation metadata untracked.")
    install.add_argument("--url", required=True, type=_non_empty, metavar="GIT-URL")
    install.add_argument("--branch", type=_non_empty, metavar="BRANCH")
    install.add_argument("--tag", type=_non_empty, metavar="TAG")
    install.add_argument("--commit", type=_non_empty, metavar="HASH")
    install.add_argument("--key", action="append", default=[], type=_non_empty, metavar="QUERY-KEY")

    for name, help_text in (("restore", "Restore a tracked installation."), ("track", "Track an installation.")):
        command = subcommands.add_parser(name, help=help_text)
        command.add_argument("--install-id", required=True, type=_non_empty, metavar="INSTALL-ID")

    remove = subcommands.add_parser("remove", help="Remove selected installations.")
    selection = remove.add_mutually_exclusive_group(required=True)
    selection.add_argument("--install-id", type=_non_empty, metavar="INSTALL-ID")
    selection.add_argument("--untracked", action="store_true", help="Select all untracked installations.")
    selection.add_argument("--auto", action="store_true", help="Select installations eligible for automatic cleanup.")

    ref = subcommands.add_parser("ref", help="Create a managed installation reference.")
    ref.add_argument("--install-id", required=True, type=_non_empty, metavar="INSTALL-ID")
    ref.add_argument("--src-sub-dir", type=_non_empty, metavar="INSTALLED-REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    ref.add_argument("--target-dir", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")

    unref = subcommands.add_parser("unref", help="Remove a managed installation reference.")
    unref.add_argument("--target-dir", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")

    query = subcommands.add_parser("query", help="Query installations and managed references.")
    selectors = query.add_mutually_exclusive_group(required=True)
    selectors.add_argument("--install-id", type=_non_empty, metavar="INSTALL-ID")
    selectors.add_argument("--install-path", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    selectors.add_argument("--ref-path", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    selectors.add_argument("--key", action="append", default=[], type=_non_empty, metavar="QUERY-KEY")


def _add_worktree_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    worktree = commands.add_parser("worktree", help="Manage Git worktrees.")
    subcommands = worktree.add_subparsers(dest="worktree_command", required=True, metavar="COMMAND")

    create = subcommands.add_parser("create", help="Create a managed worktree.")
    source = create.add_mutually_exclusive_group(required=True)
    source.add_argument("--install-id", type=_non_empty, metavar="INSTALL-ID")
    source.add_argument("--url", type=_non_empty, metavar="GIT-URL")
    create.add_argument("--work-path", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")

    remove = subcommands.add_parser("remove", help="Remove a managed worktree.")
    remove.add_argument("--work-path", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    remove.add_argument("--force", action="store_true", help="Allow removal of a dirty or abnormal worktree.")

    query = subcommands.add_parser("query", help="Query a managed worktree.")
    query.add_argument("--work-path", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")


def _add_validate_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    validate = commands.add_parser("validate", help="Validate the doctidex-git work model and tree.")
    validate.add_argument("--subdir", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")


def _validate_revision_arguments(args: argparse.Namespace) -> None:
    if args.command != "import" or args.import_command != "install":
        return
    if args.branch and args.tag:
        raise UsageError("--branch and --tag are mutually exclusive", parameter="--branch/--tag")
    if not any((args.branch, args.tag, args.commit)):
        raise UsageError("one of --branch, --tag, or --commit is required", parameter="--branch/--tag/--commit")


def _command_path(args: argparse.Namespace) -> str:
    parts = [args.command]
    for name in ("boundary_command", "import_command", "worktree_command"):
        value = getattr(args, name, None)
        if value:
            parts.append(value)
    return " ".join(parts)


def _command_from_argv(argv: list[str]) -> str:
    values = iter(argv)
    for value in values:
        if value == "--repos-path":
            next(values, None)
            continue
        if value.startswith("-"):
            continue
        if value in COMMANDS:
            command = value
            break
    else:
        return "unknown"

    subcommands = SUBCOMMANDS.get(command, set())
    index = argv.index(command)
    for value in argv[index + 1 :]:
        if value in subcommands:
            return f"{command} {value}"
    return command


def _repos_path_from_argv(argv: list[str]) -> str | None:
    try:
        index = argv.index("--repos-path")
    except ValueError:
        return None
    if index + 1 >= len(argv) or argv[index + 1].startswith("-"):
        return None
    return argv[index + 1]


def _parameter_from_message(message: str) -> str | None:
    match = re.search(r"argument (--[\w-]+)", message)
    if match:
        return match.group(1)
    match = re.search(r"required: (--[\w-]+)", message)
    return match.group(1) if match else None


def _non_empty(value: str) -> str:
    if not value:
        raise argparse.ArgumentTypeError("value must not be empty")
    return value


def _json(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
