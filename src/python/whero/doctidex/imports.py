"""Import installation and managed-reference command workflows."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    Installation,
    InstallationContextReference,
    InstallationShare,
    Ref,
)
from whero.doctidex.model_view import scan_cross_boundary_links
from whero.doctidex.paths import (
    is_managed_imports_path,
    is_managed_worktrees_path,
    normalize_repo_path,
    repo_path_to_fs,
)
from whero.doctidex.repository import (
    GitCommitUnavailable,
    current_branch_name,
    ensure_commit_available,
    local_branch_names,
    repository_location,
    resolve_revision,
)
from whero.doctidex.store.coordination import WorkflowCoordinator
from whero.doctidex.store.model_view import RuntimeModelView, RuntimeWriteModelView
from whero.doctidex.store.runtime import RuntimeStore


def install(
    store: RuntimeStore,
    coordinator: WorkflowCoordinator,
    *,
    tracked: bool,
    git_url: str,
    branch: str,
    tag: str,
    commit: str,
    keys: list[str],
) -> Installation:
    """Install one Git revision as a tracked or untracked Installation."""

    selector_kind, selector_value = _revision_selector(branch=branch, tag=tag, commit=commit)
    resolved_commit: str | None = None

    def install_from_repository(repository: Path) -> Installation:
        nonlocal resolved_commit
        if resolved_commit is None:
            resolved_commit = _resolve_revision(repository, git_url, kind=selector_kind, value=selector_value)
        commit_hash = resolved_commit
        ensure_install_commit(repository, git_url, selector_kind, selector_value, commit_hash)
        return _install_resolved(
            store,
            repository,
            tracked=tracked,
            git_url=git_url,
            branch=branch,
            tag=tag,
            keys=keys,
            selector_kind=selector_kind,
            commit_hash=commit_hash,
            selector_value=selector_value,
        )

    return coordinator.with_repository(git_url, install_from_repository)


def restore_context_import(
    owner_store: RuntimeStore,
    installation_store: RuntimeStore,
    coordinator: WorkflowCoordinator,
    *,
    parent_install_path: str,
    sub_install_id: str,
) -> Installation:
    """Restore one Installation-local sub-Installation into the owner work model."""

    with installation_store.unlocked_read_only_transaction() as transaction:
        local = transaction.model_view().installation(sub_install_id)
    if local is None:
        raise CommandFailure(
            code="installation.not-found",
            summary="The requested installation does not exist.",
            subject={"kind": "installation", "install-id": sub_install_id},
            details={"operation": "find"},
        )

    parent_install_id = _parent_install_id(owner_store, parent_install_path)
    owner_share_path: str | None = None

    def restore_from_repository(repository: Path) -> None:
        nonlocal owner_share_path
        with owner_store.write_transaction() as transaction:
            view = transaction.write_model_view()
            share = _ensure_share_for_commit(
                owner_store,
                repository,
                view,
                local.git_url,
                local.commit_hash,
            )
            context_reference = InstallationContextReference(
                install_id=local.install_id,
                owner_install_id=parent_install_id,
            )
            view.upsert_installation_share(_with_context_reference(share, context_reference))
            owner_share_path = share.install_path

    coordinator.with_repository(local.git_url, restore_from_repository)
    if owner_share_path is None:
        raise CommandFailure(
            code="installation.context.unavailable",
            summary="The owner Installation share could not be created.",
            subject={"kind": "installation", "install-id": local.install_id},
            details={"owner-path": str(owner_store.git_root), "reason": "share-unavailable"},
        )
    return replace(
        local,
        presentation_path=str(
            repo_path_to_fs(owner_store.git_root, owner_share_path)
        ),
    )


def restore(
    store: RuntimeStore,
    coordinator: WorkflowCoordinator,
    install_id: str,
) -> Installation:
    """Restore a tracked Installation's physical worktree at its recorded commit."""

    installation = coordinator.run(lambda: _read_installation(store, install_id))
    if not installation.tracked:
        raise _installation_failure(
            "installation.tracking-state.invalid", installation, {"required-tracked": True, "actual-tracked": False}
        )

    def restore_from_repository(repository: Path) -> Installation:
        return _restore_resolved(store, repository, install_id)

    return coordinator.with_repository(installation.git_url, restore_from_repository)


