from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from whero.doctidex.errors import DoctidexError
from whero.doctidex.git.diagnostics import write_diagnostic
from whero.doctidex.git.external import ExternalService
from whero.doctidex.git.source import RevisionSelector
from whero.doctidex.git.storage import RootStorage
from whero.doctidex.git.worktrees import CacheService, WorktreeService
from whero.doctidex.protocol.root import RootContext, discover_roots, root_at, select_root
from whero.doctidex.protocol.validation import validate_protocol

from .render import render_human, render_json


class UsageError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_count = raw.count("--json")
    json_output = json_count > 0
    raw = [value for value in raw if value != "--json"]
    args: argparse.Namespace | None = None
    try:
        if json_count > 1:
            raise UsageError("--json may be provided at most once")
        args = _parser().parse_args(raw)
        payload = _dispatch(args)
        exit_code = 2 if payload["status"] == "blocked" else (1 if payload.get("protocol_structure") == "fail" else 0)
    except UsageError as exc:
        payload = DoctidexError(
            str(exc),
            operation="command",
            actions=["Use one of the documented v1.0.0 command forms."],
            code="argument_invalid",
        ).as_result()
        exit_code = 2
    except DoctidexError as exc:
        payload = exc.as_result(root=_selected_root_for_error(args))
        exit_code = 2
    except KeyboardInterrupt:
        payload = DoctidexError(
            "The operation was interrupted; completed results were preserved.",
            operation=_operation_name(args),
            actions=["Inspect changed and affected fields before a limited retry."],
            code="interrupted",
        ).as_result(root=_selected_root_for_error(args))
        exit_code = 130
    except Exception as exc:
        try:
            diagnostic_id = write_diagnostic(exc)
        except Exception:
            diagnostic_id = "unavailable"
        payload = DoctidexError(
            "The CLI could not complete the operation.",
            operation=_operation_name(args),
            result=(
                "Existing files, Git worktrees, manifests, and cache entries were preserved "
                "where ownership was uncertain."
            ),
            actions=["Retry once.", f"If the failure persists, report diagnostic ID {diagnostic_id}."],
            code="unexpected_failure",
            details={"diagnostic_id": diagnostic_id},
        ).as_result(root=_selected_root_for_error(args))
        exit_code = 2
    print((render_json if json_output else render_human)(payload))
    return exit_code


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path.cwd()
    if args.command == "validate":
        context = select_root(
            operation="validate",
            explicit=Path(args.root) if args.root else None,
            default=cwd,
        )
        return validate_protocol(context, scopes=args.scope, limit=args.limit, cursor=args.cursor)

    if args.command == "external":
        if args.external_command == "link-parse":
            path = Path(args.path).absolute()
            _validate_parse_path(path)
            context = _select_path_owner(
                path,
                operation="external_link_parse",
                explicit=Path(args.root) if args.root else None,
            )
            return ExternalService(context).link_parse(path)

        context = select_root(
            operation=f"external_{args.external_command}",
            explicit=Path(args.root) if args.root else None,
            default=cwd,
        )
        service = ExternalService(context)
        if args.external_command == "install":
            return service.install(
                args.url,
                _selector(args),
                dependency_of=args.dependency_of,
                apply=args.apply,
                cwd=cwd,
            )
        if args.external_command == "link":
            return service.link(Path(args.source_directory), args.target_path, apply=args.apply)
        if args.external_command == "remove":
            return service.remove(args.install_id, apply=args.apply)
        return service.restore(
            args.install,
            apply=args.apply,
            limit=args.limit,
            cursor=args.cursor,
        )

    if args.command == "worktree":
        if args.worktree_command == "close":
            path = Path(args.worktree).absolute()
            context = _owner_root_for_worktree(path)
            return WorktreeService(context).close(path)
        if args.worktree_command == "open":
            source_path = Path(args.source).expanduser()
            if args.root:
                context = (
                    _select_path_owner(
                        source_path.absolute(),
                        operation="worktree_open",
                        explicit=Path(args.root),
                        unmanaged_must_contain=False,
                    )
                    if source_path.exists()
                    else select_root(operation="worktree_open", explicit=Path(args.root), default=cwd)
                )
            elif source_path.exists():
                context = _owner_root_for_path(source_path.absolute(), operation="worktree_open", fallback=cwd)
            else:
                context = select_root(operation="worktree_open", explicit=None, default=cwd)
            selector = _selector(args)
            assert selector is not None
            return WorktreeService(context).open(args.source, selector)
        context = select_root(
            operation="worktree_list",
            explicit=Path(args.root) if args.root else None,
            default=cwd,
        )
        return WorktreeService(context).list(
            source_filter=args.source,
            worktree_filter=Path(args.worktree).absolute() if args.worktree else None,
            limit=args.limit,
            cursor=args.cursor,
        )

    if args.command == "cache":
        if args.auto:
            return CacheService().clean_auto(apply=args.apply)
        assert args.url is not None
        return CacheService().clean(args.url, apply=args.apply)
    raise AssertionError(args.command)


