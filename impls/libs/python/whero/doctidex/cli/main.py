from __future__ import annotations

import argparse
import base64
import json
import sys
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from whero.doctidex.errors import DoctidexError
from whero.doctidex.git.context import git_status, git_worktree, root_gitignore_status
from whero.doctidex.git.maintenance import MaintenanceService
from whero.doctidex.git.mounts import GitMountService
from whero.doctidex.git.repository import RevisionSelector, SourceRepository
from whero.doctidex.git.setup import initialize
from whero.doctidex.git.state import write_diagnostic
from whero.doctidex.protocol.document import DoctidexDocument
from whero.doctidex.protocol.paths import internal_to_filesystem, mount_for_path, normalize_internal_path
from whero.doctidex.protocol.tree import RootContext, discover_roots, inspect_path, require_root
from whero.doctidex.protocol.validation import validate_protocol

from .render import render_human, render_json


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    globals_, remaining = _global_options(raw)
    parser = _parser()
    args = parser.parse_args(remaining)
    try:
        payload = _dispatch(args, globals_)
        payload = _apply_budget(payload, globals_)
        exit_code = (
            2 if payload.get("status") == "blocked" else (1 if payload.get("protocol_structure") == "fail" else 0)
        )
    except DoctidexError as exc:
        payload = exc.as_result()
        payload = _apply_budget(payload, globals_)
        exit_code = 2
    except KeyboardInterrupt:
        payload = DoctidexError(
            "The operation was interrupted; completed files and Git state were preserved.",
            operation=getattr(args, "operation", "operation"),
            actions=["Inspect the current state before retrying."],
            code="interrupted",
        ).as_result()
        exit_code = 130
    except Exception as exc:
        try:
            diagnostic_id = write_diagnostic(exc)
        except Exception:
            diagnostic_id = "unavailable"
        payload = DoctidexError(
            "The CLI could not complete the operation.",
            operation=getattr(args, "command", "operation"),
            result="Existing files, mounts, and Git results were preserved.",
            actions=["Retry once.", f"If the failure persists, report diagnostic ID {diagnostic_id}."],
            code="unexpected_failure",
            details={"diagnostic_id": diagnostic_id},
        ).as_result()
        exit_code = 2
    renderer = render_json if globals_["json"] else render_human
    print(renderer(payload))
    return exit_code


def _dispatch(args: argparse.Namespace, options: dict[str, Any]) -> dict[str, Any]:
    cwd = Path.cwd()
    if args.command == "context":
        path = Path(args.path or cwd).absolute()
        roots = discover_roots(path)
        if not roots:
            return {
                "status": "warning",
                "operation": "context",
                "git_worktree": str(git_worktree(path)) if git_worktree(path) else None,
                "root": None,
                "result": "No doctidex root contains the path.",
                "next_actions": ["Run doctidex-git init --dry-run for the intended root."],
            }
        if len(roots) > 1:
            raise DoctidexError(
                "More than one doctidex root contains the path.",
                operation="context",
                affected=[str(root.root) for root in roots],
                actions=["Retry with the exact root path."],
                code="root_ambiguous",
            )
        root = roots[0]
        mode = "mount_read" if "/.doctidex/mounts/" in path.as_posix() else "host_read"
        return {
            "status": "ok",
            "operation": "context",
            "git_worktree": str(git_worktree(root.root)),
            "root": str(root.root),
            "index": str(root.index.path),
            "mode": mode,
            "result": "Context selected.",
        }
    if args.command == "init":
        return initialize(Path(args.path or cwd), apply=args.apply)

    context = require_root(cwd if not getattr(args, "path", None) else Path(args.path), operation=args.command)
    if args.command == "inspect":
        target = Path(args.path).absolute() if args.path else cwd
        return _inspect(context, target)
    if args.command == "resolve":
        return _resolve(context, args.internal_path)
    if args.command == "mount":
        return _mount(context, args)
    if args.command == "maintenance":
        return _maintenance(context, args)
    if args.command == "check":
        return _check(context, online=args.online)
    if args.command == "changes":
        target = Path(args.path).absolute() if args.path else context.root
        changes = git_status(target)
        return {
            "status": "ok",
            "operation": "changes",
            "root": str(context.root),
            "items": changes,
            "result": f"Found {len(changes)} Git change(s).",
        }
    raise AssertionError(args.command)