def track(store: RuntimeStore, install_id: str) -> Installation:
    """Promote an untracked Installation to the tracked projection."""

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        installation = _find_installation(view, install_id)
        if installation.tracked:
            return installation
        return view.set_installation_tracking(installation, tracked=True)


def remove(
    store: RuntimeStore,
    install_id: str | None,
    *,
    untracked: bool,
    auto: bool,
    branches: tuple[str, ...] = (),
) -> None:
    """Remove selected Installations after confirming no link or Ref blocks them."""

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        if branches:
            deleted_branches = _explicit_branch_snapshot_names(store, view, branches)
        elif auto:
            deleted_branches = _stale_branch_snapshot_names(store, view)
        else:
            deleted_branches = ()

        if not branches:
            selected = _select_installations(view, install_id, untracked=untracked, auto=auto)
            blocked = _blocked_installations(store.git_root, view, selected)
            if blocked:
                raise CommandFailure(
                    code="installation.remove.blocked",
                    summary="The selected installation is still referenced by the current doctidex tree.",
                    subject={
                        "kind": "installation" if install_id else "installation-selection",
                        **({"install-id": install_id} if install_id else {}),
                    },
                    details={"blocked-installations": blocked},
                )
            for item in selected:
                _remove_installation_reference(store, view, item)

        if deleted_branches:
            _remove_branch_snapshot_history(store, view, deleted_branches)


