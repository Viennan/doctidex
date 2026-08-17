"""Repository-internal path normalization for command workflows."""

from __future__ import annotations

import posixpath
from pathlib import Path

from whero.doctidex.errors import CommandFailure


def normalize_repo_path(value: str, *, parameter: str) -> str:
    if not value.startswith("/"):
        raise CommandFailure(
            code="repository-path.invalid",
            summary="The path must be an absolute path within the Git root.",
            subject={"kind": "repository-path", "path": value},
            details={
                "parameter": parameter,
                "path": value,
                "normalized-path": None,
                "constraint": "repository-internal-absolute-path",
            },
        )
    depth = 0
    for part in value.split("/"):
        if not part or part == ".":
            continue
        if part == "..":
            depth -= 1
            if depth < 0:
                raise CommandFailure(
                    code="repository-path.invalid",
                    summary="The path must not escape the Git root.",
                    subject={"kind": "repository-path", "path": value},
                    details={
                        "parameter": parameter,
                        "path": value,
                        "normalized-path": None,
                        "constraint": "within-git-root",
                    },
                )
            continue
        depth += 1
    normalized = posixpath.normpath(value)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized


def repo_path_to_fs(git_root: Path, repo_path: str) -> Path:
    return git_root / repo_path.lstrip("/")