def _inspect(context: RootContext, target: Path) -> dict[str, Any]:
    inspected = inspect_path(context, target)
    result: dict[str, Any] = {
        "status": "ok",
        "operation": "inspect",
        "root": str(context.root),
        "path_context": inspected.as_dict(),
        "result": "Path context inspected.",
    }
    if inspected.responsible_index:
        document = DoctidexDocument.load(inspected.responsible_index)
        result["links"] = [asdict(link) for link in document.links()]
    if inspected.source == "mount" and inspected.mount_path:
        entries = GitMountService(context).list()
        mount_state = next(item for item in entries if item["mount_path"] == inspected.mount_path)
        result["mount"] = mount_state
        if mount_state["readable"]:
            mount_root = context.root.joinpath(*inspected.mount_path.lstrip("/").split("/"))
            source_index = DoctidexDocument.load(mount_root / "index.md")
            relative = target.absolute().relative_to(mount_root.absolute())
            source_inspected = inspect_path(RootContext(mount_root, source_index), mount_root / relative)
            result["source_context"] = source_inspected.as_dict()
    protocol = validate_protocol(context)
    result["semantic_candidates"] = [
        item for item in protocol["semantic_candidates"] if item.get("index") == str(inspected.responsible_index)
    ]
    return result


def _resolve(context: RootContext, value: str) -> dict[str, Any]:
    normalized = normalize_internal_path(value)
    mounts = GitMountService(context).list()
    matched = mount_for_path(normalized, [item["mount_path"] for item in mounts])
    mount = next((item for item in mounts if item["mount_path"] == matched), None)
    working_path = internal_to_filesystem(context.root, normalized)
    return {
        "status": "ok",
        "operation": "resolve",
        "root": str(context.root),
        "input": value,
        "internal_path": normalized,
        "link_root": str(context.root),
        "working_path": str(working_path),
        "crosses_mount": mount is not None,
        "mount": mount,
        "result": "Path resolved."
        if not mount or mount["readable"]
        else "Mount is not prepared; use the listed action before native file access.",
    }


def _mount(context: RootContext, args: argparse.Namespace) -> dict[str, Any]:
    service = GitMountService(context)
    if args.mount_command == "list":
        items = service.list()
        return {
            "status": "ok",
            "operation": "mount_list",
            "root": str(context.root),
            "items": items,
            "result": f"Found {len(items)} mount(s).",
        }
    if args.mount_command == "add":
        selector = _argument_selector(args)
        return service.add(url=args.url, selector=selector, mount_path=args.mount_path, apply=args.apply)
    if args.mount_command == "remove":
        return service.remove(args.mount_path, apply=args.apply)
    targets = [args.mount_path] if args.mount_path else [mount.mount_path for mount in service.mounts()]
    if args.mount_command == "prepare":
        return _mount_batch("mount_prepare", context.root, targets, service.prepare)
    if args.mount_command == "sync":
        return _mount_batch("mount_sync", context.root, targets, lambda target: service.sync(target, apply=args.apply))
    raise AssertionError(args.mount_command)


def _maintenance(context: RootContext, args: argparse.Namespace) -> dict[str, Any]:
    service = MaintenanceService(context)
    if args.maintenance_command == "scope":
        items = service.scope([Path(path).absolute() for path in args.paths])
        return {
            "status": "ok",
            "operation": "maintenance_scope",
            "root": str(context.root),
            "items": items,
            "result": f"Found {len(items)} maintenance scope(s).",
        }
    root = Path(args.maintenance_root).absolute() if getattr(args, "maintenance_root", None) else None
    if args.maintenance_command == "open":
        return service.open(args.mount_path)
    if args.maintenance_command == "status":
        items = service.status(root)
        return {
            "status": "ok",
            "operation": "maintenance_status",
            "root": str(context.root),
            "items": items,
            "result": f"Found {len(items)} maintenance context(s).",
        }
    if args.maintenance_command == "handoff":
        return service.handoff(root)
    if args.maintenance_command == "close":
        return service.close(root)
    raise AssertionError(args.maintenance_command)


