"""Shared Git root, source location, and revision operations."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from whero.doctidex.errors import CommandFailure


@dataclass(frozen=True, slots=True)
class GitRootUnresolved(RuntimeError):
    """The requested path cannot be used as the command's Git root."""

    requested_repos_path: str | None
    discovery_start_path: Path


@dataclass(frozen=True, slots=True)
class GitCommitUnavailable(RuntimeError):
    """The selected bare repository cannot provide one required commit."""

    git_url: str
    commit_hash: str


def resolve_git_root(repos_path: str | None, *, cwd: Path | None = None) -> Path:
    """Resolve the explicit root or discover the enclosing Git worktree root."""

    start_path = (Path(repos_path) if repos_path is not None else cwd or Path.cwd()).expanduser()
    try:
        start_path = start_path.resolve(strict=True)
    except OSError as exc:
        raise GitRootUnresolved(repos_path, start_path) from exc

    try:
        completed = subprocess.run(
            ["git", "-C", str(start_path), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GitRootUnresolved(repos_path, start_path) from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise GitRootUnresolved(repos_path, start_path)

    root = Path(completed.stdout.strip()).resolve()
    if repos_path is not None and start_path != root:
        raise GitRootUnresolved(repos_path, start_path)
    return root


def current_branch_name(repository: Path) -> str | None:
    """Return the current branch short name, or ``None`` for a detached HEAD."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "symbolic-ref", "--quiet", "--short", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GitRootUnresolved(str(repository), repository) from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return completed.stdout.strip()


def branch_name_from_ref(reference: str) -> str | None:
    """Return the branch short name for one Git branch ref, or ``None``."""

    prefix = "refs/heads/"
    if not reference.startswith(prefix) or reference == prefix:
        return None
    return reference[len(prefix) :]


def branch_has_workspace(repository: Path, branch_name: str) -> bool:
    """Return whether one branch tree has a tracked doctidex-git work model."""

    required_artifact = ".doctidex-git/config.toml"
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "ls-tree",
                "-r",
                "--name-only",
                f"refs/heads/{branch_name}",
                "--",
                ".doctidex-git",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GitRootUnresolved(str(repository), repository) from exc
    if completed.returncode != 0:
        return False
    tracked = set(completed.stdout.splitlines())
    return required_artifact in tracked


def repository_location(git_url: str) -> tuple[str, tuple[str, ...]]:
    """Return the Git URL domain and repository path without a trailing ``.git``."""

    parsed = urlsplit(git_url)
    if parsed.hostname is not None:
        domain = parsed.hostname
        repository_path = parsed.path
    elif parsed.scheme == "file":
        domain = "local"
        repository_path = parsed.path
    elif match := re.fullmatch(r"(?:[^@/:]+@)?(?P<domain>[^/:]+):(?P<path>.+)", git_url):
        domain = match.group("domain")
        repository_path = match.group("path")
    else:
        domain = "local"
        repository_path = git_url

    components = tuple(component for component in repository_path.strip("/").split("/") if component)
    if components:
        components = (*components[:-1], components[-1].removesuffix(".git"))
    return domain, components or ("repository",)


def resolve_revision(repository: Path, git_url: str, *, kind: str, value: str) -> str:
    """Synchronize or fetch one selector and return its resolved commit hash."""

    if kind == "branch":
        _git_revision(
            repository,
            git_url,
            kind,
            value,
            "fetch",
            "origin",
            f"+refs/heads/{value}:refs/heads/{value}",
        )
        return _git_revision(
            repository,
            git_url,
            kind,
            value,
            "rev-parse",
            "--verify",
            f"refs/heads/{value}^{{commit}}",
        )
    if kind == "tag":
        _git_revision(
            repository,
            git_url,
            kind,
            value,
            "fetch",
            "origin",
            f"+refs/tags/{value}:refs/tags/{value}",
        )
        return _git_revision(
            repository,
            git_url,
            kind,
            value,
            "rev-parse",
            "--verify",
            f"refs/tags/{value}^{{commit}}",
        )
    _git_revision(repository, git_url, kind, value, "fetch", "origin", value)
    return _git_revision(repository, git_url, kind, value, "rev-parse", "--verify", f"{value}^{{commit}}")


def ensure_commit_available(repository: Path, git_url: str, commit_hash: str) -> None:
    """Ensure a bare repository contains one commit without reselecting a revision."""

    if _contains_commit(repository, git_url, commit_hash):
        return
    try:
        subprocess.run(
            ["git", "-C", str(repository), "fetch", "origin", commit_hash],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitCommitUnavailable(git_url, commit_hash) from exc
    if not _contains_commit(repository, git_url, commit_hash):
        raise GitCommitUnavailable(git_url, commit_hash)


def _contains_commit(repository: Path, git_url: str, commit_hash: str) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "cat-file", "-e", f"{commit_hash}^{{commit}}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise GitCommitUnavailable(git_url, commit_hash) from exc
    return completed.returncode == 0


def _git_revision(
    repository: Path,
    git_url: str,
    selector_kind: str,
    selector_value: str,
    *arguments: str,
) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CommandFailure(
            code="revision.unresolvable",
            summary="The requested Git revision could not be resolved.",
            subject={"kind": "git-source", "git-url": git_url},
            details={
                "operation": arguments[0],
                "selector-kind": selector_kind,
                "selector-value": selector_value,
            },
        ) from exc
