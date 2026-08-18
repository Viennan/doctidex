"""Managed Git worktree command workflows."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import Worktree
from whero.doctidex.paths import normalize_repo_path, repo_path_to_fs
from whero.doctidex.repository import (
    GitCommitUnavailable,
    ensure_commit_available,
    repository_location,
    resolve_revision,
)
from whero.doctidex.store.coordination import WorkflowCoordinator
from whero.doctidex.store.files import StoreFailure, atomic_write_bytes
from whero.doctidex.store.model_view import RuntimeWriteModelView
from whero.doctidex.store.runtime import RuntimeStore

_DEFAULT_WORKTREE_DIRECTORY = "/.doctidex-git/worktrees"
_IGNORE_MARKER_PREFIX = "# doctidex-git worktree: "
_RANDOM_TREE_NAME_LENGTH = 7


def create(
    store: RuntimeStore,
    coordinator: WorkflowCoordinator,
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
        installation = coordinator.run(lambda: _read_installation(store, install_id))
        if installation is None:
            raise _source_failure(_failure_work_path(explicit_work_path), install_id=install_id)
        source_url = installation.git_url
        base_commit_hash = installation.commit_hash
        selector_kind, selector_value = "install-id", install_id

        def create_from_repository(repository: Path) -> Worktree:
            return _create_from_repository(
                store,
                repository,
                install_id=install_id,
                source_url=source_url,
                base_commit_hash=base_commit_hash,
                explicit_work_path=explicit_work_path,
                tree_name=tree_name,
                selector_kind=selector_kind,
                selector_value=selector_value,
            )

    else:
        assert git_url is not None
        source_url = git_url
        selector_kind, selector_value = _revision_selector(branch=branch, tag=tag, commit=commit)
        resolved_commit: str | None = None

        def create_from_repository(repository: Path) -> Worktree:
            nonlocal resolved_commit
            if resolved_commit is None:
                resolved_commit = _resolve_revision(repository, source_url, selector_kind, selector_value)
            return _create_from_repository(
                store,
                repository,
                install_id=None,
                source_url=source_url,
                base_commit_hash=resolved_commit,
                explicit_work_path=explicit_work_path,
                tree_name=tree_name,
                selector_kind=selector_kind,
                selector_value=selector_value,
            )

    try:
        return coordinator.with_repository(source_url, create_from_repository)
    except CommandFailure as exc:
        if exc.code == "cache.repository.unavailable":
            raise _source_failure(
                _failure_work_path(explicit_work_path), install_id=install_id, git_url=source_url
            ) from exc
        raise


def remove(
    store: RuntimeStore,
    *,
    work_path: str,
    force: bool,
) -> None:
    """Remove a recorded worktree and its custom Git ignore protection."""

    selected_path = normalize_repo_path(work_path, parameter="--work-path")
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        if view.worktree(selected_path) is None:
            return

        target = repo_path_to_fs(store.git_root, selected_path)
        if target.exists() or target.is_symlink():
            if not force:
                reason = _remove_block_reason(target)
                if reason is not None:
                    raise _remove_blocked_failure(selected_path, reason)
            _remove_worktree_path(target, selected_path)
        if not _is_default_work_path(selected_path):
            _remove_custom_ignore(store.git_root, selected_path)
        view.remove_worktrees((selected_path,))


def _read_installation(store: RuntimeStore, install_id: str):
    with store.read_only_transaction() as transaction:
        return transaction.model_view().installation(install_id)


def query(store: RuntimeStore, *, work_path: str) -> Worktree:
    """Return the recorded Worktree for one repository-internal path."""

    selected_path = normalize_repo_path(work_path, parameter="--work-path")
    with store.read_only_transaction() as transaction:
        record = transaction.model_view().worktree(selected_path)
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
    selector_kind: str,
    selector_value: str,
) -> Worktree:
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        work_path = _select_work_path(view, store.git_root, source_url, explicit_work_path, tree_name)
        target = repo_path_to_fs(store.git_root, work_path)
        _ensure_available_target(view, target, work_path)
        _ensure_worktree_commit(
            repository,
            source_url,
            base_commit_hash,
            work_path=work_path,
            selector_kind=selector_kind,
            selector_value=selector_value,
        )

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
        raise _revision_failure(git_url, selector_kind, selector_value) from exc


def _ensure_worktree_commit(
    repository: Path,
    git_url: str,
    commit_hash: str,
    *,
    work_path: str,
    selector_kind: str,
    selector_value: str,
) -> None:
    try:
        ensure_commit_available(repository, git_url, commit_hash)
    except GitCommitUnavailable as exc:
        if selector_kind == "install-id":
            raise _source_failure(work_path, install_id=selector_value) from exc
        raise _revision_failure(git_url, selector_kind, selector_value) from exc


def _revision_failure(git_url: str, selector_kind: str, selector_value: str) -> CommandFailure:
    return CommandFailure(
        code="revision.unresolvable",
        summary="The requested Git revision could not be resolved.",
        subject={"kind": "git-source", "git-url": git_url},
        details={
            "operation": "worktree create",
            "selector-kind": selector_kind,
            "selector-value": selector_value,
        },
    )


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


def _remove_worktree_path(target: Path, work_path: str) -> None:
    """Remove only the managed worktree directory, leaving stale Git registration to create-prune."""

    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.exists():
            shutil.rmtree(target)
    except OSError as exc:
        raise _remove_unavailable_failure(work_path) from exc


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


def _align_custom_ignores(git_root: Path, work_paths: tuple[str, ...]) -> None:
    """Keep only tool-marked ignore pairs required by the current Worktree records."""

    desired = set(work_paths)
    gitignore = git_root / ".gitignore"
    try:
        content = gitignore.read_text() if gitignore.exists() else ""
        lines = content.splitlines()
        updated: list[str] = []
        retained: set[str] = set()
        index = 0
        while index < len(lines):
            marker = lines[index]
            if marker.startswith(_IGNORE_MARKER_PREFIX) and index + 1 < len(lines):
                candidate = marker.removeprefix(_IGNORE_MARKER_PREFIX)
                expected_marker, expected_rule = _ignore_entry(candidate)
                if marker == expected_marker and lines[index + 1] == expected_rule:
                    if candidate in desired:
                        updated.extend((marker, lines[index + 1]))
                        retained.add(candidate)
                    index += 2
                    continue
            updated.append(marker)
            index += 1
        for work_path in sorted(desired - retained):
            updated.extend(_ignore_entry(work_path))
        if updated != lines:
            atomic_write_bytes(
                gitignore,
                ("\n".join(updated) + ("\n" if updated else "")).encode(),
                store="runtime",
                phase="worktree-ignore",
            )
    except (OSError, StoreFailure) as exc:
        raise _ignore_failure("/.gitignore", operation="repair", gitignore=gitignore) from exc


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


def _remove_unavailable_failure(work_path: str) -> CommandFailure:
    return CommandFailure(
        code="worktree.remove.unavailable",
        summary="The managed worktree directory could not be removed.",
        subject={"kind": "worktree", "work-path": work_path},
        details={"operation": "remove", "reason": "worktree-path-unavailable"},
    )
