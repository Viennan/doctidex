"""Structured planning and execution service for Whero Wiki Views."""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath

from .model import is_view_root
from .mounts import discover_boundaries, mount_for_path
from .paths import is_within
from .view_errors import fail
from .view_executor import create_link, disclosed_selections
from .view_git import git_source_identity, validate_git_worktree_disclosure
from .view_planner import (
    adaptive_collapse_notices,
    adaptively_collapse,
    add_path_view_files,
    boundary_expansion_notices,
    directory_view_expansion_notice,
    promote_mount_selections,
    promote_preserved_selections,
    promote_symlink_selections,
    preserved_expansion_notices,
)
from .view_selection import (
    collapse_selections,
    infer_source,
    load_selections,
    resolve_source,
)
from .view_source import validate_wiki_meta
from .view_status import refresh_source_symlinks, validate_existing_status, write_status
from .view_types import OperationResult, ViewPlan, ViewRequest


def _promote_effective_roots(
    source: Path,
    selections: list[PurePosixPath],
    preserved: list,
    mounts: list,
) -> tuple[
    list[PurePosixPath],
    dict[PurePosixPath, list[PurePosixPath]],
    dict[PurePosixPath, list[PurePosixPath]],
    dict[PurePosixPath, list[PurePosixPath]],
]:
    promoted, preserved_expansions = promote_preserved_selections(selections, preserved)
    promoted, mount_expansions = promote_mount_selections(promoted, mounts)
    promoted, symlink_expansions = promote_symlink_selections(source, promoted)
    return promoted, preserved_expansions, mount_expansions, symlink_expansions


def plan_view(request: ViewRequest) -> ViewPlan:
    source = resolve_source(request.source) if request.source else infer_source(
        request.includes,
        request.include_files,
    )
    validate_wiki_meta(source)

    target_parent = request.target.expanduser().absolute()
    output_root = target_parent / (request.view_name or source.name)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output == source or is_within(resolved_output, source):
        fail("--target must not place the View inside its source Wiki")
    if os.path.lexists(output_root):
        if output_root.is_symlink():
            fail(f"View root must not be a symlink: {output_root}")
        if not output_root.is_dir():
            fail(f"View root is not a directory: {output_root}")

    git_source = git_source_identity(source)
    status_state = validate_existing_status(
        source,
        git_source,
        output_root,
        allow_path_relocation=request.allow_path_relocation,
    )
    requested_now = load_selections(source, request.includes, request.include_files)
    mounts, preserved, boundary_problems = discover_boundaries(source)
    if boundary_problems:
        fail(boundary_problems[0])
    for selection in requested_now:
        if source.joinpath(*selection.parts).exists():
            continue
        mount = mount_for_path(selection, mounts)
        guidance = (
            "; restore the declared external reference first"
            if mount is not None and mount.index is not None
            else ""
        )
        fail(
            "source item is unavailable from the immediate source: "
            f"{selection}{guidance}"
        )
    source_is_view = is_view_root(source)
    for entry in preserved:
        if not entry.root.exists():
            if source_is_view:
                continue
            fail(f"declared preserved path does not exist: {entry.path}")

    relocated_source = status_state.previous_source if status_state.source_moved else None
    existing = disclosed_selections(source, output_root, relocated_source)
    stored_requested = list(status_state.requested_selections)
    requested_all = collapse_selections(set(stored_requested) | set(requested_now))

    requested_effective, requested_preserved, requested_mounts, requested_symlinks = (
        _promote_effective_roots(source, requested_all, preserved, mounts)
    )
    existing_effective, existing_preserved, existing_mounts, existing_symlinks = (
        _promote_effective_roots(source, existing, preserved, mounts)
    )
    protected_roots = {entry.path for entry in preserved} | {
        mount.path for mount in mounts
    } | set(requested_symlinks) | set(existing_symlinks)
    expanded = add_path_view_files(
        source,
        collapse_selections(set(existing_effective) | set(requested_effective)),
        protected_roots,
    )
    pre_collapse_selections = expanded
    selections, adaptive_directories = adaptively_collapse(
        source,
        expanded,
        request.collapse_threshold,
        protected_roots,
    )
    validate_git_worktree_disclosure(source, git_source, selections)

    notices: list[str] = []
    if status_state.git_notice:
        notices.append(status_state.git_notice)
    notices.extend(
        preserved_expansion_notices(requested_preserved, label="requested selection")
    )
    notices.extend(
        preserved_expansion_notices(existing_preserved, label="existing View")
    )
    notices.extend(boundary_expansion_notices(requested_mounts, boundary_type="Mount"))
    notices.extend(boundary_expansion_notices(existing_mounts, boundary_type="existing Mount"))
    notices.extend(
        boundary_expansion_notices(requested_symlinks, boundary_type="source symlink")
    )
    notices.extend(
        boundary_expansion_notices(existing_symlinks, boundary_type="existing source symlink")
    )
    notices.extend(
        adaptive_collapse_notices(
            source,
            pre_collapse_selections,
            adaptive_directories,
            request.collapse_threshold,
            protected_roots,
        )
    )
    explicit_directory_collapses = [
        selection
        for selection in selections
        if selection in requested_effective
        and source.joinpath(*selection.parts).is_dir()
        and any(
            existing_root.parts[: len(selection.parts)] == selection.parts
            and existing_root != selection
            for existing_root in existing
        )
    ]
    notices.extend(
        directory_view_expansion_notice(
            source,
            existing,
            directory,
            "requested parent collapse",
            excluded_roots=protected_roots,
        )
        for directory in explicit_directory_collapses
    )

    relink_plan: list[str] = []
    if status_state.source_moved:
        assert status_state.previous_source is not None
        relink_plan = refresh_source_symlinks(
            status_state.previous_source,
            source,
            output_root,
            True,
        )
    link_plan = [
        create_link(source, output_root, selection, True, relocated_source)
        for selection in selections
    ]
    return ViewPlan(
        request=request,
        source=source,
        output_root=output_root,
        git_source=git_source,
        status=status_state,
        relocated_source=relocated_source,
        requested_selections=tuple(requested_all),
        selections=tuple(selections),
        notices=tuple(notices),
        relink_plan=tuple(relink_plan),
        link_plan=tuple(link_plan),
    )