def _parser() -> Parser:
    parser = Parser(prog="doctidex-git")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("root", nargs="?")
    validate.add_argument("--scope", action="append", default=[])
    _pagination(validate)

    external = commands.add_parser("external")
    external_commands = external.add_subparsers(dest="external_command", required=True)
    install = external_commands.add_parser("install")
    install.add_argument("--url", required=True)
    install.add_argument("--root")
    _revision(install, required=False)
    install.add_argument("--dependency-of")
    _mode(install)

    link = external_commands.add_parser("link")
    link.add_argument("source_directory")
    link.add_argument("target_path")
    link.add_argument("--root")
    _mode(link)

    restore = external_commands.add_parser("restore")
    restore.add_argument("--root")
    restore.add_argument("--install", action="append", default=[])
    _pagination(restore)
    _mode(restore)

    remove = external_commands.add_parser("remove")
    remove.add_argument("install_id")
    remove.add_argument("--root")
    _mode(remove)

    link_parse = external_commands.add_parser("link-parse")
    link_parse.add_argument("path")
    link_parse.add_argument("--root")

    worktree = commands.add_parser("worktree")
    worktree_commands = worktree.add_subparsers(dest="worktree_command", required=True)
    open_command = worktree_commands.add_parser("open")
    open_command.add_argument("source")
    open_command.add_argument("--root")
    _revision(open_command, required=True)

    list_command = worktree_commands.add_parser("list")
    list_command.add_argument("--root")
    filters = list_command.add_mutually_exclusive_group()
    filters.add_argument("--source")
    filters.add_argument("--worktree")
    _pagination(list_command)

    close = worktree_commands.add_parser("close")
    close.add_argument("worktree")

    cache = commands.add_parser("cache")
    cache_commands = cache.add_subparsers(dest="cache_command", required=True)
    clean = cache_commands.add_parser("clean")
    cache_selector = clean.add_mutually_exclusive_group(required=True)
    cache_selector.add_argument("--url")
    cache_selector.add_argument("--auto", action="store_true")
    _mode(clean)
    return parser


def _revision(parser: argparse.ArgumentParser, *, required: bool) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--commit")
    group.add_argument("--tag")
    group.add_argument("--branch")