def _check(context: RootContext, *, online: bool) -> dict[str, Any]:
    protocol = validate_protocol(context)
    readiness = root_gitignore_status(context.root)
    findings = list(protocol["findings"])
    service = GitMountService(context)
    try:
        service.mounts()
    except DoctidexError as exc:
        readiness = {**readiness, "status": "blocked"}
        extension_finding = exc.as_result(str(context.root))["findings"][0]
        extension_finding["domain"] = "plugin_readiness"
        findings.append(extension_finding)
    if readiness["status"] == "blocked":
        findings.append(
            {
                "domain": "plugin_readiness",
                "severity": "error",
                "code": "git_mount_not_ready",
                "path": str(context.root / ".doctidex" / "mounts"),
                "message": "The root .gitignore or Git index is not ready for mount presentation.",
                "actions": ["Add /.doctidex/mounts/ to the root .gitignore and resolve tracked mount content."],
            }
        )
    remote: list[dict[str, Any]] = []
    if online:
        state = {item["mount_path"]: item for item in service.list()}
        for mount in service.mounts():
            latest = SourceRepository(mount.url).resolve(mount.selector, refresh=True)
            current = state[mount.mount_path].get("effective_commit")
            remote.append(
                {
                    "mount_path": mount.mount_path,
                    "effective_commit": current,
                    "remote_commit": latest,
                    "update_available": bool(current and current != latest),
                }
            )
    changes = git_status(context.root) if git_worktree(context.root) else []
    semantic = list(protocol["semantic_candidates"])
    for change in changes:
        if change["path"].endswith(("index.md", "log.md")):
            continue
        semantic.append(
            {
                "domain": "semantic_review",
                "severity": "info",
                "code": "git_change_review",
                "path": change["path"],
                "message": "Review whether this Git change requires index or log follow-up.",
                "actions": ["Use the responsible index and applicable log to make the semantic decision."],
            }
        )
    return {
        "status": "warning"
        if protocol["protocol_structure"] == "fail" or readiness["status"] == "blocked" or semantic
        else "ok",
        "operation": "check",
        "root": str(context.root),
        "protocol_structure": protocol["protocol_structure"],
        "semantic_review": "required" if semantic else "clear",
        "plugin_readiness": readiness["status"],
        "findings": findings,
        "semantic_candidates": semantic,
        "remote": remote,
        "result": "Checks completed without changing files or mount state.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doctidex-git")
    commands = parser.add_subparsers(dest="command", required=True)
    context = commands.add_parser("context")
    context.add_argument("path", nargs="?")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("path", nargs="?")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("internal_path")
    init = commands.add_parser("init")
    init.add_argument("path", nargs="?")
    _write_mode(init)

    mount = commands.add_parser("mount")
    mounts = mount.add_subparsers(dest="mount_command", required=True)
    mounts.add_parser("list")
    add = mounts.add_parser("add")
    add.add_argument("--url", required=True)
    selectors = add.add_mutually_exclusive_group(required=True)
    selectors.add_argument("--commit")
    selectors.add_argument("--tag")
    selectors.add_argument("--branch")
    add.add_argument("--mount-path", required=True)
    _write_mode(add)
    remove = mounts.add_parser("remove")
    remove.add_argument("mount_path")
    _write_mode(remove)
    prepare = mounts.add_parser("prepare")
    prepare.add_argument("mount_path", nargs="?")
    sync = mounts.add_parser("sync")
    sync.add_argument("mount_path", nargs="?")
    _write_mode(sync)

    maintenance = commands.add_parser("maintenance")
    maintenance_commands = maintenance.add_subparsers(dest="maintenance_command", required=True)
    scope = maintenance_commands.add_parser("scope")
    scope.add_argument("paths", nargs="*")
    open_command = maintenance_commands.add_parser("open")
    open_command.add_argument("mount_path")
    for name in ("status", "handoff", "close"):
        command = maintenance_commands.add_parser(name)
        command.add_argument("maintenance_root", nargs="?")

    check = commands.add_parser("check")
    check.add_argument("path", nargs="?")
    check.add_argument("--online", action="store_true")
    changes = commands.add_parser("changes")
    changes.add_argument("path", nargs="?")
    return parser