def ref(store: RuntimeStore, install_id: str, src_sub_dir: str, target_dir: str) -> Ref:
    """Create a managed symbolic reference into one Installation."""

    target_dir = normalize_repo_path(target_dir, parameter="--target-dir")
    if src_sub_dir:
        src_sub_dir = normalize_repo_path(src_sub_dir, parameter="--src-sub-dir")
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        reason, boundary = _ref_target_reservation(view, target_dir)
        if reason is not None:
            details: dict[str, object] = {"install-id": install_id, "operation": "create", "reason": reason}
            if boundary is not None:
                details["boundary-path"] = boundary.path
                details["boundary-type"] = boundary.type
            raise CommandFailure(
                code="ref.target.unavailable",
                summary="The managed reference target cannot be created at the requested path.",
                subject={"kind": "ref", "target-dir": target_dir},
                details=details,
            )
        installation = _find_installation(view, install_id)
        source = repo_path_to_fs(store.git_root, installation.install_path)
        if src_sub_dir:
            source = source / src_sub_dir.lstrip("/")
        if not source.exists():
            raise _installation_failure(
                "ref.source.unavailable",
                installation,
                {"install-path": installation.install_path, "src-sub-dir": src_sub_dir},
            )
        target = repo_path_to_fs(store.git_root, target_dir)
        if target.exists() or target.is_symlink():
            raise CommandFailure(
                code="ref.target.unavailable",
                summary="The managed reference target is already occupied.",
                subject={"kind": "ref", "target-dir": target_dir},
                details={"install-id": install_id, "operation": "create"},
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(os.path.relpath(source, start=target.parent), target, target_is_directory=source.is_dir())
        except OSError as exc:
            raise CommandFailure(
                code="ref.target.unavailable",
                summary="The managed reference could not be created.",
                subject={"kind": "ref", "target-dir": target_dir},
                details={"install-id": install_id, "operation": "create"},
            ) from exc
        record = Ref(install_id=install_id, src_sub_dir=src_sub_dir, target_dir=target_dir)
        view.set_installation_tracking(installation, tracked=True)
        view.upsert_ref(record)
        return record


def unref(store: RuntimeStore, target_dir: str) -> None:
    """Remove a managed reference after confirming no Markdown link uses it."""

    target_dir = normalize_repo_path(target_dir, parameter="--target-dir")
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        record = view.ref(target_dir)
        if record is None:
            return
        blocking_links = [
            link.reference_details()
            for link in scan_cross_boundary_links(store.git_root, view)
            if link.ref == record
        ]
        if blocking_links:
            raise CommandFailure(
                code="ref.remove.blocked",
                summary="The managed reference is still linked from the current doctidex tree.",
                subject={"kind": "ref", "target-dir": target_dir},
                details={"blocking-links": blocking_links},
            )
        installation = _find_installation(view, record.install_id)
        source = repo_path_to_fs(store.git_root, installation.install_path) / record.src_sub_dir.lstrip("/")
        target = repo_path_to_fs(store.git_root, target_dir)
        if not target.is_symlink() or target.resolve(strict=False) != source.resolve(strict=False):
            raise CommandFailure(
                code="ref.target.inconsistent",
                summary="The managed reference target does not match its recorded source.",
                subject={"kind": "ref", "target-dir": target_dir},
                details={
                    "expected-source": str(source),
                    "actual-target": os.readlink(target) if target.is_symlink() else None,
                },
            )
        target.unlink()
        view.remove_ref(target_dir)


def query(
    model: RuntimeModelView,
    *,
    git_root: Path,
    install_id: str | None,
    install_path: str | None,
    ref_path: str | None,
    keys: list[str],
) -> list[dict[str, object]]:
    """Return Installations selected by identity, path, Ref, or fuzzy key."""

    candidates = _query_installations(
        model,
        install_id=install_id,
        install_path=install_path,
        ref_path=ref_path,
        keys=tuple(keys),
    )
    return [
        {
            "git-url": item.git_url,
            "commit-hash": item.commit_hash,
            "install-id": item.install_id,
            "install-path": item.install_path,
            "restore-state": (
                "available"
                if item.presentation_path is not None
                else installation_restore_state(git_root, item)
            ),
            **({"presentation-path": item.presentation_path} if item.presentation_path is not None else {}),
            "keys": list(item.keys),
            "refs": [
                {"src-sub-dir": ref.src_sub_dir, "target-dir": ref.target_dir}
                for ref in model.refs_for(item)
            ],
            "branch": item.branch,
            "tag": item.tag,
        }
        for item in candidates
    ]


def installation_restore_state(git_root: Path, installation: Installation) -> str:
    """Return the physical restore state for one Installation."""

    if repo_path_to_fs(git_root, installation.install_path).exists():
        return "available"
    if installation.tracked:
        return "restore-required"
    return "missing"


def ensure_install_commit(
    repository: Path,
    git_url: str,
    selector_kind: str,
    selector_value: str,
    commit_hash: str,
) -> None:
    """Fail as a structured command error if the selected commit is unavailable."""

    try:
        ensure_commit_available(repository, git_url, commit_hash)
    except GitCommitUnavailable as exc:
        raise CommandFailure(
            code="revision.unresolvable",
            summary="The requested Git revision could not be resolved.",
            subject={"kind": "git-source", "git-url": git_url},
            details={
                "operation": "fetch",
                "selector-kind": selector_kind,
                "selector-value": selector_value,
            },
        ) from exc


def ensure_selector_symlink(store: RuntimeStore, selector_install_path: str, share_install_path: str) -> None:
    """Create or refresh a selector Installation symlink to one share path."""

    _ensure_symlink(store, selector_install_path, share_install_path)


def ensure_install_worktree(
    repository: Path,
    target: Path,
    *,
    git_url: str,
    commit_hash: str,
    install_path: str,
) -> None:
    """Ensure one detached Git worktree is present, compatible, clean, and checked out."""

    if not target.exists() and not target.is_symlink():
        _create_worktree(repository, target, commit_hash, install_path=install_path)
        return

    existing = _inspect_worktree(target, install_path)
    if existing is None:
        _remove_install_path(target, install_path)
        _create_worktree(repository, target, commit_hash, install_path=install_path)
        return
    if existing.git_url != git_url:
        raise _installation_target_failure(install_path, "different-git-url")
    reusable = existing.detached and existing.clean
    if reusable:
        if existing.head_hash != commit_hash:
            _checkout_worktree(target, commit_hash, install_path)
        return

    _remove_worktree(repository, target, install_path=install_path)
    _create_worktree(repository, target, commit_hash, install_path=install_path)


@dataclass(frozen=True, slots=True)
class _ExistingWorktree:
    """The reusable state of one existing install-path worktree."""

    git_url: str | None
    detached: bool
    clean: bool
    head_hash: str | None


def _install_resolved(
    store: RuntimeStore,
    repository: Path,
    *,
    tracked: bool,
    git_url: str,
    branch: str,
    tag: str,
    keys: list[str],
    selector_kind: str,
    selector_value: str,
    commit_hash: str,
) -> Installation:
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        if selector_kind in {"branch", "tag"}:
            return _install_selector_resolved(
                store,
                repository,
                view,
                tracked=tracked,
                git_url=git_url,
                branch=branch,
                tag=tag,
                keys=keys,
                selector_value=selector_value,
                commit_hash=commit_hash,
            )
        return _install_commit_resolved(
            store,
            repository,
            view,
            tracked=tracked,
            git_url=git_url,
            keys=keys,
            commit_hash=commit_hash,
        )


def _install_selector_resolved(
    store: RuntimeStore,
    repository: Path,
    view: RuntimeWriteModelView,
    *,
    tracked: bool,
    git_url: str,
    branch: str,
    tag: str,
    keys: list[str],
    selector_value: str,
    commit_hash: str,
) -> Installation:
    selector_kind = "branch" if branch else "tag"
    install_path = _selector_install_path(git_url, selector_kind, selector_value)
    install_id = _install_id(install_path)
    existing = view.installation(install_id)
    if existing is not None and existing.install_path != install_path:
        raise _install_id_collision_failure(install_id, existing.install_path, install_path)
    if existing is not None and existing.commit_hash == commit_hash:
        _ensure_installation_in_share(store, repository, view, existing)
        return existing

    if existing is not None:
        _leave_share(store, view, existing)

    if existing is None:
        installation = Installation(
            tracked=tracked,
            git_url=git_url,
            commit_hash=commit_hash,
            install_id=install_id,
            install_path=install_path,
            keys=tuple(dict.fromkeys((*_default_keys(git_url, branch=branch, tag=tag), *keys))),
            branch=branch,
            tag=tag,
        )
        view.upsert_installation(installation)
    else:
        installation = replace(
            existing,
            commit_hash=commit_hash,
            tracked=tracked or bool(view.refs_for(existing)),
            keys=tuple(dict.fromkeys((*_default_keys(git_url, branch=branch, tag=tag), *keys))),
        )
        view.upsert_installation(installation)
    _ensure_installation_in_share(store, repository, view, installation)
    return installation


def _install_commit_resolved(
    store: RuntimeStore,
    repository: Path,
    view: RuntimeWriteModelView,
    *,
    tracked: bool,
    git_url: str,
    keys: list[str],
    commit_hash: str,
) -> Installation:
    share = _ensure_share_for_commit(store, repository, view, git_url, commit_hash)
    install_id = _install_id(share.install_path)
    existing = view.installation(install_id)
    if existing is not None and existing.install_path != share.install_path:
        raise _install_id_collision_failure(install_id, existing.install_path, share.install_path)
    if existing is not None:
        if tracked and not existing.tracked:
            existing = view.set_installation_tracking(existing, tracked=True)
        _ensure_installation_in_share(store, repository, view, existing)
        return existing

    installation = Installation(
        tracked=tracked,
        git_url=git_url,
        commit_hash=commit_hash,
        install_id=install_id,
        install_path=share.install_path,
        keys=tuple(dict.fromkeys((*_default_keys(git_url, branch="", tag=""), *keys))),
        branch="",
        tag="",
    )
    view.upsert_installation(installation)
    _ensure_installation_in_share(store, repository, view, installation)
    return installation


def _ensure_share_for_commit(
    store: RuntimeStore,
    repository: Path,
    view: RuntimeWriteModelView,
    git_url: str,
    commit_hash: str,
) -> InstallationShare:
    share = view.installation_share(git_url, commit_hash)
    install_path = share.install_path if share is not None else _selector_install_path(git_url, "commit", commit_hash)
    target = repo_path_to_fs(store.git_root, install_path)
    ensure_install_worktree(
        repository,
        target,
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path,
    )
    if share is not None:
        return share

    share = InstallationShare(
        git_url=git_url,
        commit_hash=commit_hash,
        install_path=install_path,
        install_ids=(),
        context_references=(),
        branch_refs=_current_branch_refs(store),
    )
    view.upsert_installation_share(share)
    return share


def _ensure_installation_in_share(
    store: RuntimeStore,
    repository: Path,
    view: RuntimeWriteModelView,
    installation: Installation,
) -> None:
    share = _ensure_share_for_commit(store, repository, view, installation.git_url, installation.commit_hash)
    install_ids = (
        share.install_ids
        if installation.install_id in share.install_ids
        else (*share.install_ids, installation.install_id)
    )
    branch_refs = share.branch_refs
    current_branch = current_branch_name(store.git_root)
    if current_branch is not None and current_branch not in branch_refs:
        branch_refs = (*branch_refs, current_branch)
    share = replace(share, install_ids=install_ids, branch_refs=branch_refs)
    view.upsert_installation_share(share)
    if installation.branch or installation.tag:
        _ensure_symlink(store, installation.install_path, share.install_path)


def _with_context_reference(
    share: InstallationShare,
    context_reference: InstallationContextReference,
) -> InstallationShare:
    """Return the share with one context reference inserted or replaced by owner/sub-install pair."""

    key = (context_reference.owner_install_id, context_reference.install_id)
    existing_keys = {(item.owner_install_id, item.install_id) for item in share.context_references}
    if key in existing_keys:
        context_references = tuple(
            context_reference if (item.owner_install_id, item.install_id) == key else item
            for item in share.context_references
        )
    else:
        context_references = (*share.context_references, context_reference)
    return replace(share, context_references=context_references)


def _ensure_symlink(store: RuntimeStore, selector_install_path: str, share_install_path: str) -> None:
    target = repo_path_to_fs(store.git_root, selector_install_path)
    source = repo_path_to_fs(store.git_root, share_install_path)
    if target.is_symlink() and target.resolve(strict=False) == source.resolve(strict=False):
        return
    _remove_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(os.path.relpath(source, start=target.parent), target, target_is_directory=True)
    except OSError as exc:
        raise _installation_target_failure(selector_install_path, "unavailable-path") from exc


def _leave_share(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
    installation: Installation,
) -> None:
    """Detach a replaced selector Installation without deleting its Installation record."""

    if installation.branch or installation.tag:
        _remove_path(repo_path_to_fs(store.git_root, installation.install_path))

    share = view.installation_share(installation.git_url, installation.commit_hash)
    if share is None:
        return
    _remove_from_installation_share(store, view, share, installation)


def _remove_from_installation_share(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
    share: InstallationShare,
    installation: Installation,
) -> None:
    """Remove one Installation from a share, deleting the share when empty."""

    remaining = tuple(item for item in share.install_ids if item != installation.install_id)
    context_references = tuple(
        item for item in share.context_references if item.owner_install_id != installation.install_id
    )
    if remaining:
        view.upsert_installation_share(
            replace(share, install_ids=remaining, context_references=context_references)
        )
        return

    current_branch = current_branch_name(store.git_root)
    branch_refs = tuple(item for item in share.branch_refs if item != current_branch)
    if context_references or branch_refs:
        view.upsert_installation_share(
            replace(share, install_ids=(), context_references=context_references, branch_refs=branch_refs)
        )
    else:
        _remove_path(repo_path_to_fs(store.git_root, share.install_path))
        view.remove_installation_share(installation.git_url, installation.commit_hash)


def _read_installation(store: RuntimeStore, install_id: str) -> Installation:
    with store.read_only_transaction() as transaction:
        return _find_installation(transaction.model_view(), install_id)


def _restore_resolved(store: RuntimeStore, repository: Path, install_id: str) -> Installation:
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        current = _find_installation(view, install_id)
        if not current.tracked:
            raise _installation_failure(
                "installation.tracking-state.invalid",
                current,
                {"required-tracked": True, "actual-tracked": False},
            )
        _ensure_restore_commit(repository, current)
        _ensure_installation_in_share(store, repository, view, current)
        return current


def _query_installations(
    model: RuntimeModelView,
    *,
    install_id: str | None,
    install_path: str | None,
    ref_path: str | None,
    keys: tuple[str, ...],
) -> tuple[Installation, ...]:
    """Apply import query selectors, including its user-facing fuzzy key search."""

    if install_id is not None:
        installation = model.installation(install_id)
        return (installation,) if installation is not None else ()
    if install_path is not None:
        installation = model.installation_at(install_path)
        return (installation,) if installation is not None else ()
    if ref_path is not None:
        reference = model.ref(ref_path)
        installation = model.installation(reference.install_id) if reference is not None else None
        return (installation,) if installation is not None else ()
    return _fuzzy_key_matches(model.installations, keys)


def _fuzzy_key_matches(installations: tuple[Installation, ...], keys: tuple[str, ...]) -> tuple[Installation, ...]:
    """Return fuzzy key matches ordered by matching-key and exact-match counts."""

    matches: list[tuple[int, int, Installation]] = []
    for installation in installations:
        matched_keys = tuple(
            installation_key
            for installation_key in installation.keys
            if any(query_key in installation_key for query_key in keys)
        )
        if matched_keys:
            exact_matches = sum(installation_key in keys for installation_key in matched_keys)
            matches.append((len(matched_keys), exact_matches, installation))
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return tuple(item[2] for item in matches)


def _revision_selector(*, branch: str, tag: str, commit: str) -> tuple[str, str]:
    selectors = (("branch", branch), ("tag", tag), ("commit", commit))
    selected = [(kind, value) for kind, value in selectors if value]
    if len(selected) != 1:
        raise ValueError("exactly one revision selector is required")
    return selected[0]


def _resolve_revision(repository: Path, git_url: str, *, kind: str, value: str) -> str:
    return resolve_revision(repository, git_url, kind=kind, value=value)


def _ensure_restore_commit(repository: Path, installation: Installation) -> None:
    try:
        ensure_commit_available(repository, installation.git_url, installation.commit_hash)
    except GitCommitUnavailable as exc:
        raise _installation_failure(
            "installation.restore.unavailable", installation, {"commit-hash": installation.commit_hash}
        ) from exc


def _inspect_worktree(target: Path, install_path: str) -> _ExistingWorktree | None:
    """Return Git worktree reuse facts, or ``None`` for a non-Git path."""

    try:
        controlled = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc
    if controlled.returncode != 0 or not controlled.stdout.strip():
        return None
    if Path(controlled.stdout.strip()).resolve() != target.resolve():
        return None

    try:
        remote = subprocess.run(
            ["git", "-C", str(target), "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
        )
        head = subprocess.run(
            ["git", "-C", str(target), "symbolic-ref", "--quiet", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        status = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
        head_commit = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc
    return _ExistingWorktree(
        git_url=remote.stdout.strip() if remote.returncode == 0 else None,
        detached=head.returncode == 1,
        clean=status.returncode == 0 and not status.stdout.strip(),
        head_hash=head_commit.stdout.strip() if head_commit.returncode == 0 else None,
    )


def _checkout_worktree(target: Path, commit_hash: str, install_path: str) -> None:
    try:
        subprocess.run(
            ["git", "-C", str(target), "checkout", "--detach", commit_hash],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc


def _create_worktree(repository: Path, target: Path, commit_hash: str, *, install_path: str) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "prune"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "add", "--detach", str(target), commit_hash],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc


def _remove_worktree(repository: Path, target: Path, *, install_path: str) -> None:
    try:
        subprocess.run(
            ["git", "-C", str(repository), "worktree", "remove", "--force", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        _remove_install_path(target, install_path)


def _remove_install_path(target: Path, install_path: str) -> None:
    try:
        _remove_path(target)
    except OSError as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc


def _selector_install_path(git_url: str, selector_kind: str, selector_value: str) -> str:
    domain, repository_name = repository_location(git_url)
    components = [".doctidex-git", "imports", domain, *repository_name]
    if selector_kind in {"branch", "tag"}:
        components.append(selector_kind)
    components.extend(selector_value.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise _installation_target_failure("/.doctidex-git/imports", "invalid-source-path")
    return f"/{'/'.join(components)}"


def _install_id(selector_install_path: str) -> str:
    return hashlib.sha256(selector_install_path.encode("utf-8")).hexdigest()[:16]


def _install_id_collision_failure(install_id: str, existing_path: str, computed_path: str) -> CommandFailure:
    return CommandFailure(
        code="installation.id.collision",
        summary="The derived installation id is already used by a different installation path.",
        subject={"kind": "installation", "install-id": install_id},
        details={"existing-install-path": existing_path, "computed-install-path": computed_path},
    )
def _ref_target_reservation(
    view: RuntimeModelView, target_dir: str
) -> tuple[str | None, BoundaryPoint | None]:
    """Return the rejection reason and boundary that block Ref creation at ``target_dir``."""

    if is_managed_imports_path(target_dir):
        return "managed-imports-directory", None
    if is_managed_worktrees_path(target_dir):
        return "managed-worktrees-directory", None
    boundary = view.first_boundary(target_dir)
    if boundary is None:
        return None, None
    return "existing-boundary", boundary


def _find_installation(model: RuntimeModelView, install_id: str) -> Installation:
    installation = model.installation(install_id)
    if installation is None:
        raise CommandFailure(
            code="installation.not-found",
            summary="The requested installation does not exist.",
            subject={"kind": "installation", "install-id": install_id},
            details={"operation": "find"},
        )
    return installation


def _parent_install_id(owner_store: RuntimeStore, parent_install_path: str) -> str:
    with owner_store.read_only_transaction() as transaction:
        installation = transaction.model_view().installation_at(parent_install_path)
    if installation is None:
        raise CommandFailure(
            code="installation.context.unavailable",
            summary="The owning Installation cannot be resolved.",
            subject={"kind": "installation", "install-path": parent_install_path},
            details={"owner-path": str(owner_store.git_root), "reason": "owner-installation-missing"},
        )
    return installation.install_id


def _select_installations(
    model: RuntimeModelView, install_id: str | None, *, untracked: bool, auto: bool
) -> tuple[Installation, ...]:
    if install_id:
        installation = model.installation(install_id)
        return (installation,) if installation is not None else ()
    if untracked:
        return tuple(item for item in model.installations if not item.tracked)
    return tuple(
        item
        for item in model.installations
        if not item.tracked or not model.refs_for(item)
    )


def _explicit_branch_snapshot_names(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
    branches: tuple[str, ...],
) -> tuple[str, ...]:
    current = current_branch_name(store.git_root)
    if current is not None and any(branch == current for branch in branches):
        raise _current_branch_removal_failure(current)
    return tuple(branch for branch in branches if branch in view.state.branch_snapshots)


def _stale_branch_snapshot_names(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
) -> tuple[str, ...]:
    local_branches = set(local_branch_names(store.git_root))
    current = current_branch_name(store.git_root)
    return tuple(
        branch
        for branch in view.state.branch_snapshots
        if branch not in local_branches and branch != current
    )


def _remove_branch_snapshot_history(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
    branches: tuple[str, ...],
) -> None:
    deleted = set(branches)
    view.remove_branch_snapshots(deleted)

    active_shares = tuple(
        _without_deleted_branch_refs(share, deleted)
        for share in view.state.installation_shares
    )
    remaining_snapshots: dict[str, BranchSnapshot] = {
        branch: replace(
            snapshot,
            installation_shares=tuple(
                _without_deleted_branch_refs(share, deleted)
                for share in snapshot.installation_shares
            ),
        )
        for branch, snapshot in view.state.branch_snapshots.items()
    }
    all_shares = (
        *active_shares,
        *(share for snapshot in remaining_snapshots.values() for share in snapshot.installation_shares),
    )
    share_groups = _share_groups(all_shares)
    orphan_keys = _orphaned_share_keys(share_groups)

    for share in active_shares:
        if _share_key(share) not in orphan_keys:
            view.upsert_installation_share(share)
    for key in orphan_keys:
        view.remove_installation_share(*key)

    view.replace_branch_snapshots(
        {
            branch: replace(
                snapshot,
                installation_shares=tuple(
                    share
                    for share in snapshot.installation_shares
                    if _share_key(share) not in orphan_keys
                ),
            )
            for branch, snapshot in remaining_snapshots.items()
        }
    )

    for key in orphan_keys:
        _remove_orphaned_share_path(store, share_groups[key][0])


def _without_deleted_branch_refs(
    share: InstallationShare,
    deleted: set[str],
) -> InstallationShare:
    branch_refs = tuple(branch for branch in share.branch_refs if branch not in deleted)
    if branch_refs == share.branch_refs:
        return share
    return replace(share, branch_refs=branch_refs)


def _share_key(share: InstallationShare) -> tuple[str, str]:
    return (share.git_url, share.commit_hash)


def _share_groups(
    shares: tuple[InstallationShare, ...],
) -> dict[tuple[str, str], tuple[InstallationShare, ...]]:
    grouped: dict[tuple[str, str], list[InstallationShare]] = {}
    for share in shares:
        grouped.setdefault(_share_key(share), []).append(share)
    return {key: tuple(records) for key, records in grouped.items()}


def _orphaned_share_keys(
    groups: dict[tuple[str, str], tuple[InstallationShare, ...]],
) -> set[tuple[str, str]]:
    return {
        key
        for key, records in groups.items()
        if all(_is_empty_installation_share(record) for record in records)
    }


def _is_empty_installation_share(share: InstallationShare) -> bool:
    return not share.install_ids and not share.context_references and not share.branch_refs


def _remove_orphaned_share_path(store: RuntimeStore, share: InstallationShare) -> None:
    try:
        _remove_path(repo_path_to_fs(store.git_root, share.install_path))
    except OSError as exc:
        raise CommandFailure(
            code="import.branch-snapshot.reconcile.failed",
            summary="The orphaned Installation share could not be removed.",
            subject={"kind": "installation-share", "install-path": share.install_path},
            details={"operation": "remove-orphaned-share"},
        ) from exc


def _current_branch_removal_failure(branch: str) -> CommandFailure:
    return CommandFailure(
        code="import.branch-snapshot.remove.current-branch",
        summary="The currently checked-out branch snapshot cannot be removed.",
        subject={"kind": "branch-snapshot", "branch": branch},
        details={"operation": "remove"},
    )


def _remove_installation_reference(
    store: RuntimeStore,
    view: RuntimeWriteModelView,
    installation: Installation,
) -> None:
    """Remove an Installation record and then detach its share membership."""

    if installation.branch or installation.tag:
        _remove_path(repo_path_to_fs(store.git_root, installation.install_path))
    view.remove_installations((installation.install_id,))

    share = view.installation_share(installation.git_url, installation.commit_hash)
    if share is None:
        return

    _remove_from_installation_share(store, view, share, installation)


def _installation_failure(code: str, installation: Installation, details: dict[str, object]) -> CommandFailure:
    return CommandFailure(
        code=code,
        summary="The installation cannot complete the requested operation.",
        subject={
            "kind": "installation",
            "install-id": installation.install_id,
            "install-path": installation.install_path,
        },
        details=details,
    )


def _installation_target_failure(path: str, occupant: str) -> CommandFailure:
    return CommandFailure(
        code="installation.target.unavailable",
        summary="The installation path cannot be used for the requested revision.",
        subject={"kind": "installation", "install-path": path},
        details={"operation": "install", "occupant": occupant},
    )


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _current_branch_refs(store: RuntimeStore) -> tuple[str, ...]:
    branch = current_branch_name(store.git_root)
    return (branch,) if branch is not None else ()


def _default_keys(git_url: str, *, branch: str, tag: str) -> tuple[str, ...]:
    parsed = git_url.split("://", 1)[-1]
    if ":" in parsed and "/" not in parsed.split(":", 1)[0]:
        parsed = parsed.split(":", 1)[1]
    base = parsed.removesuffix(".git").strip("/")
    return (base, *(f"{base}@{value}" for value in (branch, tag) if value))


def _blocked_installations(
    git_root: Path, model: RuntimeModelView, selected: tuple[Installation, ...]
) -> list[dict[str, object]]:
    links = {item.install_id: [] for item in selected if item.tracked}
    for link in scan_cross_boundary_links(git_root, model):
        if link.installation is not None and link.installation.install_id in links:
            links[link.installation.install_id].append(link.reference_details())
    result: list[dict[str, object]] = []
    for item in selected:
        if not item.tracked:
            continue
        reference_targets = [ref.target_dir for ref in model.refs_for(item)]
        item_links = links.get(item.install_id, [])
        if item_links or reference_targets:
            result.append(
                {
                    "install-id": item.install_id,
                    "install-path": item.install_path,
                    "blocking-links": item_links,
                    "blocking-ref-target-dirs": reference_targets,
                }
            )
    return result
