"""Import installation and managed-reference command workflows."""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import Installation, Ref
from whero.doctidex.model_view import scan_markdown_links
from whero.doctidex.paths import normalize_repo_path, repo_path_to_fs
from whero.doctidex.repository import (
    GitCommitUnavailable,
    ensure_commit_available,
    repository_location,
    resolve_revision,
)
from whero.doctidex.store.coordination import WorkflowCoordinator
from whero.doctidex.store.model_view import RuntimeModelView
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
) -> None:
    """Remove selected Installations after confirming no link or Ref blocks them."""

    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
        selected = _select_installations(view, install_id, untracked=untracked, auto=auto)
        selected_ids = {item.install_id for item in selected}
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
            _remove_path(repo_path_to_fs(store.git_root, item.install_path))
        view.remove_installations(selected_ids)


def ref(store: RuntimeStore, install_id: str, src_sub_dir: str, target_dir: str) -> Ref:
    """Create a managed symbolic reference into one Installation."""

    target_dir = normalize_repo_path(target_dir, parameter="--target-dir")
    if src_sub_dir:
        src_sub_dir = normalize_repo_path(src_sub_dir, parameter="--src-sub-dir")
    with store.write_transaction() as transaction:
        view = transaction.write_model_view()
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
            for link in scan_markdown_links(store.git_root, view)
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
    model: RuntimeModelView, *, install_id: str | None, install_path: str | None, ref_path: str | None, keys: list[str]
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
            **(
                {"presentation-path": item.presentation_path}
                if item.presentation_path is not None
                else {}
            ),
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


def create_worktree(repository: Path, target: Path, commit_hash: str, *, install_path: str) -> None:
    """Create one detached Git worktree at the requested install path."""

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


def prepare_install_path(
    repository: Path,
    target: Path,
    *,
    git_url: str,
    commit_hash: str,
    install_path: str,
) -> bool:
    """Prepare an existing install-path, returning whether it was reused."""

    if not target.exists() and not target.is_symlink():
        return False

    existing = _inspect_worktree(target, install_path)
    if existing is None:
        _remove_install_path(target, install_path)
        return False
    if existing.git_url != git_url:
        raise _installation_target_failure(install_path, "different-git-url")
    if existing.detached and existing.clean:
        _checkout_worktree(target, commit_hash, install_path)
        return True

    _remove_worktree(repository, target, install_path=install_path)
    return False


@dataclass(frozen=True, slots=True)
class _ExistingWorktree:
    """The reusable state of one existing install-path worktree."""

    git_url: str | None
    detached: bool
    clean: bool


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
        existing = (
            view.installation_for_selector(git_url, branch=branch, tag=tag)
            if selector_kind in {"branch", "tag"}
            else view.installation_for_commit(git_url, commit_hash)
        )
        keep_existing = existing is not None and existing.commit_hash == commit_hash
        install_path = existing.install_path if keep_existing else _install_path(git_url, selector_value)
        target = repo_path_to_fs(store.git_root, install_path)
        if not prepare_install_path(
            repository,
            target,
            git_url=git_url,
            commit_hash=commit_hash,
            install_path=install_path,
        ):
            create_worktree(repository, target, commit_hash, install_path=install_path)
        if keep_existing:
            return existing

        installation = Installation(
            tracked=tracked or bool(existing is not None and view.refs_for(existing)),
            git_url=git_url,
            commit_hash=commit_hash,
            install_id=uuid.uuid4().hex,
            install_path=install_path,
            keys=tuple(dict.fromkeys((*_default_keys(git_url, branch=branch, tag=tag), *keys))),
            branch=branch,
            tag=tag,
        )
        if existing is None:
            view.upsert_installation(installation)
        else:
            view.replace_installation(existing, installation)
        return installation


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
        target = repo_path_to_fs(store.git_root, current.install_path)
        try:
            if not prepare_install_path(
                repository,
                target,
                git_url=current.git_url,
                commit_hash=current.commit_hash,
                install_path=current.install_path,
            ):
                create_worktree(repository, target, current.commit_hash, install_path=current.install_path)
        except CommandFailure as exc:
            if exc.code != "installation.target.unavailable":
                raise
            raise _installation_failure(
                "installation.restore.unavailable", current, {"commit-hash": current.commit_hash}
            ) from exc
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
    except OSError as exc:
        raise _installation_target_failure(install_path, "unavailable-path") from exc
    return _ExistingWorktree(
        git_url=remote.stdout.strip() if remote.returncode == 0 else None,
        detached=head.returncode == 1,
        clean=status.returncode == 0 and not status.stdout.strip(),
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


def _install_path(git_url: str, selector_value: str) -> str:
    domain, repository_name = _repository_location(git_url)
    components = (".doctidex-git", "imports", domain, *repository_name, *selector_value.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise _installation_target_failure("/.doctidex-git/imports", "invalid-source-path")
    return f"/{'/'.join(components)}"


def _repository_location(git_url: str) -> tuple[str, tuple[str, ...]]:
    return repository_location(git_url)


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
    for link in scan_markdown_links(git_root, model):
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
