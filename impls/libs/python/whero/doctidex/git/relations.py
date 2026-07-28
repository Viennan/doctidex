from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from .runner import git


def git_head(path: Path, *, operation: str) -> str | None:
    result = git(["-C", str(path), "rev-parse", "HEAD"], operation=operation, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def git_branch(path: Path, *, operation: str) -> str | None:
    result = git(
        ["-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"],
        operation=operation,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def repository_relation(
    root: Path,
    source: str,
    effective_commit: str | None,
    *,
    root_head: str | None = None,
) -> dict[str, str]:
    if not _same_repository(root, source):
        return {"source": "unknown", "revision": "unknown"}
    head = root_head if root_head is not None else git_head(root, operation="repository_relation")
    if not head or not effective_commit:
        revision = "unknown"
    elif head == effective_commit:
        revision = "same_commit"
    else:
        revision = "different_commit"
    return {"source": "same_repository", "revision": revision}


def maintenance_reuse(
    root: Path,
    source: str,
    effective_commit: str | None,
    relation: dict[str, str],
    records: list[dict[str, Any]],
    *,
    target_branch: str | None,
    root_branch: str | None,
) -> dict[str, Any]:
    same_revision_records = [
        item
        for item in records
        if item.get("url") == source
        and effective_commit is not None
        and item.get("base_commit") == effective_commit
        and isinstance(item.get("path"), str)
        and Path(item["path"]).is_dir()
    ]
    compatible_records = [
        item
        for item in same_revision_records
        if _delivery_targets_compatible(target_branch, _branch_hint(item.get("target_branch")))
    ]
    compatible_records.sort(key=lambda item: item["path"])
    host_same_commit = relation == {"source": "same_repository", "revision": "same_commit"}
    host_compatible = host_same_commit and _delivery_targets_compatible(target_branch, root_branch)
    if host_compatible:
        return {
            "status": "recommended",
            "scope_kind": "host_root",
            "write_path": str(root),
            "target_branch": root_branch,
            "candidate_count": 1 + len(compatible_records),
            "reason": "current_root_same_commit",
        }
    if len(compatible_records) == 1:
        record = compatible_records[0]
        return {
            "status": "recommended",
            "scope_kind": "maintenance_root",
            "write_path": record["path"],
            "target_branch": _branch_hint(record.get("target_branch")),
            "candidate_count": 1,
            "reason": "existing_scope_same_commit",
        }
    if len(compatible_records) > 1:
        return {
            "status": "selection_required",
            "scope_kind": "maintenance_root",
            "write_path": None,
            "target_branch": None,
            "candidate_count": len(compatible_records),
            "reason": "multiple_existing_scopes",
    }
    if effective_commit is None:
        reason = "source_not_prepared"
    elif (host_same_commit and not host_compatible) or same_revision_records:
        reason = "delivery_target_conflict"
    elif relation == {"source": "same_repository", "revision": "different_commit"}:
        reason = "current_root_different_commit"
    else:
        reason = "no_compatible_scope"
    return {
        "status": "not_available",
        "scope_kind": None,
        "write_path": None,
        "target_branch": None,
        "candidate_count": 0,
        "reason": reason,
    }


def current_root_reuse(root: Path, target_branch: str | None) -> dict[str, Any]:
    return {
        "status": "recommended",
        "scope_kind": "host_root",
        "write_path": str(root),
        "target_branch": target_branch,
        "candidate_count": 1,
        "reason": "current_root",
    }


def _same_repository(root: Path, source: str) -> bool:
    worktree = _git_worktree_root(root)
    if worktree is None or worktree != root.resolve(strict=False):
        return False
    root_common = _git_common_directory(root)
    source_path = _local_source_path(source, root)
    if root_common is not None and source_path is not None:
        source_common = _git_common_directory(source_path)
        if source_common is not None and source_common == root_common:
            return True

    remotes = _remote_urls(root)
    if source in remotes:
        return True
    if source_path is None:
        return False
    for remote in remotes:
        remote_path = _local_source_path(remote, root)
        if remote_path is not None and remote_path == source_path:
            return True
    return False


def _git_worktree_root(path: Path) -> Path | None:
    result = git(
        ["-C", str(path), "rev-parse", "--show-toplevel"],
        operation="repository_relation",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve(strict=False)


def _git_common_directory(path: Path) -> Path | None:
    result = git(
        ["-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation="repository_relation",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve(strict=False)


def _remote_urls(root: Path) -> set[str]:
    result = git(
        ["-C", str(root), "config", "--get-regexp", r"^remote\..*\.url$"],
        operation="repository_relation",
        check=False,
    )
    if result.returncode != 0:
        return set()
    values: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and fields[1]:
            values.add(fields[1])
    return values


def _local_source_path(value: str, root: Path) -> Path | None:
    parsed = urlsplit(value)
    if parsed.scheme == "file":
        if parsed.netloc not in {"", "localhost"}:
            return None
        candidate = Path(unquote(parsed.path))
    elif parsed.scheme:
        return None
    else:
        if _is_scp_like_remote(value):
            return None
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
    if not candidate.exists():
        return None
    return candidate.resolve(strict=False)


def _delivery_targets_compatible(first: object, second: object) -> bool:
    return not (isinstance(first, str) and isinstance(second, str) and first != second)


def _branch_hint(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _is_scp_like_remote(value: str) -> bool:
    colon = value.find(":")
    if colon <= 0:
        return False
    prefix = value[:colon]
    return "/" not in prefix and "\\" not in prefix
