"""Filesystem preflight and mutation primitives for Views."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath

from .model import STATUS_FILENAME
from .view_errors import fail
from .view_selection import collapse_selections
from .view_status import (
    list_disclosed_symlinks,
    logical_link_target,
    resolved_link_target,
)


def prepare_parent_directories(
    output_root: Path,
    relative: PurePosixPath,
    source: Path,
    create: bool,
    relocated_source: Path | None = None,
) -> bool:
    if os.path.lexists(output_root):
        if output_root.is_symlink():
            fail(f"View root must not be a symlink: {output_root}")
        if not output_root.is_dir():
            fail(f"View root is not a directory: {output_root}")
    elif create:
        output_root.mkdir(parents=True)

    current = output_root
    for index, part in enumerate(relative.parts[:-1], start=1):
        current /= part
        expected = expected_source_path(
            source,
            PurePosixPath(*relative.parts[:index]),
        )
        if os.path.lexists(current):
            if current.is_symlink():
                actual = logical_link_target(current)
                if (
                    actual != expected
                    and resolved_link_target(current) != expected.resolve(strict=False)
                ):
                    relocated = (
                        Path(
                            os.path.abspath(
                                relocated_source.joinpath(*relative.parts[:index])
                            )
                        )
                        if relocated_source
                        else None
                    )
                    if actual != relocated and not (
                        relocated is not None
                        and resolved_link_target(current) == relocated.resolve(strict=False)
                    ):
                        fail(f"target symlink collision: {current}")
                return False
            if not current.is_dir():
                fail(f"target path is not a directory: {current}")
        elif create:
            current.mkdir()
    return True


def expected_source_path(source: Path, relative: PurePosixPath) -> Path:
    expected = Path(os.path.abspath(source.joinpath(*relative.parts)))
    if not expected.exists():
        fail(f"source item is unavailable from the immediate source: {relative}")
    return expected


def link_matches_source(
    link: Path,
    relative: PurePosixPath,
    source: Path,
    relocated_source: Path | None = None,
) -> bool:
    actual = logical_link_target(link)
    expected = expected_source_path(source, relative)
    if actual == expected or resolved_link_target(link) == expected.resolve(strict=False):
        return True
    if relocated_source is None:
        return False
    relocated = Path(os.path.abspath(relocated_source.joinpath(*relative.parts)))
    return actual == relocated or resolved_link_target(link) == relocated.resolve(strict=False)


def disclosed_selections(
    source: Path,
    output_root: Path,
    relocated_source: Path | None = None,
) -> list[PurePosixPath]:
    selections: list[PurePosixPath] = []
    for directory, dirnames, filenames in os.walk(output_root, followlinks=False):
        current = Path(directory)
        if current != output_root:
            relative_directory = PurePosixPath(*current.relative_to(output_root).parts)
            if not expected_source_path(source, relative_directory).is_dir():
                fail(f"View contains an unexpected container directory: {current}")
        for name in filenames:
            candidate = current / name
            if candidate.is_symlink():
                continue
            if current == output_root and name == STATUS_FILENAME:
                continue
            fail(f"target collision: View contains non-generated content: {candidate}")
    for relative_text in list_disclosed_symlinks(output_root):
        relative = PurePosixPath(relative_text)
        link = output_root.joinpath(*relative.parts)
        if not link_matches_source(link, relative, source, relocated_source):
            fail(f"generated symlink does not match the active source: {link}")
        selections.append(relative)
    return collapse_selections(set(selections))


def validate_collapsible_directory(
    directory: Path,
    source: Path,
    output_root: Path,
    relocated_source: Path | None = None,
) -> None:
    pending = [directory]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda path: path.name)
        except OSError as exc:
            fail(f"cannot inspect View container {current}: {exc}")
        for child in children:
            relative = PurePosixPath(*child.relative_to(output_root).parts)
            if child.is_symlink():
                if not link_matches_source(
                    child,
                    relative,
                    source,
                    relocated_source,
                ):
                    fail(f"cannot collapse directory with unexpected symlink: {child}")
                continue
            if child.is_dir():
                expected = expected_source_path(source, relative)
                if not expected.is_dir():
                    fail(f"cannot collapse unexpected container directory: {child}")
                pending.append(child)
                continue
            fail(f"cannot collapse directory with non-generated content: {child}")


def collapse_directory_to_link(
    output_item: Path,
    resolved_item: Path,
    output_root: Path,
) -> str:
    try:
        backup_root = Path(
            tempfile.mkdtemp(
                prefix=".whero-collapse-",
                dir=output_root.parent,
            )
        )
    except OSError as exc:
        fail(f"cannot prepare directory collapse for {output_item}: {exc}")
    backup_item = backup_root / "previous"
    link_target = os.path.relpath(resolved_item, start=output_item.parent)
    try:
        os.replace(output_item, backup_item)
    except OSError as exc:
        try:
            shutil.rmtree(backup_root)
        except OSError:
            pass
        fail(f"cannot collapse View directory {output_item}: {exc}")

    try:
        output_item.symlink_to(link_target, target_is_directory=True)
    except OSError as link_error:
        try:
            os.replace(backup_item, output_item)
        except OSError as restore_error:
            fail(
                f"cannot create collapsed link {output_item}: {link_error}; "
                f"automatic restore also failed: {restore_error}; "
                f"backup retained at {backup_item}"
            )
        try:
            shutil.rmtree(backup_root)
        except OSError:
            pass
        fail(f"cannot create collapsed link {output_item}: {link_error}")

    try:
        shutil.rmtree(backup_root)
    except OSError as exc:
        print(
            f"warning: collapsed {output_item}, but could not remove backup "
            f"{backup_root}: {exc}",
            file=sys.stderr,
        )
    return f"collapsed {output_item} -> {link_target}"


def create_link(
    source: Path,
    output_root: Path,
    relative: PurePosixPath,
    dry_run: bool,
    relocated_source: Path | None = None,
) -> str:
    source_item = expected_source_path(source, relative)

    output_item = output_root.joinpath(*relative.parts)
    if not prepare_parent_directories(
        output_root,
        relative,
        source,
        create=not dry_run,
        relocated_source=relocated_source,
    ):
        return f"covered by existing directory link: {output_item}"

    if os.path.lexists(output_item):
        if output_item.is_symlink():
            actual = logical_link_target(output_item)
            if actual == source_item:
                return f"already linked: {output_item}"
            if resolved_link_target(output_item) == source_item.resolve(strict=False):
                if dry_run:
                    return f"would relink {output_item} -> {source_item}"
                desired_target = os.path.relpath(source_item, start=output_item.parent)
                temporary = output_item.with_name(
                    f".{output_item.name}.whero-relink-{os.getpid()}"
                )
                temporary.symlink_to(
                    desired_target,
                    target_is_directory=source_item.is_dir(),
                )
                os.replace(temporary, output_item)
                return f"relinked {output_item} -> {desired_target}"
            if relocated_source:
                relocated_item = Path(
                    os.path.abspath(relocated_source.joinpath(*relative.parts))
                )
                if actual == relocated_item:
                    return f"covered by planned source relocation: {output_item}"
        elif output_item.is_dir() and source_item.is_dir():
            validate_collapsible_directory(
                output_item,
                source,
                output_root,
                relocated_source,
            )
            if dry_run:
                return f"would collapse {output_item} -> {source_item}"
            return collapse_directory_to_link(output_item, source_item, output_root)
        fail(f"target collision: {output_item}")

    if dry_run:
        return f"would link {output_item} -> {source_item}"

    link_target = os.path.relpath(source_item, start=output_item.parent)
    output_item.symlink_to(link_target, target_is_directory=source_item.is_dir())
    return f"linked {output_item} -> {link_target}"
