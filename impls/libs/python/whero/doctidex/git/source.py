from __future__ import annotations

import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

from whero.doctidex.errors import DoctidexError

from .runner import git
from .storage import source_cache

_HEX_OBJECT = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")


@dataclass(frozen=True, slots=True)
class RevisionSelector:
    kind: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    input_url: str
    public_url: str
    canonical: str
    selector: RevisionSelector
    default_branch: str | None
    commit: str
    network: bool


def sanitize_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme and parsed.hostname:
        host = parsed.hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        if parsed.port:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
    return value


def canonical_source(value: str, *, cwd: Path | None = None) -> str:
    parsed = urlsplit(value)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            return sanitize_url(value).rstrip("/")
        return str(Path(unquote(parsed.path)).resolve(strict=False))
    if parsed.scheme:
        sanitized = urlsplit(sanitize_url(value))
        return urlunsplit(
            (sanitized.scheme.lower(), sanitized.netloc.lower(), sanitized.path.rstrip("/"), sanitized.query, "")
        )
    if _is_scp_like(value):
        return value.rstrip("/")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() and cwd is not None:
        candidate = cwd / candidate
    return str(candidate.resolve(strict=False))


def validate_source_locator(value: str, *, cwd: Path | None = None) -> None:
    parsed = urlsplit(value)
    if parsed.scheme or _is_scp_like(value):
        return
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() and cwd is not None:
        candidate = cwd / candidate
    result = git(["-C", str(candidate), "rev-parse", "--git-dir"], operation="external_install", check=False)
    if result.returncode != 0:
        raise DoctidexError(
            "The source URL is not a Git repository locator.",
            operation="external_install",
            affected=[sanitize_url(value)],
            actions=["Pass an accessible Git URL or local Git repository path."],
            code="source_invalid",
            domain="external",
        )


def resolve_source(
    value: str,
    selector: RevisionSelector | None,
    *,
    cwd: Path,
) -> ResolvedSource:
    validate_source_locator(value, cwd=cwd)
    canonical = canonical_source(value, cwd=cwd)
    local = _local_repository(canonical)
    public = canonical if local is not None else sanitize_url(value)
    network = local is None
    if selector is None:
        branch, commit = _default_revision(canonical, local)
        return ResolvedSource(value, public, canonical, RevisionSelector("commit", commit), branch, commit, network)
    _validate_selector(selector)
    commit = _resolve_revision(canonical, local, selector)
    normalized = RevisionSelector(selector.kind, commit if selector.kind == "commit" else selector.value)
    resolution_used_network = local is None
    return ResolvedSource(value, public, canonical, normalized, None, commit, resolution_used_network)


def ensure_source_cache(source: ResolvedSource) -> tuple[Path, bool]:
    target = source_cache(source.canonical)
    if not target.is_dir():
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            git(["clone", "--bare", "--no-local", source.input_url, str(target)], operation="external_install")
        except Exception:
            shutil.rmtree(target, ignore_errors=True)
            raise
    else:
        git(
            [
                "--git-dir",
                str(target),
                "fetch",
                "--force",
                "--tags",
                source.input_url,
                "+refs/heads/*:refs/heads/*",
            ],
            operation="external_install",
        )
    commit = _resolve_in_gitdir(target, source.selector, source.commit)
    if commit != source.commit:
        raise DoctidexError(
            "The source revision changed between planning and apply.",
            operation="external_install",
            affected=[source.public_url],
            actions=["Run the dry-run again and review the new resolved commit."],
            code="index_update_conflict",
            domain="external",
        )
    return target, _local_repository(source.canonical) is None


def ensure_exact_commit_cache(public_url: str, canonical: str, commit: str) -> tuple[Path, bool]:
    target = source_cache(canonical)
    network = False
    if not target.is_dir():
        target.parent.mkdir(parents=True, exist_ok=True)
        git(["clone", "--bare", "--no-local", public_url, str(target)], operation="external_restore")
        network = _local_repository(canonical) is None
    exists = git(
        ["--git-dir", str(target), "cat-file", "-e", f"{commit}^{{commit}}"],
        operation="external_restore",
        check=False,
    )
    if exists.returncode != 0:
        git(["--git-dir", str(target), "fetch", public_url, commit], operation="external_restore")
        network = network or _local_repository(canonical) is None
    _require_commit(target, commit, operation="external_restore")
    return target, network


def verify_exact_commit(public_url: str, canonical: str, commit: str, *, operation: str) -> bool:
    cached = source_cache(canonical)
    if cached.is_dir():
        exists = git(
            ["--git-dir", str(cached), "cat-file", "-e", f"{commit}^{{commit}}"],
            operation=operation,
            check=False,
        )
        if exists.returncode == 0:
            return False
    local = _local_repository(canonical)
    if local is not None:
        gitdir = _common_gitdir(local)
        assert gitdir is not None
        _require_commit(gitdir, commit, operation=operation)
        return False
    with tempfile.TemporaryDirectory(prefix="doctidex-git-restore-") as temporary:
        gitdir = Path(temporary) / "source.git"
        git(["init", "--bare", str(gitdir)], operation=operation)
        fetched = git(
            ["--git-dir", str(gitdir), "fetch", "--depth=1", public_url, commit],
            operation=operation,
            check=False,
        )
        if fetched.returncode != 0:
            raise _revision_error(operation)
        _require_commit(gitdir, commit, operation=operation)
    return True