def execute_view(request: ViewRequest) -> OperationResult:
    plan = plan_view(request)
    messages = list(plan.notices)
    if request.dry_run:
        planned_links = sum(
            message.startswith(("would link ", "would collapse ", "would relink "))
            for message in plan.link_plan
        )
        status_action = write_status(
            plan.source,
            plan.git_source,
            plan.output_root,
            plan.requested_selections,
            plan.selections,
            request.collapse_threshold,
            True,
        )
        messages.append(
            f"dry-run summary: {planned_links} link/collapse action(s), "
            f"{len(plan.relink_plan)} source relink(s), {status_action}"
        )
        return OperationResult(tuple(messages))

    mutated = False
    relink_complete = not plan.status.source_moved
    try:
        if plan.status.source_moved:
            assert plan.status.previous_source is not None
            relink_messages = refresh_source_symlinks(
                plan.status.previous_source,
                plan.source,
                plan.output_root,
                False,
            )
            relink_complete = True
            mutated = mutated or bool(relink_messages)
            if relink_messages:
                messages.append(
                    f"source relocation: updated {len(relink_messages)} "
                    "generated symlink(s)"
                )

        for selection in plan.selections:
            message = create_link(plan.source, plan.output_root, selection, False)
            if message.startswith(("linked ", "collapsed ", "relinked ")):
                mutated = True
        write_status(
            plan.source,
            plan.git_source,
            plan.output_root,
            plan.requested_selections,
            plan.selections,
            request.collapse_threshold,
            False,
        )
        mutated = True
    except (SystemExit, OSError) as operation_error:
        if mutated and relink_complete:
            try:
                effective = tuple(disclosed_selections(plan.source, plan.output_root))
                recovery = write_status(
                    plan.source,
                    plan.git_source,
                    plan.output_root,
                    plan.requested_selections,
                    effective,
                    request.collapse_threshold,
                    False,
                )
                print(
                    f"warning: recovered View metadata after failure: {recovery}",
                    file=sys.stderr,
                )
            except (SystemExit, OSError) as recovery_error:
                print(
                    "warning: View links remain readable, but metadata recovery "
                    f"failed: {recovery_error}",
                    file=sys.stderr,
                )
        if isinstance(operation_error, SystemExit):
            raise
        fail(f"cannot update View: {operation_error}")
    return OperationResult(tuple(messages), mutated)
