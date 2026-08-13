"""Managed Git worktree command workflows."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from whero.doctidex.errors import CommandFailure
from whero.doctidex.git_cache import GitCache
from whero.doctidex.model import Worktree
from whero.doctidex.model_view import RuntimeModelView, RuntimeWriteModelView
from whero.doctidex.paths import normalize_repo_path, repo_path_to_fs
from whero.doctidex.repository import repository_location, resolve_revision
from whero.doctidex.store.files import StoreFailure, atomic_write_bytes
from whero.doctidex.store.runtime import RuntimeStore

_DEFAULT_WORKTREE_DIRECTORY = "/.doctidex-git/worktrees"
_IGNORE_MARKER_PREFIX = "# doctidex-git worktree: "
_RANDOM_TREE_NAME_LENGTH = 7


def create(
    store: RuntimeStore,
    cache: GitCache,
    *,
    install_id: str | None,
    git_url: str | None,
    work_path: str | None,
    branch: str = "",
    tag: str = "",
    commit: str = "",
    tree_name: str | None = None,
) -> Worktree:
    """Create and record a managed worktree from one Installation or Git URL."""

    explicit_work_path = _explicit_work_path(work_path)

    if install_id is not None:
        with store.read_only_transaction() as transaction:
            installation = RuntimeModelView(transaction).installation(install_id)
        if installation is None:
            raise _source_failure(_failure_work_path(explicit_work_path), install_id=install_id)
        source_url = installation.git_url
        base_commit_hash = installation.commit_hash

        def create_from_repository(repository: Path) -> Worktree:
            return _create_from_repository(
                store,
                repository,
                install_id=install_id,
                source_url=source_url,
                base_commit_hash=base_commit_hash,
                explicit_work_path=explicit_work_path,
                tree_name=tree_name,
            )

    else:
        assert git_url is not None
        source_url = git_url
        selector_kind, selector_value = _revision_selector(branch=branch, tag=tag, commit=commit)

        def create_from_repository(repository: Path) -> Worktree:
            base_commit_hash = _resolve_revision(repository, source_url, selector_kind, selector_value)
            return _create_from_repository(
                store,
                repository,
                install_id=None,
                source_url=source_url,
                base_commit_hash=base_commit_hash,
                explicit_work_path=explicit_work_path,
                tree_name=tree_name,
            )

    try:
        return cache.with_repository(source_url, create_from_repository)
    except CommandFailure as exc:
        if exc.code == "cache.repository.unavailable":
            raise _source_failure(
                _failure_work_path(explicit_work_path), install_id=install_id, git_url=source_url
            ) from exc
        raise


def remove(store: RuntimeStore, cache: GitCache, *, work_path: str, force: bool) -> None:
    """Remove a recorded worktree and its custom Git ignore protection."""

    selected_path = normalize_repo_path(work_path, parameter="--work-path")
    with store.read_only_transaction() as transaction:
        record = RuntimeModelView(transaction).worktree(selected_path)
    if record is None:
        return

    target = repo_path_to_fs(store.git_root, selected_path)
    if not target.exists() and not target.is_symlink():
        _remove_missing_worktree_record(store, selected_path)
        return

    cache.with_repository(
        record.url,
        lambda repository: _remove_from_repository(store, repository, work_path=selected_path, force=force),
    )


def query(store: RuntimeStore, *, work_path: str) -> Worktree:
    """Return the recorded Worktree for one repository-internal path."""

    selected_path = normalize_repo_path(work_path, parameter="--work-path")
    with store.read_only_transaction() as transaction:
        record = RuntimeModelView(transaction).worktree(selected_path)
    if record is None:
        raise _not_found_failure(selected_path, operation="query")
    return record


def _create_from_repository(
    store: RuntimeStore,
    repository: Path,
    *,
    install_id: str | None,
    source_url: str,
    base_commit_hash: str,
    explicit_work_path: str | None,
    tree_name: str | None,
) -> Worktree:
    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        work_path = _select_work_path(view, store.git_root, source_url, explicit_work_path, tree_name)
        target = repo_path_to_fs(store.git_root, work_path)
        _ensure_available_target(view, target, work_path)

        ignored = False
        if not _is_default_work_path(work_path):
            ignored = _add_custom_ignore(store.git_root, work_path)
        try:
            _create_git_worktree(repository, target, base_commit_hash, work_path, source_url, install_id)
        except CommandFailure:
            if ignored:
                _remove_custom_ignore(store.git_root, work_path)
            raise

        record = Worktree(
            url=source_url,
            install_id=install_id,
            base_commit_hash=base_commit_hash,
            work_path=work_path,
        )
        view.upsert_worktree(record)
        return record


def _remove_missing_worktree_record(store: RuntimeStore, work_path: str) -> None:
    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        record = view.worktree(work_path)
        if record is None:
            return
        _finalize_removal(store, view, work_path)


def _remove_from_repository(store: RuntimeStore, repository: Path, *, work_path: str, force: bool) -> None:
    with store.write_transaction() as transaction:
        view = RuntimeWriteModelView(transaction)
        record = view.worktree(work_path)
        if record is None:
            return
        target = repo_path_to_fs(store.git_root, work_path)
        if not target.exists() and not target.is_symlink():
            _finalize_removal(store, view, work_path)
            return
        if not force:
            reason = _remove_block_reason(target)
            if reason is not None:
                raise _remove_blocked_failure(work_path, reason)
        _remove_git_worktree(repository, target, work_path, force=force)
        _finalize_removal(store, view, work_path)


def _finalize_removal(store: RuntimeStore, view: RuntimeWriteModelView, work_path: str) -> None:
    """Remove the managed ignore rule and Worktree record after physical removal."""

    if not _is_default_work_path(work_path):
        _remove_custom_ignore(store.git_root, work_path)
    view.remove_worktrees((work_path,))


def _explicit_work_path(work_path: str | None) -> str | None:
    return normalize_repo_path(work_path, parameter="--work-path") if work_path is not None else None


def _select_work_path(
    view: RuntimeWriteModelView,
    git_root: Path,
    git_url: str,
    explicit_work_path: str | None,
    tree_name: str | None,
) -> str:
    if explicit_work_path is not None:
        return explicit_work_path
    if tree_name is not None:
        return _default_work_path(git_url, tree_name)
    return _available_default_work_path(view, git_root, git_url)


def _available_default_work_path(view: RuntimeWriteModelView, git_root: Path, git_url: str) -> str:
    while True:
        work_path = _default_work_path(git_url, _random_tree_name())
        target = repo_path_to_fs(git_root, work_path)
        if view.worktree(work_path) is None and not target.exists() and not target.is_symlink():
            return work_path


def _default_work_path(git_url: str, name: str) -> str:
    domain, repository_path = repository_location(git_url)
    path_components = tuple(component for component in name.replace("\\", "/").split("/") if component)
    if not path_components or any(component in {".", ".."} for component in path_components):
        raise _tree_name_failure(name)
    return f"{_DEFAULT_WORKTREE_DIRECTORY}/{domain}/{'/'.join((*repository_path, *path_components))}"


def _random_tree_name() -> str:
    return uuid.uuid4().hex[:_RANDOM_TREE_NAME_LENGTH]


def _failure_work_path(work_path: str | None) -> str:
    if work_path is None:
        return _DEFAULT_WORKTREE_DIRECTORY
    return normalize_repo_path(work_path, parameter="--work-path")


def _revision_selector(*, branch: str, tag: str, commit: str) -> tuple[str, str]:
    selectors = (("branch", branch), ("tag", tag), ("commit", commit))
    selected = [(kind, value) for kind, value in selectors if value]
    if len(selected) != 1:
        raise ValueError("exactly one revision selector is required")
    return selected[0]


def _resolve_revision(repository: Path, git_url: str, selector_kind: str, selector_value: str) -> str:
    try:
        return resolve_revision(repository, git_url, kind=selector_kind, value=selector_value)
    except CommandFailure as exc:
        if exc.code != "revision.unresolvable":
            raise
        raise CommandFailure(
            code=exc.code,
            summary=exc.summary,
            subject=exc.subject,
            details={
                "operation": "worktree create",
                "selector-kind": selector_kind,
                "selector-value": selector_value,
            },
        ) from exc


def _is_default_work_path(work_path: str) -> bool:
    return work_path.startswith(f"{_DEFAULT_WORKTREE_DIRECTORY}/")


def _ensure_available_target(view: RuntimeWriteModelView, target: Path, work_path: str) -> None:
    if view.worktree(work_path) is not None:
        raise _target_failure(work_path, occupant="managed-worktree")
    if target.exists() or target.is_symlink():
        raise _target_failure(work_path, occupant="existing-path")


def _create_git_worktree(
    repository: Path,
    target: Path,
    revision: str,
    work_path: str,
    git_url: str,
    install_id: str | None,
) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise _target_failure(work_path, occupant="unavailable-path") from exc
    try:
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "prune"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "add", "--detach", str(target), revision],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _source_failure(work_path, install_id=install_id, git_url=git_url) from exc


def _remove_block_reason(target: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "git-worktree-unavailable"
    return "uncommitted-changes" if result.stdout else None


def _remove_git_worktree(repository: Path, target: Path, work_path: str, *, force: bool) -> None:
    arguments = ["git", "-C", str(repository), "worktree", "remove"]
    if force:
        arguments.append("--force")
    arguments.append(str(target))
    try:
        subprocess.run(arguments, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _remove_blocked_failure(work_path, "git-worktree-unavailable") from exc


def _add_custom_ignore(git_root: Path, work_path: str) -> bool:
    marker, rule = _ignore_entry(work_path)
    gitignore = git_root / ".gitignore"
    try:
        content = gitignore.read_text() if gitignore.exists() else ""
        lines = content.splitlines()
        if _has_ignore_entry(lines, marker, rule):
            return False
        atomic_write_bytes(
            gitignore,
            "\n".join((*lines, marker, rule)).encode() + b"\n",
            store="runtime",
            phase="worktree-ignore",
        )
    except (OSError, StoreFailure) as exc:
        raise _ignore_failure(work_path, operation="add", gitignore=gitignore) from exc
    return True


def _remove_custom_ignore(git_root: Path, work_path: str) -> None:
    marker, rule = _ignore_entry(work_path)
    gitignore = git_root / ".gitignore"
    try:
        content = gitignore.read_text() if gitignore.exists() else ""
        lines = content.splitlines()
        updated: list[str] = []
        index = 0
        while index < len(lines):
            if lines[index] == marker and index + 1 < len(lines) and lines[index + 1] == rule:
                index += 2
                continue
            updated.append(lines[index])
            index += 1
        if updated != lines:
            atomic_write_bytes(
                gitignore,
                ("\n".join(updated) + ("\n" if updated else "")).encode(),
                store="runtime",
                phase="worktree-ignore",
            )
    except (OSError, StoreFailure) as exc:
        raise _ignore_failure(work_path, operation="remove", gitignore=gitignore) from exc


def _ignore_entry(work_path: str) -> tuple[str, str]:
    return f"{_IGNORE_MARKER_PREFIX}{work_path}", f"{work_path.rstrip('/')}/"


def _has_ignore_entry(lines: list[str], marker: str, rule: str) -> bool:
    return any(lines[index] == marker and lines[index + 1] == rule for index in range(len(lines) - 1))


def _source_failure(
    work_path: str, *, install_id: str | None = None, git_url: str | None = None
) -> CommandFailure:
    details: dict[str, object] = {"operation": "create"}
    if install_id is not None:
        details["install-id"] = install_id
    if git_url is not None:
        details["git-url"] = git_url
    return CommandFailure(
        code="worktree.source.unavailable",
        summary="The requested source cannot provide a managed worktree.",
        subject={"kind": "worktree", "work-path": work_path},
        details=details,
    )


def _target_failure(work_path: str, *, occupant: str) -> CommandFailure:
    return CommandFailure(
        code="worktree.target.unavailable",
        summary="The requested worktree path cannot be used for creation.",
        subject={"kind": "worktree", "work-path": work_path},
        details={"operation": "create", "occupant": occupant},
    )


def _tree_name_failure(tree_name: str) -> CommandFailure:
    return CommandFailure(
        code="argument.invalid",
        summary="The worktree tree name cannot be used as a relative directory path.",
        details={
            "parameter": "--tree-name",
            "received": tree_name,
            "constraint": "relative-path-without-dot-components",
        },
    )


def _ignore_failure(work_path: str, *, operation: str, gitignore: Path) -> CommandFailure:
    return CommandFailure(
        code="worktree.ignore.protection.failed",
        summary="The worktree path could not be protected by Git ignore rules.",
        subject={"kind": "worktree", "work-path": work_path},
        details={"operation": operation, "gitignore-path": str(gitignore)},
    )


def _not_found_failure(work_path: str, *, operation: str) -> CommandFailure:
    return CommandFailure(
        code="worktree.not-found",
        summary="The requested managed worktree does not exist.",
        subject={"kind": "worktree", "work-path": work_path},
        details={"operation": operation},
    )


def _remove_blocked_failure(work_path: str, reason: str) -> CommandFailure:
    return CommandFailure(
        code="worktree.remove.blocked",
        summary="The managed worktree cannot be removed without force.",
        subject={"kind": "worktree", "work-path": work_path},
        details={"reason": reason, "required-option": "--force"},
    )