def add_detached_worktree(gitdir: Path, path: Path, commit: str, *, operation: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    git(
        ["--git-dir", str(gitdir), "worktree", "prune", "--expire", "now"],
        operation=operation,
    )
    git(
        ["--git-dir", str(gitdir), "worktree", "add", "--detach", str(path), commit],
        operation=operation,
    )


def make_logically_read_only(path: Path) -> None:
    for item in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if item.is_symlink():
            continue
        try:
            mode = item.stat().st_mode
            item.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        except OSError:
            continue
    try:
        mode = path.stat().st_mode
        path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    except OSError:
        pass


def remove_detached_worktree(path: Path, *, operation: str) -> None:
    """Remove an owned linked worktree while preserving its Git registration semantics."""

    if not path.exists():
        return
    make_logically_writable(path)
    common = git(
        ["-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation=operation,
        check=False,
    )
    if common.returncode != 0:
        raise DoctidexError(
            "The managed install path is not a removable Git worktree.",
            operation=operation,
            affected=[str(path)],
            actions=["Preserve the path and repair the managed install before retrying remove."],
            code="install_damaged",
            domain="external",
            path=str(path),
        )
    git(
        ["--git-dir", common.stdout.strip(), "worktree", "remove", "--force", str(path)],
        operation=operation,
    )


def move_detached_worktree(path: Path, destination: Path, *, operation: str) -> None:
    """Move an owned linked worktree without losing its Git registration."""

    make_logically_writable(path)
    common = git(
        ["-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation=operation,
        check=False,
    )
    if common.returncode != 0:
        raise DoctidexError(
            "The managed install path is not a movable Git worktree.",
            operation=operation,
            affected=[str(path)],
            actions=["Preserve the path and repair the managed install before retrying."],
            code="install_damaged",
            domain="external",
            path=str(path),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    git(
        ["--git-dir", common.stdout.strip(), "worktree", "move", str(path), str(destination)],
        operation=operation,
    )
    make_logically_read_only(destination)


def make_logically_writable(path: Path) -> None:
    for item in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if item.is_symlink():
            continue
        try:
            item.chmod(item.stat().st_mode | stat.S_IWUSR)
        except OSError:
            continue
    try:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    except OSError:
        pass


def source_relation(root: Path, canonical: str) -> str:
    source_path = _local_repository(canonical)
    if source_path is not None:
        root_common = _common_gitdir(root)
        source_common = _common_gitdir(source_path)
        if root_common is not None and source_common == root_common:
            return "host_repository"
    remotes = git(["-C", str(root), "remote", "get-url", "--all", "origin"], operation="source_relation", check=False)
    if remotes.returncode == 0:
        if canonical in {canonical_source(line, cwd=root) for line in remotes.stdout.splitlines() if line}:
            return "host_repository"
        return "other"
    return "unknown"


def resolve_local_revision(gitdir: Path, selector: RevisionSelector, *, operation: str) -> str:
    _validate_selector(selector)
    if selector.kind == "commit":
        expression = f"{selector.value}^{{commit}}"
    elif selector.kind == "tag":
        expression = f"refs/tags/{selector.value}^{{commit}}"
    else:
        expression = f"refs/heads/{selector.value}^{{commit}}"
    result = git(["--git-dir", str(gitdir), "rev-parse", "--verify", expression], operation=operation, check=False)
    if result.returncode != 0:
        raise _revision_error(operation)
    commit = result.stdout.strip().lower()
    _require_full_object(gitdir, commit, operation=operation)
    return commit


def _default_revision(canonical: str, local: Path | None) -> tuple[str, str]:
    if local is not None:
        branch_result = git(
            ["-C", str(local), "symbolic-ref", "--quiet", "--short", "HEAD"],
            operation="external_install",
            check=False,
        )
        if branch_result.returncode != 0:
            raise DoctidexError(
                "The source does not expose a default branch.",
                operation="external_install",
                affected=[str(local)],
                actions=["Pass --commit, --tag, or --branch explicitly."],
                requires_user="revision",
                code="default_branch_unavailable",
                domain="external",
            )
        branch = branch_result.stdout.strip()
        commit = git(
            ["-C", str(local), "rev-parse", "--verify", "HEAD^{commit}"], operation="external_install"
        ).stdout.strip()
        return branch, commit.lower()
    result = git(["ls-remote", "--symref", canonical, "HEAD"], operation="external_install")
    branch: str | None = None
    commit: str | None = None
    for line in result.stdout.splitlines():
        if line.startswith("ref: refs/heads/") and line.endswith("\tHEAD"):
            branch = line[len("ref: refs/heads/") : -len("\tHEAD")]
        elif line.endswith("\tHEAD"):
            commit = line.split("\t", 1)[0]
    if not branch or not commit:
        raise DoctidexError(
            "The remote does not expose a resolvable default branch.",
            operation="external_install",
            affected=[sanitize_url(canonical)],
            actions=["Pass --commit, --tag, or --branch explicitly."],
            requires_user="revision",
            code="default_branch_unavailable",
            domain="external",
            network=True,
        )
    return branch, commit.lower()


def _resolve_revision(canonical: str, local: Path | None, selector: RevisionSelector) -> str:
    if local is not None:
        gitdir = _common_gitdir(local)
        assert gitdir is not None
        return resolve_local_revision(gitdir, selector, operation="external_install")
    if selector.kind == "commit":
        commit = selector.value.lower()
        with tempfile.TemporaryDirectory(prefix="doctidex-git-revision-") as temporary:
            gitdir = Path(temporary) / "source.git"
            git(["init", "--bare", str(gitdir)], operation="external_install")
            fetched = git(
                ["--git-dir", str(gitdir), "fetch", "--depth=1", canonical, commit],
                operation="external_install",
                check=False,
            )
            if fetched.returncode != 0:
                raise _revision_error("external_install")
            _require_commit(gitdir, commit, operation="external_install")
        return commit
    ref = f"refs/{'tags' if selector.kind == 'tag' else 'heads'}/{selector.value}"
    result = git(["ls-remote", canonical, ref, f"{ref}^{{}}"], operation="external_install")
    values = {}
    for line in result.stdout.splitlines():
        fields = line.split("\t", 1)
        if len(fields) == 2:
            values[fields[1]] = fields[0].lower()
    commit = values.get(f"{ref}^{{}}") or values.get(ref)
    if not commit:
        raise _revision_error("external_install")
    return commit


def _resolve_in_gitdir(gitdir: Path, selector: RevisionSelector, planned_commit: str) -> str:
    if selector.kind == "commit":
        _require_commit(gitdir, planned_commit, operation="external_install")
        return planned_commit
    return resolve_local_revision(gitdir, selector, operation="external_install")


def _require_commit(gitdir: Path, commit: str, *, operation: str) -> None:
    result = git(["--git-dir", str(gitdir), "cat-file", "-e", f"{commit}^{{commit}}"], operation=operation, check=False)
    if result.returncode != 0:
        raise _revision_error(operation)


def _require_full_object(gitdir: Path, commit: str, *, operation: str) -> None:
    object_format = git(
        ["--git-dir", str(gitdir), "rev-parse", "--show-object-format"], operation=operation
    ).stdout.strip()
    expected = 64 if object_format == "sha256" else 40
    if len(commit) != expected:
        raise DoctidexError(
            "A commit selector must resolve to a full object ID.",
            operation=operation,
            affected=[commit],
            actions=["Pass the full commit object ID."],
            requires_user="revision",
            code="revision_invalid",
            domain="external",
        )


def _validate_selector(selector: RevisionSelector) -> None:
    if selector.kind not in {"commit", "tag", "branch"} or not selector.value:
        raise _revision_error("external_install")
    if selector.kind == "commit":
        if not _HEX_OBJECT.fullmatch(selector.value):
            raise DoctidexError(
                "A commit selector must be a full SHA-1 or SHA-256 object ID.",
                operation="external_install",
                affected=[selector.value],
                actions=["Pass the full commit object ID."],
                requires_user="revision",
                code="revision_invalid",
                domain="external",
            )
        return
    invalid = any(token in selector.value for token in ("..", "@{", "~", "^", ":", " "))
    check = git(
        ["check-ref-format", f"refs/{'tags' if selector.kind == 'tag' else 'heads'}/{selector.value}"],
        operation="revision",
        check=False,
    )
    if invalid or check.returncode != 0:
        raise DoctidexError(
            "The tag or branch selector is not a single valid Git ref name.",
            operation="external_install",
            affected=[selector.value],
            actions=["Pass a branch or tag name, not a revspec."],
            requires_user="revision",
            code="revision_invalid",
            domain="external",
        )


def _revision_error(operation: str) -> DoctidexError:
    return DoctidexError(
        "The Git revision does not resolve to a commit.",
        operation=operation,
        actions=["Pass an existing full commit, tag, or branch."],
        requires_user="revision",
        code="revision_not_found",
        domain="external",
    )


def _local_repository(canonical: str) -> Path | None:
    if _is_scp_like(canonical) or urlsplit(canonical).scheme:
        return None
    path = Path(canonical)
    result = git(["-C", str(path), "rev-parse", "--git-dir"], operation="source", check=False)
    return path if result.returncode == 0 else None


def _common_gitdir(path: Path) -> Path | None:
    result = git(
        ["-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation="source",
        check=False,
    )
    return Path(result.stdout.strip()).resolve(strict=False) if result.returncode == 0 else None


def _is_scp_like(value: str) -> bool:
    colon = value.find(":")
    if colon <= 0:
        return False
    prefix = value[:colon]
    return "/" not in prefix and "\\" not in prefix
