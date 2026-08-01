from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.errors import DoctidexError

from .document import DoctidexDocument


@dataclass(frozen=True, slots=True)
class RootContext:
    root: Path
    index: DoctidexDocument


def root_at(path: Path) -> RootContext | None:
    directory = Path(os.path.abspath(path))
    if not directory.is_dir():
        return None
    index_path = directory / "index.md"
    if not index_path.is_file():
        return None
    try:
        document = DoctidexDocument.load(index_path)
    except DoctidexError:
        return None
    return RootContext(directory, document) if document.is_root else None


def discover_roots(path: Path) -> list[RootContext]:
    current = Path(os.path.abspath(path))
    if current.is_file() or current.is_symlink() or not current.exists():
        current = current.parent
    roots: list[RootContext] = []
    for directory in (current, *current.parents):
        context = root_at(directory)
        if context is not None:
            roots.append(context)
    return roots


def select_root(
    *,
    operation: str,
    explicit: Path | None,
    default: Path,
    must_contain: Path | None = None,
) -> RootContext:
    if explicit is not None:
        candidate = Path(os.path.abspath(explicit))
        context = root_at(candidate)
        if context is None:
            raise DoctidexError(
                "The explicit root must be an existing doctidex root directory.",
                operation=operation,
                affected=[str(candidate)],
                actions=["Pass the exact directory whose index.md declares doctidex.root: true."],
                requires_user="doctidex_root",
                code="root_not_found",
                path=str(candidate),
            )
        if must_contain is not None and not is_within(must_contain, context.root):
            raise DoctidexError(
                "The operation path does not belong to the explicit doctidex root.",
                operation=operation,
                affected=[str(must_contain), str(context.root)],
                actions=["Pass the owner root for the operation path."],
                requires_user="doctidex_root",
                code="root_mismatch",
                path=str(must_contain),
            )
        return context

    roots = discover_roots(default)
    if must_contain is not None:
        roots = [context for context in roots if is_within(must_contain, context.root)]
    if not roots:
        raise DoctidexError(
            "No doctidex root could be selected.",
            operation=operation,
            affected=[str(default)],
            actions=["Retry with the exact doctidex root."],
            code="root_not_found",
            path=str(default),
        )
    if len(roots) > 1:
        raise DoctidexError(
            "More than one doctidex root could own this operation.",
            operation=operation,
            affected=[str(context.root) for context in roots],
            actions=["Retry with --root and the exact owner root."],
            requires_user="doctidex_root",
            code="root_ambiguous",
        )
    return roots[0]


def is_within(path: Path, root: Path) -> bool:
    try:
        Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root)))
        return True
    except ValueError:
        return False
