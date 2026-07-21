"""Caller-friendly input parsing and canonical View selections."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath

from .model import STATUS_FILENAME, WIKI_META_FILENAME
from .paths import is_within
from .view_errors import fail


DEFAULT_COLLAPSE_THRESHOLD = 80.0


def _selection_candidate(
    source: Path,
    candidate: Path,
) -> tuple[PurePosixPath, bool] | None:
    logical = Path(os.path.abspath(candidate.expanduser()))
    selected = logical
    if not is_within(selected, source):
        try:
            resolved = logical.resolve(strict=False)
        except OSError:
            return None
        if not is_within(resolved, source):
            return None
        selected = resolved
    try:
        relative = selected.relative_to(source)
    except ValueError:
        return None
    if not relative.parts:
        return PurePosixPath("."), os.path.lexists(logical)
    return PurePosixPath(*relative.parts), os.path.lexists(logical)


def find_wiki_roots(path: Path) -> tuple[Path, ...]:
    candidate = Path(os.path.abspath(path.expanduser()))
    if not candidate.is_dir():
        candidate = candidate.parent
    return tuple(
        directory
        for directory in (candidate, *candidate.parents)
        if (directory / WIKI_META_FILENAME).is_file()
    )


def find_wiki_root(path: Path) -> Path | None:
    roots = find_wiki_roots(path)
    return roots[0] if roots else None


def resolve_source(raw: Path) -> Path:
    candidate = raw.expanduser().absolute()
    root = find_wiki_root(candidate)
    if root is None:
        fail(f"cannot find {WIKI_META_FILENAME} at or above source path: {raw}")
    return root.resolve(strict=True)


def infer_source(values: tuple[str, ...], files: tuple[Path, ...]) -> Path:
    candidates: list[Path] = []
    for value in values:
        supplied = Path(value.strip()).expanduser()
        if supplied.is_absolute():
            candidates.append(supplied)
        else:
            candidates.append(Path.cwd() / supplied)
    for selection_file in files:
        resolved_file = selection_file.expanduser().resolve(strict=True)
        for line in resolved_file.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            supplied = Path(value).expanduser()
            candidates.append(
                supplied if supplied.is_absolute() else resolved_file.parent / supplied
            )
    root_sets = [
        {root.resolve(strict=True) for root in find_wiki_roots(candidate)}
        for candidate in candidates
    ]
    root_sets = [roots for roots in root_sets if roots]
    if not root_sets:
        fail("cannot infer source Wiki; pass --source or select a path inside a Wiki")
    common = set.intersection(*root_sets)
    if len(common) != 1:
        candidates_text = ", ".join(
            str(root)
            for root in sorted(set.union(*root_sets), key=str)
        )
        fail(
            "source Wiki is ambiguous across containing roots: "
            f"[{candidates_text}]; pass --source for the intended lifecycle"
        )
    return next(iter(common))


def parse_selection(
    raw: str,
    source: Path,
    *,
    additional_bases: list[Path] | None = None,
) -> PurePosixPath:
    value = raw.strip()
    if not value:
        fail("include paths must not be empty")
    supplied = Path(value).expanduser()
    raw_candidates = (
        [supplied]
        if supplied.is_absolute()
        else [
            source / supplied,
            Path.cwd() / supplied,
            *((base / supplied) for base in additional_bases or []),
        ]
    )
    candidate_states = {
        candidate: exists
        for raw_candidate in raw_candidates
        if (parsed := _selection_candidate(source, raw_candidate)) is not None
        for candidate, exists in [parsed]
    }
    if not candidate_states:
        fail(f"include path must resolve inside the source Wiki: {raw!r}")
    existing = {path for path, exists in candidate_states.items() if exists}
    candidates = existing or set(candidate_states)
    if len(candidates) > 1:
        names = ", ".join(path.as_posix() for path in sorted(candidates, key=str))
        fail(
            "include path is ambiguous across valid base directories: "
            f"{raw!r} -> [{names}]; use an absolute path"
        )
    result = next(iter(candidates))
    if result == PurePosixPath("."):
        fail("include path must identify an item below the source Wiki root")
    if result.name == STATUS_FILENAME and len(result.parts) == 1:
        fail(f"{result.name} is generated and cannot be selected from source")
    return result


def parse_collapse_threshold(raw: str) -> float:
    value = raw.strip()
    percent_form = value.endswith("%")
    if percent_form:
        value = value[:-1]
    try:
        threshold = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid collapse threshold: {raw!r}")
    if not percent_form and 0 < threshold <= 1:
        threshold *= 100
    if not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("collapse threshold must be between 0 and 100")
    return threshold


def parse_view_name(raw: str) -> str:
    value = raw.strip()
    path = PurePosixPath(value)
    if not value or path.is_absolute() or len(path.parts) != 1 or value in (".", ".."):
        raise argparse.ArgumentTypeError(
            "view name must be one non-empty directory name"
        )
    return value


def collapse_selections(paths: set[PurePosixPath]) -> list[PurePosixPath]:
    ordered = sorted(paths, key=lambda path: (len(path.parts), str(path)))
    collapsed: list[PurePosixPath] = []
    for candidate in ordered:
        if any(
            candidate.parts[: len(parent.parts)] == parent.parts
            for parent in collapsed
        ):
            continue
        collapsed.append(candidate)
    return collapsed


def load_selections(
    source: Path,
    values: tuple[str, ...],
    files: tuple[Path, ...],
) -> list[PurePosixPath]:
    selections = {parse_selection(value, source) for value in values}
    for selection_file in files:
        try:
            resolved_file = selection_file.expanduser().resolve(strict=True)
            lines = resolved_file.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            fail(f"cannot read include file {selection_file}: {exc}")
        selections.update(
            parse_selection(
                line.strip(),
                source,
                additional_bases=[resolved_file.parent],
            )
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
    if not selections:
        fail("provide at least one --include or --include-from path")
    return collapse_selections(selections)
