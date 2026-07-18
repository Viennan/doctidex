"""Git identity, remote, and changed-path helpers for Whero tooling."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import WheroToolError


@dataclass(frozen=True)
class GitRemote:
    name: str
    fetch_url: str
    normalized_url: str


def git_output(directory: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def repository_root(path: Path) -> Path | None:
    output = git_output(path, "rev-parse", "--show-toplevel")
    return Path(output).resolve(strict=False) if output else None


def head_commit(path: Path) -> str | None:
    return git_output(path, "rev-parse", "HEAD")


def sanitize_remote_url(url: str) -> str | None:
    value = url.strip()
    if not value:
        return None
    value = re.sub(r"^(https?://)[^/@]+@", r"\1", value)
    value = re.sub(r"^(ssh://)[^/@]+@", r"\1", value)
    if re.search(r"(?:token|password|passwd|oauth|access_key)=", value, re.I):
        value = value.split("?", 1)[0]
    return value


def normalize_remote_url(url: str) -> str:
    value = sanitize_remote_url(url) or ""
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value, flags=re.I)
    value = re.sub(r"^[^@/]+@", "", value)
    value = value.replace(":", "/", 1) if ":" in value.split("/", 1)[0] else value
    return value.removesuffix(".git").rstrip("/")


def preferred_remote(path: Path) -> GitRemote | None:
    branch = git_output(path, "symbolic-ref", "--quiet", "--short", "HEAD")
    remote_name = None
    if branch:
        remote_name = git_output(path, "config", f"branch.{branch}.remote")
    candidates = [name for name in (remote_name, "origin") if name and name != "."]
    candidates.extend(
        name
        for name in (git_output(path, "remote") or "").splitlines()
        if name not in candidates
    )
    for name in candidates:
        raw = git_output(path, "remote", "get-url", name)
        sanitized = sanitize_remote_url(raw or "")
        if sanitized:
            return GitRemote(name, sanitized, normalize_remote_url(sanitized))
    return None


def changed_paths(path: Path, revision: str) -> list[PurePosixPath]:
    root = repository_root(path)
    if root is None:
        raise WheroToolError(f"path is not under Git version control: {path}")
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", "--find-renames", revision, "--"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise WheroToolError(
            f"cannot inspect Git diff {revision}: {result.stderr.strip() or 'git diff failed'}"
        )
    return [PurePosixPath(line) for line in result.stdout.splitlines() if line.strip()]

