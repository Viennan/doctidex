"""CLI entry point and argument contract for doctidex-git v2."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from whero.doctidex import boundary as boundary_workflow
from whero.doctidex import imports as import_workflow
from whero.doctidex import worktree as worktree_workflow
from whero.doctidex.errors import CommandFailure
from whero.doctidex.git_cache import GitCache
from whero.doctidex.initialization import (
    WORKSPACE_ARTIFACTS,
    GitRootUnresolved,
    WorkspaceInitializeFailed,
    initialize,
)
from whero.doctidex.model import ModelFormatError
from whero.doctidex.model_view import RuntimeModelView
from whero.doctidex.paths import normalize_repo_path
from whero.doctidex.repository import resolve_git_root
from whero.doctidex.store.files import StoreFailure
from whero.doctidex.store.runtime import RuntimeStore

from .results import argument_error, error, success

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
    """The common command and Git-root selection contract used by dispatch."""

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
    """Return the common invocation information used by command workflows."""

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

    if args.command == "init":
        return _run_init(invocation)
    if args.command == "boundary-set":
        return _run_boundary(invocation, args)
    if args.command == "import":
        return _run_import(invocation, args)
    if args.command == "worktree":
        return _run_worktree(invocation, args)
    payload = error(
        command=invocation.command,
        code="command.phase-unavailable",
        summary="The command is registered, but its workflow is implemented in a later phase.",
        details={"implementation-phase": _implementation_phase(args.command)},
        repos_path=invocation.repos_path,
    )
    print(_json(payload))
    return 2


def _run_boundary(invocation: ParsedInvocation, args: argparse.Namespace) -> int:
    try:
        root = resolve_git_root(invocation.repos_path)
        operation = ParsedInvocation(invocation.command, str(root))
        store = _runtime_store(root)
        if args.boundary_command == "add":
            boundary_workflow.add(store, args.path)
            payload = success(command=operation.command)
        elif args.boundary_command == "remove":
            boundary_workflow.remove(store, args.path)
            payload = success(command=operation.command)
        else:
            payload = success(command=operation.command, results=boundary_workflow.parse(store, args.path))
    except CommandFailure as exc:
        payload = _command_failure(locals().get("operation", invocation), exc)
    except GitRootUnresolved as exc:
        payload = error(
            command=invocation.command,
            code="git-root.unresolved",
            summary="The command could not resolve the requested Git root.",
            details={
                "requested-repos-path": exc.requested_repos_path,
                "discovery-start-path": str(exc.discovery_start_path),
            },
            repos_path=invocation.repos_path,
        )
    except (StoreFailure, ModelFormatError) as exc:
        payload = _store_or_model_failure(locals().get("operation", invocation), exc)
    print(_json(payload))
    return 0 if payload["status"] == "ok" else 2


def _run_import(invocation: ParsedInvocation, args: argparse.Namespace) -> int:
    try:
        root = resolve_git_root(invocation.repos_path)
        operation = ParsedInvocation(invocation.command, str(root))
        store = _runtime_store(root)
        cache = GitCache.from_environment()
        name = args.import_command
        if name == "install":
            item = import_workflow.install(
                store,
                cache,
                tracked=args.tracked,
                git_url=args.url,
                branch=args.branch or "",
                tag=args.tag or "",
                commit=args.commit or "",
                keys=args.key,
            )
            payload = success(
                command=operation.command, **{"install-id": item.install_id, "install-path": item.install_path}
            )
        elif name == "restore":
            item = import_workflow.restore(store, cache, args.install_id)
            payload = success(
                command=operation.command, **{"install-id": item.install_id, "install-path": item.install_path}
            )
        elif name == "track":
            item = import_workflow.track(store, args.install_id)
            payload = success(
                command=operation.command, **{"install-id": item.install_id, "install-path": item.install_path}
            )
        elif name == "remove":
            import_workflow.remove(store, args.install_id, untracked=args.untracked, auto=args.auto)
            payload = success(command=operation.command)
        elif name == "ref":
            import_workflow.ref(store, args.install_id, args.src_sub_dir or "", args.target_dir)
            payload = success(command=operation.command)
        elif name == "unref":
            import_workflow.unref(store, args.target_dir)
            payload = success(command=operation.command)
        else:
            install_path = _normalize_optional_path(args.install_path, "--install-path")
            ref_path = _normalize_optional_path(args.ref_path, "--ref-path")
            with store.read_only_transaction() as transaction:
                candidates = import_workflow.query(
                    RuntimeModelView(transaction),
                    install_id=args.install_id,
                    install_path=install_path,
                    ref_path=ref_path,
                    keys=args.key,
                )
            payload = success(command=operation.command, candidates=candidates)
    except CommandFailure as exc:
        payload = _command_failure(locals().get("operation", invocation), exc)
    except GitRootUnresolved as exc:
        payload = error(
            command=invocation.command,
            code="git-root.unresolved",
            summary="The command could not resolve the requested Git root.",
            details={
                "requested-repos-path": exc.requested_repos_path,
                "discovery-start-path": str(exc.discovery_start_path),
            },
            repos_path=invocation.repos_path,
        )
    except (StoreFailure, ModelFormatError) as exc:
        payload = _store_or_model_failure(locals().get("operation", invocation), exc)
    print(_json(payload))
    return 0 if payload["status"] == "ok" else 2


def _run_worktree(invocation: ParsedInvocation, args: argparse.Namespace) -> int:
    try:
        root = resolve_git_root(invocation.repos_path)
        operation = ParsedInvocation(invocation.command, str(root))
        store = _runtime_store(root)
        name = args.worktree_command
        if name == "create":
            record = worktree_workflow.create(
                store,
                GitCache.from_environment(),
                install_id=args.install_id,
                git_url=args.url,
                work_path=args.work_path,
                branch=args.branch or "",
                tag=args.tag or "",
                commit=args.commit or "",
                tree_name=args.tree_name,
            )
            payload = success(command=operation.command, **{"work-path": record.work_path})
        elif name == "remove":
            worktree_workflow.remove(
                store,
                GitCache.from_environment(),
                work_path=args.work_path,
                force=args.force,
            )
            payload = success(command=operation.command)
        else:
            record = worktree_workflow.query(store, work_path=args.work_path)
            fields: dict[str, object] = {}
            if record.install_id is not None:
                fields["install-id"] = record.install_id
            payload = success(command=operation.command, **fields)
    except CommandFailure as exc:
        payload = _command_failure(locals().get("operation", invocation), exc)
    except GitRootUnresolved as exc:
        payload = error(
            command=invocation.command,
            code="git-root.unresolved",
            summary="The command could not resolve the requested Git root.",
            details={
                "requested-repos-path": exc.requested_repos_path,
                "discovery-start-path": str(exc.discovery_start_path),
            },
            repos_path=invocation.repos_path,
        )
    except (StoreFailure, ModelFormatError) as exc:
        payload = _store_or_model_failure(locals().get("operation", invocation), exc)
    print(_json(payload))
    return 0 if payload["status"] == "ok" else 2


def _command_failure(invocation: ParsedInvocation, exc: CommandFailure) -> dict[str, object]:
    return error(
        command=invocation.command,
        code=exc.code,
        summary=exc.summary,
        subject=exc.subject,
        details=exc.details,
        repos_path=invocation.repos_path,
    )


def _store_or_model_failure(invocation: ParsedInvocation, exc: Exception) -> dict[str, object]:
    if isinstance(exc, StoreFailure):
        details: dict[str, object] = {"store": exc.store, "phase": exc.phase, "state-path": str(exc.state_path)}
        if exc.transaction_id is not None:
            details["transaction-id"] = exc.transaction_id
        return error(
            command=invocation.command,
            code="store.transaction.unavailable",
            summary="The doctidex-git state store could not complete the requested operation.",
            details=details,
            repos_path=invocation.repos_path,
        )
    return error(
        command=invocation.command,
        code="work-model.invalid",
        summary="The doctidex-git work model is not valid for this operation.",
        details={"violations": [{"artifact": exc.artifact, "expected": exc.expected_shape}]},
        repos_path=invocation.repos_path,
    )


def _runtime_store(root: Path) -> RuntimeStore:
    store = RuntimeStore(root)
    if not store.workspace_path.is_dir():
        raise CommandFailure(
            code="work-model.uninitialized",
            summary="The doctidex-git work model has not been initialized.",
            subject={"kind": "workspace", "path": "/.doctidex-git"},
            details={"required-command": "init"},
        )
    return store


def _normalize_optional_path(value: str | None, parameter: str) -> str | None:
    return normalize_repo_path(value, parameter=parameter) if value is not None else None


def _run_init(invocation: ParsedInvocation) -> int:
    try:
        initialize(invocation.repos_path)
    except GitRootUnresolved as exc:
        payload = error(
            command="init",
            code="git-root.unresolved",
            summary="The command could not resolve the requested Git root.",
            details={
                "requested-repos-path": exc.requested_repos_path,
                "discovery-start-path": str(exc.discovery_start_path),
            },
        )
    except WorkspaceInitializeFailed as exc:
        payload = error(
            command="init",
            code="workspace.initialize.failed",
            summary="The doctidex-git workspace could not be initialized completely.",
            subject={"kind": "workspace", "path": "/.doctidex-git"},
            details={
                "required-artifacts": list(WORKSPACE_ARTIFACTS),
                "unavailable-artifacts": list(exc.unavailable_artifacts),
            },
            repos_path=str(exc.git_root),
        )
    except StoreFailure as exc:
        payload = error(
            command="init",
            code="store.transaction.unavailable",
            summary="The RuntimeStore could not be read while initializing the work model.",
            details={
                "store": exc.store,
                "phase": exc.phase,
                "state-path": str(exc.state_path),
                **({"transaction-id": exc.transaction_id} if exc.transaction_id is not None else {}),
            },
            repos_path=invocation.repos_path,
        )
    else:
        print(_json(success(command="init")))
        return 0

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
    create.add_argument("--branch", type=_non_empty, metavar="BRANCH")
    create.add_argument("--tag", type=_non_empty, metavar="TAG")
    create.add_argument("--commit", type=_non_empty, metavar="HASH")
    create.add_argument("--work-path", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    create.add_argument("--tree-name", type=_non_empty, metavar="TREE-NAME")

    remove = subcommands.add_parser("remove", help="Remove a managed worktree.")
    remove.add_argument("--work-path", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")
    remove.add_argument("--force", action="store_true", help="Allow removal of a dirty or abnormal worktree.")

    query = subcommands.add_parser("query", help="Query a managed worktree.")
    query.add_argument("--work-path", required=True, type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")


def _add_validate_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    validate = commands.add_parser("validate", help="Validate the doctidex-git work model and tree.")
    validate.add_argument("--subdir", type=_non_empty, metavar="REPOSITORY-INTERNAL-ABSOLUTE-PATH")


def _validate_revision_arguments(args: argparse.Namespace) -> None:
    if args.command == "import" and args.import_command == "install":
        if sum(bool(value) for value in (args.branch, args.tag, args.commit)) != 1:
            raise UsageError(
                "exactly one of --branch, --tag, or --commit is required",
                parameter="--branch/--tag/--commit",
            )
        return
    if args.command != "worktree" or args.worktree_command != "create":
        return
    selectors = (args.branch, args.tag, args.commit)
    if args.install_id is not None and any(selectors):
        raise UsageError(
            "revision selectors are only available with --url",
            parameter="--branch/--tag/--commit",
        )
    if args.url is not None and sum(bool(value) for value in selectors) != 1:
        raise UsageError(
            "exactly one of --branch, --tag, or --commit is required with --url",
            parameter="--branch/--tag/--commit",
        )
    if args.work_path is not None and args.tree_name is not None:
        raise UsageError("--tree-name requires the default work-path", parameter="--tree-name")


def _implementation_phase(command: str) -> int:
    return {
        "boundary-set": 4,
        "import": 4,
        "worktree": 5,
        "validate": 6,
        "repair": 6,
    }[command]


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
