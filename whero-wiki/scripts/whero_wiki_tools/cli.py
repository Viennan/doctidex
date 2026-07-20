"""Command-line interface for Whero Wiki maintenance tooling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .curated import (
    CURATION_MODES,
    CURATION_STATUSES,
    init_curated_collection,
    init_curated_concept,
    init_index,
    init_log,
    record_source_digests,
    validate_wiki,
)
from .errors import WheroToolError
from .links import (
    inbound_links,
    inspect_document_links,
    inspect_wiki_links,
    normalization_suggestions,
    render_link_references,
    render_suggestions,
)
from .model import STATUS_FILENAME, validate_wiki_root
from .mounts import discover_boundaries
from .paths import parse_relative_path, path_from_root
from .git import changed_paths, repository_root
from .project import init_project_wiki
from .provenance import affected_concepts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Maintain, validate, and inspect Whero Wiki knowledge."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate a full or partial Wiki")
    validate.add_argument("--wiki", required=True, type=Path)
    validate.add_argument("--mode", choices=("auto", "full", "available"), default="auto")
    validate.add_argument("--strict-stale", action="store_true")
    validate.add_argument("--format", choices=("text", "json"), default="text")

    links = commands.add_parser("links", help="inspect the Wiki link graph")
    link_commands = links.add_subparsers(dest="links_command", required=True)
    for name, help_text in (
        ("list", "list links from one file or the owned Wiki"),
        ("broken", "list missing, invalid, or broken-anchor links"),
        ("graph", "emit the owned Wiki link graph"),
    ):
        command = link_commands.add_parser(name, help=help_text)
        command.add_argument("--wiki", required=True, type=Path)
        command.add_argument("--file")
        command.add_argument(
            "--mode",
            choices=("auto", "full", "available"),
            default="auto",
        )
        command.add_argument("--format", choices=("text", "json"), default="text")
    inbound = link_commands.add_parser("inbound", help="find links to one Wiki path")
    inbound.add_argument("--wiki", required=True, type=Path)
    inbound.add_argument("--target", required=True)
    inbound.add_argument(
        "--mode",
        choices=("auto", "full", "available"),
        default="auto",
    )
    inbound.add_argument("--format", choices=("text", "json"), default="text")
    normalize = link_commands.add_parser(
        "normalize",
        help="suggest whero-wiki:/ replacements for deep relative links",
    )
    normalize.add_argument("--wiki", required=True, type=Path)
    normalize.add_argument("--dry-run", action="store_true", required=True)
    normalize.add_argument("--format", choices=("text", "json"), default="text")

    mounts = commands.add_parser(
        "mounts",
        help="list preserved, nested Wiki, and submodule boundaries",
    )
    mounts.add_argument("--wiki", required=True, type=Path)
    mounts.add_argument("--mode", choices=("auto", "full", "available"), default="auto")
    mounts.add_argument("--format", choices=("text", "json"), default="text")

    project = commands.add_parser("init-project-wiki", help="initialize a project repository as a Whero Wiki")
    project.add_argument("--root", required=True, type=Path)
    project.add_argument("--title", required=True)
    project.add_argument("--description", required=True)
    project.add_argument("--agent-guide", type=Path)
    project.add_argument("--dry-run", action="store_true")

    affected = commands.add_parser("affected", help="find curated concepts affected by Git changes")
    affected.add_argument("--wiki", required=True, type=Path)
    affected.add_argument("--git-diff", required=True, dest="revision")
    affected.add_argument("--format", choices=("text", "json"), default="text")

    index = commands.add_parser("init-index", help="create a maintained index")
    index.add_argument("--wiki", required=True, type=Path)
    index.add_argument("--directory", default=".")
    index.add_argument("--title", required=True)
    index.add_argument("--description", required=True)
    index.add_argument("--dry-run", action="store_true")

    log = commands.add_parser("init-log", help="create a maintained log")
    log.add_argument("--wiki", required=True, type=Path)
    log.add_argument("--directory", default=".")
    log.add_argument("--title", required=True)
    log.add_argument("--dry-run", action="store_true")

    curated = commands.add_parser(
        "init-curated",
        help="declare and create a top-level curated collection",
    )
    curated.add_argument("--wiki", required=True, type=Path)
    curated.add_argument("--scope", required=True)
    curated.add_argument("--path", required=True)
    curated.add_argument("--title", required=True)
    curated.add_argument("--description", required=True)
    curated.add_argument("--with-log", action="store_true")
    curated.add_argument("--dry-run", action="store_true")

    concept = commands.add_parser("init-concept", help="create a curated concept")
    concept.add_argument("--wiki", required=True, type=Path)
    concept.add_argument("--path", required=True)
    concept.add_argument("--type", required=True, dest="concept_type")
    concept.add_argument("--title", required=True)
    concept.add_argument("--description", required=True)
    concept.add_argument("--curation-mode", required=True, choices=sorted(CURATION_MODES))
    concept.add_argument(
        "--curation-status",
        choices=sorted(CURATION_STATUSES),
        default="draft",
    )
    concept.add_argument("--source", action="append", default=[])
    concept.add_argument(
        "--provenance-json",
        action="append",
        default=[],
        help="JSON object for repository-path, git-revision, discussion, or user-authored provenance",
    )
    concept.add_argument("--tag", action="append", default=[])
    concept.add_argument("--dry-run", action="store_true")

    stamp = commands.add_parser(
        "record-source-digests",
        help="record source bytes after an explicit review",
    )
    stamp.add_argument("--wiki", required=True, type=Path)
    stamp.add_argument("--concept", required=True)
    stamp.add_argument("--status", choices=sorted(CURATION_STATUSES))
    stamp.add_argument("--confirm-reviewed", action="store_true", required=True)
    stamp.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init-project-wiki":
            paths = init_project_wiki(
                args.root,
                args.title,
                args.description,
                agent_guide=args.agent_guide,
                dry_run=args.dry_run,
            )
            action = "would initialize" if args.dry_run else "initialized"
            for path in paths:
                print(f"{action}: {path}")
            return 0
        if args.command == "affected":
            from dataclasses import asdict

            root = validate_wiki_root(args.wiki)
            repository = repository_root(root)
            if repository is None:
                raise WheroToolError(f"Wiki is not under Git version control: {root}")
            affected = affected_concepts(
                root,
                repository,
                changed_paths(repository, args.revision),
            )
            if args.format == "json":
                print(json.dumps([asdict(item) for item in affected], indent=2))
            else:
                for item in affected:
                    print(
                        f"AFFECTED {item.concept}: {item.changed_path} "
                        f"[{item.provenance_kind}]"
                    )
            return 0
        if args.command == "links":
            candidate = args.wiki.expanduser().resolve(strict=False)
            link_mode = getattr(args, "mode", "full")
            available = link_mode == "available" or (
                link_mode == "auto" and (candidate / STATUS_FILENAME).is_file()
            )
            root = validate_wiki_root(
                args.wiki,
                allow_symlink_meta=available,
            )
            if args.links_command == "inbound":
                references = inbound_links(root, args.target, available=available)
                output = render_link_references(references, args.format)
            elif args.links_command == "normalize":
                output = render_suggestions(normalization_suggestions(root), args.format)
            else:
                if args.file:
                    relative = parse_relative_path(args.file, label="Markdown file")
                    document = path_from_root(root, relative)
                    references = inspect_document_links(
                        root,
                        document,
                        available=available,
                    )
                else:
                    references = inspect_wiki_links(root, available=available)
                if args.links_command == "broken":
                    references = [
                        reference
                        for reference in references
                        if reference.status in ("missing", "invalid", "anchor-missing")
                    ]
                output = render_link_references(references, args.format)
            if output:
                print(output)
            return 0
        if args.command == "mounts":
            from dataclasses import asdict

            candidate = args.wiki.expanduser().resolve(strict=False)
            available = args.mode == "available" or (
                args.mode == "auto" and (candidate / STATUS_FILENAME).is_file()
            )
            root = validate_wiki_root(args.wiki, allow_symlink_meta=available)
            mounts_found, preserved, problems = discover_boundaries(root)
            if problems:
                raise WheroToolError(problems[0])
            if args.format == "json":
                print(
                    json.dumps(
                        [
                            {
                                **asdict(mount),
                                "path": mount.path.as_posix(),
                                "root": str(mount.root),
                            }
                            for mount in mounts_found
                        ]
                        + [
                            {
                                "path": entry.path.as_posix(),
                                "root": str(entry.root),
                                "kind": "preserved",
                                "submodule": False,
                                "git_commit": None,
                                "git_url": None,
                                "index": str(entry.index),
                            }
                            for entry in preserved
                        ],
                        indent=2,
                    )
                )
            else:
                for mount in mounts_found:
                    submodule = " submodule" if mount.submodule else ""
                    print(f"{mount.kind}{submodule}: {mount.path.as_posix()}")
                for entry in preserved:
                    print(f"preserved: {entry.path.as_posix()}")
            return 0
        if args.command == "validate":
            diagnostics = validate_wiki(
                args.wiki,
                mode=args.mode,
                strict_stale=args.strict_stale,
            )
            output = (
                diagnostics.render_json()
                if args.format == "json"
                else diagnostics.render_text()
            )
            if output:
                print(output)
            elif args.format == "text":
                print("validation passed")
            return 1 if diagnostics.has_errors else 0
        if args.command == "init-index":
            path = init_index(
                args.wiki,
                args.directory,
                args.title,
                args.description,
                dry_run=args.dry_run,
            )
        elif args.command == "init-log":
            path = init_log(
                args.wiki,
                args.directory,
                args.title,
                dry_run=args.dry_run,
            )
        elif args.command == "init-curated":
            path = init_curated_collection(
                args.wiki,
                args.scope,
                args.path,
                args.title,
                args.description,
                with_log=args.with_log,
                dry_run=args.dry_run,
            )
        elif args.command == "init-concept":
            provenance = []
            for raw in args.provenance_json:
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise WheroToolError(f"invalid --provenance-json: {exc}") from exc
                if not isinstance(item, dict):
                    raise WheroToolError("--provenance-json must decode to an object")
                provenance.append(item)
            path = init_curated_concept(
                args.wiki,
                args.path,
                args.concept_type,
                args.title,
                args.description,
                args.curation_mode,
                args.source,
                provenance=provenance,
                tags=args.tag,
                status=args.curation_status,
                dry_run=args.dry_run,
            )
        elif args.command == "record-source-digests":
            if not args.confirm_reviewed:
                raise WheroToolError(
                    "record-source-digests requires --confirm-reviewed"
                )
            path = record_source_digests(
                args.wiki,
                args.concept,
                status=args.status,
                dry_run=args.dry_run,
            )
        else:
            parser.error(f"unsupported command: {args.command}")
        action = "would initialize" if args.dry_run else "initialized"
        if args.command == "record-source-digests":
            action = "would record source digests for" if args.dry_run else "recorded source digests for"
        print(f"{action}: {path}")
        return 0
    except WheroToolError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
