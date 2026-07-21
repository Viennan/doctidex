"""CLI for creating and expanding Whero Wiki Views."""

from __future__ import annotations

import argparse
from pathlib import Path

from .model import WIKI_META_FILENAME
from .view_selection import (
    DEFAULT_COLLAPSE_THRESHOLD,
    parse_collapse_threshold,
    parse_view_name,
)
from .view_service import execute_view
from .view_types import ViewRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or expand a Whero Wiki View with relative symbolic links."
    )
    parser.add_argument(
        "--source",
        type=Path,
        help=(
            f"source Wiki or View, or any path inside it; omit to infer "
            f"{WIKI_META_FILENAME} from absolute or working-directory-relative "
            "selections"
        ),
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="parent directory for the View",
    )
    parser.add_argument(
        "--view-name",
        type=parse_view_name,
        help="View root name (default: source directory name)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="selection paths; equivalent to repeated --include",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help=(
            "file or directory path; accepts source-relative, current-working-"
            "directory-relative, absolute, and user-home forms; repeat as needed"
        ),
    )
    parser.add_argument(
        "--include-from",
        action="append",
        default=[],
        type=Path,
        help="file containing selection paths, one per non-comment line",
    )
    parser.add_argument(
        "--collapse-threshold",
        default=DEFAULT_COLLAPSE_THRESHOLD,
        type=parse_collapse_threshold,
        help=(
            "recursively disclosed file percentage that selects a whole directory; "
            "accepts 80, 80%%, or 0.8; use 0 to disable (default: 80)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the plan without writing",
    )
    return parser


def request_from_args(args: argparse.Namespace) -> ViewRequest:
    return ViewRequest(
        source=args.source,
        target=args.target,
        view_name=args.view_name,
        includes=tuple([*args.include, *args.paths]),
        include_files=tuple(args.include_from),
        collapse_threshold=args.collapse_threshold,
        dry_run=args.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    request = request_from_args(build_parser().parse_args(argv))
    result = execute_view(request)
    for message in result.messages:
        print(message)
    return 0
