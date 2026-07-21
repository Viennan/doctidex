"""Pure selection expansion and boundary planning for Views."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .mounts import WikiMount, mount_for_path
from .preserved import PreservedPath, preserved_for_path
from .view_errors import fail
from .view_selection import collapse_selections
from .view_source import is_view_required_file, source_files


def add_path_view_files(
    source: Path,
    requested: list[PurePosixPath],
    stop_at: set[PurePosixPath] | None = None,
) -> list[PurePosixPath]:
    expanded = set(requested)
    stop_at = stop_at or set()
    for selection in requested:
        source_item = source.joinpath(*selection.parts)
        if not source_item.exists():
            fail(f"source item is unavailable from the immediate source: {selection}")

        owner_parts = (
            selection.parts if source_item.is_dir() else selection.parts[:-1]
        )
        for boundary in stop_at:
            if selection.parts[: len(boundary.parts)] == boundary.parts:
                owner_parts = boundary.parts[:-1]
                break
        for depth in range(len(owner_parts) + 1):
            directory = source.joinpath(*owner_parts[:depth])
            try:
                children = sorted(directory.iterdir(), key=lambda path: path.name)
            except OSError as exc:
                fail(f"cannot inspect source directory {directory}: {exc}")
            for child in children:
                if is_view_required_file(child):
                    expanded.add(PurePosixPath(*child.relative_to(source).parts))
    return collapse_selections(expanded)


def disclosed_file_coverage(
    source: Path,
    selections: list[PurePosixPath],
    files: set[PurePosixPath],
) -> set[PurePosixPath]:
    covered: set[PurePosixPath] = set()
    for selection in selections:
        item = source.joinpath(*selection.parts)
        if not item.exists():
            fail(f"source item is unavailable from the immediate source: {selection}")
        if item.is_dir():
            covered.update(
                path
                for path in files
                if path.parts[: len(selection.parts)] == selection.parts
            )
        elif selection in files:
            covered.add(selection)
    return covered


def adaptively_collapse(
    source: Path,
    selections: list[PurePosixPath],
    threshold: float,
    excluded_roots: set[PurePosixPath] | None = None,
) -> tuple[list[PurePosixPath], list[PurePosixPath]]:
    if threshold == 0:
        return selections, []

    files = source_files(source, excluded_roots)
    blocked_directories: set[PurePosixPath] = set()
    for excluded in excluded_roots or set():
        for depth in range(1, len(excluded.parts) + 1):
            blocked_directories.add(PurePosixPath(*excluded.parts[:depth]))
    totals: dict[PurePosixPath, int] = {}
    for path in files:
        for depth in range(1, len(path.parts)):
            directory = PurePosixPath(*path.parts[:depth])
            totals[directory] = totals.get(directory, 0) + 1

    original = set(selections)
    current = selections
    while True:
        covered = disclosed_file_coverage(source, current, files)
        covered_totals: dict[PurePosixPath, int] = {}
        for path in covered:
            for depth in range(1, len(path.parts)):
                directory = PurePosixPath(*path.parts[:depth])
                covered_totals[directory] = covered_totals.get(directory, 0) + 1

        candidates = {
            directory
            for directory, total in totals.items()
            if covered_totals.get(directory, 0) * 100 >= threshold * total
            and directory not in blocked_directories
        }
        combined = collapse_selections(set(current) | candidates)
        if combined == current:
            break
        current = combined

    collapsed_directories = [
        path
        for path in current
        if path not in original
        and source.joinpath(*path.parts).is_dir()
    ]
    return current, collapsed_directories


def directory_view_expansion_notice(
    source: Path,
    baseline_selections: list[PurePosixPath],
    directory: PurePosixPath,
    label: str,
    threshold: float | None = None,
    excluded_roots: set[PurePosixPath] | None = None,
) -> str:
    files = source_files(source, excluded_roots)
    covered = disclosed_file_coverage(source, baseline_selections, files)
    contained = {
        path
        for path in files
        if path.parts[: len(directory.parts)] == directory.parts
    }
    previously_covered = contained & covered
    descendant_roots = [
        selection
        for selection in baseline_selections
        if selection.parts[: len(directory.parts)] == directory.parts
    ]
    percentage = len(previously_covered) * 100 / len(contained) if contained else 100
    threshold_text = f" (threshold {threshold:g}%)" if threshold is not None else ""
    return (
        f"{label}: {directory.as_posix()} had {percentage:.1f}% visible coverage"
        f"{threshold_text}; visible content expands by "
        f"{len(contained) - len(previously_covered)} file(s), and "
        f"{len(descendant_roots)} descendant selection root(s) become one "
        "directory root"
    )


def adaptive_collapse_notices(
    source: Path,
    previous_selections: list[PurePosixPath],
    collapsed_directories: list[PurePosixPath],
    threshold: float,
    excluded_roots: set[PurePosixPath] | None = None,
) -> list[str]:
    return [
        directory_view_expansion_notice(
            source,
            previous_selections,
            directory,
            "automatic collapse",
            threshold,
            excluded_roots,
        )
        for directory in collapsed_directories
    ]


def promote_mount_selections(
    requested: list[PurePosixPath],
    mounts: list[WikiMount],
) -> tuple[list[PurePosixPath], dict[PurePosixPath, list[PurePosixPath]]]:
    promoted: set[PurePosixPath] = set()
    expansions: dict[PurePosixPath, list[PurePosixPath]] = {}
    for selection in requested:
        mount = mount_for_path(selection, mounts)
        if mount is not None and mount.projection == "mount" and selection != mount.path:
            expansions.setdefault(mount.path, []).append(selection)
            promoted.add(mount.path)
        else:
            promoted.add(selection)
    return collapse_selections(promoted), expansions


def promote_symlink_selections(
    source: Path,
    selections: list[PurePosixPath],
) -> tuple[list[PurePosixPath], dict[PurePosixPath, list[PurePosixPath]]]:
    promoted: set[PurePosixPath] = set()
    expansions: dict[PurePosixPath, list[PurePosixPath]] = {}
    for selection in selections:
        boundary: PurePosixPath | None = None
        for depth in range(1, len(selection.parts) + 1):
            candidate = PurePosixPath(*selection.parts[:depth])
            if source.joinpath(*candidate.parts).is_symlink():
                boundary = candidate
                break
        if boundary is not None and boundary != selection:
            expansions.setdefault(boundary, []).append(selection)
            promoted.add(boundary)
        else:
            promoted.add(selection)
    return collapse_selections(promoted), expansions


def promote_preserved_selections(
    selections: list[PurePosixPath],
    preserved: list[PreservedPath],
) -> tuple[list[PurePosixPath], dict[PurePosixPath, list[PurePosixPath]]]:
    promoted: set[PurePosixPath] = set()
    expansions: dict[PurePosixPath, list[PurePosixPath]] = {}
    for selection in selections:
        boundary = preserved_for_path(selection, preserved)
        if boundary is not None and selection != boundary.path:
            expansions.setdefault(boundary.path, []).append(selection)
            promoted.add(boundary.path)
        else:
            promoted.add(selection)
    return collapse_selections(promoted), expansions


def preserved_expansion_notices(
    expansions: dict[PurePosixPath, list[PurePosixPath]],
    *,
    label: str,
) -> list[str]:
    notices: list[str] = []
    for boundary, descendants in sorted(expansions.items(), key=lambda item: str(item[0])):
        names = ", ".join(path.as_posix() for path in sorted(descendants, key=str))
        notices.append(
            f"preserved boundary expansion ({label}): [{names}] selects whole "
            f"boundary {boundary.as_posix()}"
        )
    return notices


def boundary_expansion_notices(
    expansions: dict[PurePosixPath, list[PurePosixPath]],
    *,
    boundary_type: str,
) -> list[str]:
    notices: list[str] = []
    for boundary, descendants in sorted(expansions.items(), key=lambda item: str(item[0])):
        names = ", ".join(path.as_posix() for path in sorted(descendants, key=str))
        notices.append(
            f"{boundary_type} promotion: [{names}] materializes whole "
            f"boundary {boundary.as_posix()}"
        )
    return notices