def _write_mode(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true")
    group.add_argument("--apply", action="store_true")


def _argument_selector(args: argparse.Namespace) -> RevisionSelector:
    for kind in ("commit", "tag", "branch"):
        value = getattr(args, kind)
        if value:
            return RevisionSelector(kind, value)
    raise AssertionError("selector")


def _mount_batch(
    operation: str,
    root: Path,
    targets: list[str],
    callback: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    if len(targets) == 1:
        return callback(targets[0])
    items: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    completed = 0
    for target in targets:
        try:
            items.append(callback(target))
            completed += 1
        except DoctidexError as exc:
            blocked = exc.as_result(str(root))
            blocked["mount_path"] = target
            items.append(blocked)
            findings.extend(blocked["findings"])
    return {
        "status": "blocked" if findings else "ok",
        "operation": operation,
        "root": str(root),
        "items": items,
        "findings": findings,
        "completed_count": completed,
        "total_count": len(targets),
        "changed": [],
        "result": f"Completed {completed} of {len(targets)} mount operation(s); all completed results were preserved.",
    }


def _global_options(arguments: list[str]) -> tuple[dict[str, Any], list[str]]:
    options: dict[str, Any] = {"json": False, "limit": 100, "depth": 4, "cursor": None}
    remaining: list[str] = []
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value == "--json":
            options["json"] = True
            index += 1
            continue
        if value in {"--limit", "--depth", "--cursor"}:
            if index + 1 >= len(arguments):
                raise SystemExit(f"{value} requires a value")
            key = value[2:]
            options[key] = arguments[index + 1] if key == "cursor" else int(arguments[index + 1])
            index += 2
            continue
        remaining.append(value)
        index += 1
    options["limit"] = max(1, min(int(options["limit"]), 1000))
    options["depth"] = max(0, min(int(options["depth"]), 32))
    return options, remaining


def _apply_budget(payload: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    limit = options["limit"]
    offset = _decode_cursor(options.get("cursor"))
    collections: dict[str, Any] = payload.setdefault("collection", {})

    def visit(value: Any, path: str, *, top_level: bool) -> Any:
        if isinstance(value, dict):
            return {
                key: visit(item, f"{path}.{key}" if path else key, top_level=False)
                for key, item in value.items()
                if key != "collection"
            }
        if not isinstance(value, list):
            return value
        start = offset if top_level else 0
        total = len(value)
        page = value[start : start + limit]
        returned = [visit(item, f"{path}[]", top_level=False) for item in page]
        next_offset = start + len(page)
        if total > len(page) or start:
            groups: dict[str, int] = {}
            for item in value:
                if not isinstance(item, dict):
                    continue
                item_path = item.get("path") or item.get("internal_path")
                if item_path:
                    parent = str(Path(str(item_path)).parent)
                    groups[parent] = groups.get(parent, 0) + 1
            collections[path] = {
                "total": total,
                "returned": len(page),
                "collapsed_directories": len(groups),
                "groups": dict(sorted(groups.items())[:limit]),
                "truncated": next_offset < total,
                "next_cursor": _encode_cursor(next_offset) if top_level and next_offset < total else None,
            }
        return returned

    for key in list(payload):
        if key == "collection":
            continue
        payload[key] = visit(payload[key], key, top_level=isinstance(payload[key], list))
    if not collections:
        payload.pop("collection", None)
    return payload


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"offset": offset}).encode("ascii")).decode("ascii").rstrip("=")


def _decode_cursor(value: str | None) -> int:
    if not value:
        return 0
    try:
        padding = "=" * (-len(value) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(value + padding))
        return max(0, int(decoded["offset"]))
    except Exception as exc:
        raise DoctidexError(
            "The pagination cursor is invalid.",
            operation="paginate",
            actions=["Restart the query without --cursor."],
            code="cursor_invalid",
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())
