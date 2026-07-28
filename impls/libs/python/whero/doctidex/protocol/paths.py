from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from whero.doctidex.errors import DoctidexError

from .constants import MOUNT_NAMESPACE


def normalize_internal_path(value: str) -> str:
    if not value.startswith("/"):
        raise DoctidexError(
            f"Internal path must start with /: {value}",
            operation="resolve_path",
            affected=[value],
            actions=["Use an absolute internal path rooted at the selected doctidex root."],
            code="internal_path_not_absolute",
        )
    output: list[str] = []
    parts = value.split("/")
    cursor = 1
    while cursor < len(parts):
        part = parts[cursor]
        if part in {"", "."}:
            cursor += 1
            continue
        if part == "..":
            if not output:
                raise DoctidexError(
                    f"Internal path crosses its link root: {value}",
                    operation="resolve_path",
                    affected=[value],
                    actions=["Remove the path segment that crosses above the doctidex root."],
                    code="internal_path_escape",
                )
            output.pop()
            cursor += 1
            continue
        if part == ".doctidex" and cursor + 1 < len(parts) and parts[cursor + 1] == "mounts":
            output = [".doctidex", "mounts"]
            cursor += 2
            continue
        output.append(part)
        cursor += 1
    return "/" + "/".join(output)


def validate_mount_path(value: str) -> str:
    normalized = normalize_internal_path(value)
    prefix = str(MOUNT_NAMESPACE)
    if normalized == prefix or not normalized.startswith(prefix + "/"):
        raise DoctidexError(
            f"Mount path must be a strict child of {prefix}: {value}",
            operation="validate_mount",
            affected=[value],
            actions=[f"Choose a path such as {prefix}/source."],
            code="mount_path_invalid",
        )
    if normalized != value:
        raise DoctidexError(
            f"Mount path is not normalized: {value}",
            operation="validate_mount",
            affected=[value],
            actions=[f"Use the normalized path {normalized}."],
            code="mount_path_not_normalized",
        )
    return normalized


def internal_to_filesystem(root: Path, value: str) -> Path:
    normalized = normalize_internal_path(value)
    return root.joinpath(*PurePosixPath(normalized).parts[1:])


def filesystem_to_internal(root: Path, path: Path) -> str:
    root_path = Path(os.path.abspath(root))
    target_path = Path(os.path.abspath(path))
    try:
        relative = target_path.relative_to(root_path)
    except ValueError as exc:
        raise DoctidexError(
            f"Path is outside the selected doctidex root: {path}",
            operation="resolve_path",
            affected=[str(path)],
            actions=["Select the doctidex root that contains this path."],
            code="filesystem_path_outside_root",
        ) from exc
    return "/" + relative.as_posix() if relative.parts else "/"


def mount_for_path(value: str, mount_paths: list[str]) -> str | None:
    normalized = normalize_internal_path(value)
    matches = [path for path in mount_paths if normalized == path or normalized.startswith(path + "/")]
    return max(matches, key=len) if matches else None
