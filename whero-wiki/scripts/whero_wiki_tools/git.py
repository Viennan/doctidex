"""Git identity, remote, and changed-path helpers for Whero tooling."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit

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


def resolve_commit(path: Path, revision: str) -> str | None:
    if not revision.strip():
        return None
    return git_output(
        path,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{revision}^{{commit}}",
    )


def sanitize_remote_url(url: str) -> str | None:
    value = url.strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme and parsed.netloc:
        hostname = parsed.hostname
        if hostname is None:
            return None
        host = f"[{hostname}]" if ":" in hostname else hostname
        try:
            port = parsed.port
        except ValueError:
            return None
        netloc = f"{host}:{port}" if port is not None else host
        return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))

    value = value.split("#", 1)[0].split("?", 1)[0]
    if re.fullmatch(r"[^/\s]+@[^/\s:]+:.+", value):
        value = value.rsplit("@", 1)[1]
    return value or None


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
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            revision,
            "--",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise WheroToolError(
            f"cannot inspect Git diff {revision}: "
            f"{result.stderr.decode(errors='replace').strip() or 'git diff failed'}"
        )
    return [
        PurePosixPath(raw.decode("utf-8", errors="surrogateescape"))
        for raw in result.stdout.split(b"\0")
        if raw
    ]