def _mode(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")


def _pagination(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=_limit, default=100)
    parser.add_argument("--cursor")


def _limit(value: str) -> int:
    number = int(value)
    if not 1 <= number <= 1000:
        raise argparse.ArgumentTypeError("--limit must be between 1 and 1000")
    return number


def _selector(args: argparse.Namespace) -> RevisionSelector | None:
    for kind in ("commit", "tag", "branch"):
        value = getattr(args, kind, None)
        if value:
            return RevisionSelector(kind, value)
    return None


def _owner_root_for_path(path: Path, *, operation: str, fallback: Path | None = None) -> RootContext:
    managed = _managed_owner_roots(path)
    if len(managed) == 1:
        return managed[0]
    if len(managed) > 1:
        raise DoctidexError(
            "More than one managed owner root matches the path.",
            operation=operation,
            affected=[str(context.root) for context in managed],
            actions=["Retry with --root and the exact outer owner root."],
            requires_user="doctidex_root",
            code="root_ambiguous",
        )
    return select_root(operation=operation, explicit=None, default=fallback or path)


def _managed_owner_roots(path: Path) -> list[RootContext]:
    managed: list[RootContext] = []
    for context in discover_roots(path):
        runtime = RootStorage(context.root).read_runtime()
        if any(
            is_path_within_internal(path, context.root, item.get("install_path"))
            for item in runtime["installs"].values()
        ) or any(path == context.root.joinpath(*target.split("/")) for target in runtime["links"]):
            managed.append(context)
    return managed


def _select_path_owner(
    path: Path,
    *,
    operation: str,
    explicit: Path | None,
    unmanaged_must_contain: bool = True,
) -> RootContext:
    managed = _managed_owner_roots(path)
    if len(managed) > 1:
        raise DoctidexError(
            "More than one managed owner root matches the path.",
            operation=operation,
            affected=[str(context.root) for context in managed],
            actions=["Retry with --root and the exact outer owner root."],
            requires_user="doctidex_root",
            code="root_ambiguous",
        )
    if explicit is None:
        return managed[0] if managed else select_root(operation=operation, explicit=None, default=path)
    selected = select_root(
        operation=operation,
        explicit=explicit,
        default=path,
        must_contain=path if managed or unmanaged_must_contain else None,
    )
    if managed and selected.root != managed[0].root:
        raise DoctidexError(
            "The explicit root is not the outer owner of this managed path.",
            operation=operation,
            affected=[str(selected.root), str(managed[0].root), str(path)],
            actions=["Retry with the outer owner root returned in affected."],
            requires_user="doctidex_root",
            code="root_mismatch",
            path=str(path),
        )
    return selected


def _owner_root_for_worktree(path: Path) -> RootContext:
    candidates = discover_roots(path)
    for context in candidates:
        runtime = RootStorage(context.root).read_runtime()
        if any(item.get("worktree_path") == str(path) for item in runtime["worktrees"].values()):
            return context
    raise DoctidexError(
        "The exact path is not registered under a doctidex owner root.",
        operation="worktree_close",
        affected=[str(path)],
        actions=["Pass an exact worktree_path returned by worktree list."],
        code="worktree_unmanaged",
        domain="worktree",
        path=str(path),
        fields={"worktree": None},
    )


def is_path_within_internal(path: Path, root: Path, internal: object) -> bool:
    if not isinstance(internal, str):
        return False
    base = root.joinpath(*internal.lstrip("/").split("/"))
    try:
        path.absolute().relative_to(base.absolute())
        return True
    except ValueError:
        return False


def _validate_parse_path(path: Path) -> None:
    if path.is_symlink() or path.is_dir():
        return
    code = "path_type_unsupported" if path.exists() else "path_invalid"
    raise DoctidexError(
        "link-parse accepts an existing directory or a symlink itself.",
        operation="external_link_parse",
        affected=[str(path)],
        actions=["Pass the directory or symlink path, including a broken symlink itself."],
        code=code,
        domain="external",
        path=str(path),
    )


def _selected_root_for_error(args: argparse.Namespace | None) -> str | None:
    if args is None or getattr(args, "command", None) == "cache":
        return None
    value = getattr(args, "root", None)
    if value:
        context = root_at(Path(value).absolute())
        return str(context.root) if context else None
    roots = discover_roots(Path.cwd())
    return str(roots[0].root) if len(roots) == 1 else None


def _operation_name(args: argparse.Namespace | None) -> str:
    if args is None:
        return "operation"
    if args.command == "external":
        return f"external_{args.external_command.replace('-', '_')}"
    if args.command == "worktree":
        return f"worktree_{args.worktree_command}"
    if args.command == "cache":
        return "cache_clean"
    return str(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
