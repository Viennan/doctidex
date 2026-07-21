"""View metadata validation, relocation, inventory, and atomic writes."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Any

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, write_markdown_atomic
from .model import (
    FORMAT_VERSION,
    STATUS_FILENAME,
    is_view_metadata,
    view_status_path,
)
from .view_errors import fail
from .view_git import recorded_git_path, validate_git_transition
from .view_source import decode_frontmatter_string, read_view_frontmatter
from .view_types import ExistingStatus, GitSource


def resolve_recorded_source(value: str, status_directory: Path) -> Path:
    recorded = Path(decode_frontmatter_string(value)).expanduser()
    if not recorded.is_absolute():
        recorded = status_directory / recorded
    return recorded.resolve(strict=False)


def _stored_paths(fields: dict[str, Any], key: str, status: Path) -> tuple[PurePosixPath, ...]:
    raw = fields.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        fail(f"{key} must be a list of relative paths: {status}")
    paths: list[PurePosixPath] = []
    for item in raw:
        path = PurePosixPath(item)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in ("", ".", "..") for part in path.parts)
        ):
            fail(f"invalid {key} path in {status}: {item!r}")
        paths.append(path)
    return tuple(paths)


def list_disclosed_symlinks(output_root: Path) -> list[str]:
    disclosed: list[str] = []
    for directory, dirnames, filenames in os.walk(output_root, followlinks=False):
        current = Path(directory)
        for name in [*dirnames, *filenames]:
            candidate = current / name
            if candidate.is_symlink():
                disclosed.append(candidate.relative_to(output_root).as_posix())
    return sorted(set(disclosed))


def validate_existing_status(
    source: Path,
    git_source: GitSource | None,
    output_root: Path,
    *,
    allow_path_relocation: bool = False,
) -> ExistingStatus:
    try:
        status = view_status_path(output_root)
    except WheroToolError as exc:
        fail(str(exc))
    if status is None:
        return ExistingStatus(None, False)
    if status.is_symlink() or not status.is_file():
        fail(f"View metadata path is not a generated regular file: {status}")
    fields = read_view_frontmatter(status)
    try:
        valid_view = is_view_metadata(fields)
    except WheroToolError as exc:
        fail(str(exc))
    if not valid_view:
        fail(f"existing metadata file does not identify a Whero Wiki View: {status}")
    if fields.get("type") != "Whero Wiki View" or str(
        fields.get("format_version", "")
    ) != FORMAT_VERSION:
        fail(f"View metadata has invalid type or format version: {status}")
    if not frontmatter_is_true(fields, "whero_maintenance") or not frontmatter_is_true(
        fields, "whero_view_required"
    ):
        fail(f"View metadata is missing required framework flags: {status}")
    for required_paths in ("requested_selections", "effective_roots"):
        if required_paths not in fields:
            fail(f"View metadata has no {required_paths}: {status}")

    if not fields.get("source"):
        fail(f"existing View metadata has no source: {status}")
    recorded_source = resolve_recorded_source(fields["source"], output_root)
    requested = _stored_paths(fields, "requested_selections", status)
    effective = _stored_paths(fields, "effective_roots", status)
    validation_mode = fields.get("source_validation", "path")
    if validation_mode == "git-commit":
        recorded_commit = decode_frontmatter_string(fields.get("source_commit", ""))
        if not recorded_commit:
            fail(f"git-commit View metadata has no source_commit: {status}")
        if git_source is None:
            fail("existing View requires a Git-controlled source")
        previous_git_path = recorded_git_path(fields, recorded_source, git_source)
        disclosed_roots = [
            PurePosixPath(path) for path in list_disclosed_symlinks(output_root)
        ]
        notice = validate_git_transition(
            git_source,
            recorded_commit.lower(),
            previous_git_path,
            disclosed_roots,
        )
        recorded_remote = decode_frontmatter_string(
            fields.get("source_git_remote_normalized", "")
        )
        current_remote = git_source.remote.normalized_url if git_source.remote else ""
        if recorded_remote and current_remote and recorded_remote != current_remote:
            remote_notice = (
                "Git remote metadata changed from "
                f"{recorded_remote} to {current_remote}; source identity still uses "
                "the validated commit and tree"
            )
            notice = f"{notice}\n{remote_notice}" if notice else remote_notice
        return ExistingStatus(
            recorded_source,
            recorded_source != source,
            notice,
            requested,
            effective,
        )

    if validation_mode != "path":
        fail(f"unsupported source_validation mode: {validation_mode}")
    if recorded_source != source:
        if allow_path_relocation:
            return ExistingStatus(
                recorded_source,
                True,
                "path-identified source relocation was explicitly approved",
                requested,
                effective,
            )
        fail(
            "existing View uses a different source: "
            f"recorded {recorded_source}, supplied {source}"
        )
    return ExistingStatus(
        recorded_source,
        False,
        None,
        requested,
        effective,
    )


def logical_link_target(link: Path) -> Path:
    raw_target = Path(os.readlink(link))
    if not raw_target.is_absolute():
        raw_target = link.parent / raw_target
    return Path(os.path.abspath(raw_target))


def resolved_link_target(link: Path) -> Path:
    return logical_link_target(link).resolve(strict=False)


def refresh_source_symlinks(
    previous_source: Path,
    source: Path,
    output_root: Path,
    dry_run: bool,
) -> list[str]:
    messages: list[str] = []
    for relative_text in list_disclosed_symlinks(output_root):
        relative = PurePosixPath(relative_text)
        link = output_root.joinpath(*relative.parts)
        previous_item = previous_source.joinpath(*relative.parts)
        source_item = source.joinpath(*relative.parts)
        if not os.path.lexists(source_item):
            fail(f"relocated source item does not exist: {relative}")
        actual = logical_link_target(link)
        if actual == Path(os.path.abspath(source_item)):
            continue
        if (
            actual != Path(os.path.abspath(previous_item))
            and resolved_link_target(link) != previous_item.resolve(strict=False)
        ):
            fail(f"generated symlink no longer matches recorded source: {link}")

        desired_target = os.path.relpath(source_item, start=link.parent)
        if dry_run:
            messages.append(f"would relink {link} -> {desired_target}")
            continue

        temporary = link.with_name(f".{link.name}.whero-relink-{os.getpid()}")
        if os.path.lexists(temporary):
            fail(f"temporary relink path already exists: {temporary}")
        try:
            temporary.symlink_to(desired_target, target_is_directory=source_item.is_dir())
            os.replace(temporary, link)
        except OSError as exc:
            if os.path.lexists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            fail(f"cannot update generated symlink {link}: {exc}")
        messages.append(f"relinked {link} -> {desired_target}")
    return messages


def write_status(
    source: Path,
    git_source: GitSource | None,
    output_root: Path,
    requested_selections: tuple[PurePosixPath, ...],
    effective_roots: tuple[PurePosixPath, ...],
    collapse_threshold: float,
    dry_run: bool,
) -> str:
    status = output_root / STATUS_FILENAME
    if dry_run:
        existing = status.exists()
        action = "update" if existing else "create"
        return f"would {action} View metadata {status}"

    relative_source = os.path.relpath(source, start=output_root)
    validation_mode = "git-commit" if git_source else "path"
    fields: dict[str, Any] = {
        "type": "Whero Wiki View",
        "title": "Whero Wiki View",
        "description": "Structure-preserving View of selected Whero Wiki material.",
        "format_version": FORMAT_VERSION,
        "whero_maintenance": True,
        "whero_view_required": True,
        "whero_view": True,
        "source": relative_source,
        "source_validation": validation_mode,
        "layout": "source-relative",
        "view_name": output_root.name,
        "collapse_threshold": collapse_threshold,
        "requested_selections": [path.as_posix() for path in requested_selections],
        "effective_roots": [path.as_posix() for path in effective_roots],
        "disclosed_symlinks": len(list_disclosed_symlinks(output_root)),
    }
    if git_source:
        fields["source_commit"] = git_source.commit
        fields["source_git_path"] = git_source.wiki_path.as_posix()
        if git_source.remote:
            fields["source_git_remote_name"] = git_source.remote.name
            fields["source_git_remote_url"] = git_source.remote.fetch_url
            fields["source_git_remote_normalized"] = git_source.remote.normalized_url
    body = (
        "\n# Whero Wiki View\n\n"
        "This directory is a structure-preserving View of its immediate source.\n"
        "Requested selections record caller intent; effective roots record the\n"
        "materialized projection after boundary promotion and collapse.\n"
    )
    try:
        write_markdown_atomic(status, fields, body, overwrite=True)
    except (OSError, WheroToolError) as exc:
        fail(f"cannot write View metadata {status}: {exc}")
    return f"wrote View metadata {status}"
