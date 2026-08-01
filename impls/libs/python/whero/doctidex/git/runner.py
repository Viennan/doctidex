from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.errors import DoctidexError


@dataclass(frozen=True, slots=True)
class GitResult:
    stdout: str
    stderr: str
    returncode: int


def git(
    arguments: Iterable[str],
    *,
    cwd: Path | None = None,
    operation: str = "git",
    check: bool = True,
) -> GitResult:
    environment = os.environ.copy()
    environment.setdefault("GIT_TERMINAL_PROMPT", "0")
    process = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    result = GitResult(process.stdout, process.stderr, process.returncode)
    if check and process.returncode:
        raise _git_error(result, operation)
    return result


def _git_error(result: GitResult, operation: str) -> DoctidexError:
    message = (result.stderr or result.stdout or "Git command failed").strip()
    lowered = message.lower()
    if any(
        fragment in lowered
        for fragment in ("authentication", "permission denied", "could not read username", "access denied")
    ):
        return DoctidexError(
            "The remote repository requires credentials.",
            operation=operation,
            actions=["Obtain repository access.", "Retry the explicit operation after access is available."],
            requires_user="repository_access",
            code="source_access_failed",
            domain="external",
            network=True,
        )
    if any(
        fragment in lowered
        for fragment in (
            "could not resolve host",
            "network is unreachable",
            "failed to connect",
            "connection timed out",
        )
    ):
        return DoctidexError(
            "The external directory tree cannot currently be reached over the network.",
            operation=operation,
            actions=[
                "Continue with an existing effective commit if available.",
                "Retry when network access is available.",
            ],
            requires_user="network_access",
            code="source_access_failed",
            domain="external",
            network=True,
        )
    if any(
        fragment in lowered
        for fragment in ("couldn't find remote ref", "not a valid object name", "unknown revision", "bad object")
    ):
        return DoctidexError(
            "The declared Git revision does not exist or cannot be resolved.",
            operation=operation,
            actions=["Confirm the commit, tag, or branch and retry."],
            requires_user="revision",
            code="revision_not_found",
            domain="external",
        )
    return DoctidexError(
        "Git could not complete the requested source operation.",
        operation=operation,
        actions=["Inspect the repository state and retry the explicit operation."],
        code="source_access_failed",
        domain="external",
    )
