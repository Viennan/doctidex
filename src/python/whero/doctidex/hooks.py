"""Git hook installation and worker command entry points for doctidex-git."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from whero.doctidex import imports as import_workflow
from whero.doctidex import validate as validate_workflow
from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import BranchSnapshot, Installation, InstallationShare
from whero.doctidex.paths import repo_path_to_fs
from whero.doctidex.repository import branch_has_workspace, branch_name_from_ref, current_branch_name
from whero.doctidex.store.files import StoreFailure, atomic_write_bytes
from whero.doctidex.store.runtime import RuntimeStore


def install_hooks(git_root: Path) -> None:
    """Install the supported Git hooks for one repository."""

    hooks_path = _hooks_path(git_root)
    command_path = _command_path()
    _write_hook(hooks_path / "post-checkout", _post_checkout_script(command_path))
    _write_hook(hooks_path / "pre-commit", _pre_commit_script(command_path))


def run_post_checkout(git_root: Path, hook_args: list[str]) -> None:
    """Run the post-checkout branch snapshot worker for one Git root."""

    if len(hook_args) >= 2:
        old_branch = branch_name_from_ref(hook_args[0])
        new_branch = branch_name_from_ref(hook_args[1])
        if old_branch is None or new_branch is None:
            return
        if not _both_have_workspace(git_root, old_branch, new_branch):
            return
        save_old_branch = True
    else:
        new_branch = current_branch_name(git_root)
        if new_branch is None or not branch_has_workspace(git_root, new_branch):
            return
        old_branch = None
        save_old_branch = False

    store = RuntimeStore(git_root)
    old_installations: tuple[Installation, ...] = ()

    def update(document: dict[str, object]) -> dict[str, object]:
        nonlocal old_installations
        current = BranchSnapshot.from_json(document, artifact="runtime.json")
        old_installations = current.installations
        if save_old_branch:
            document = _save_snapshot(document, old_branch or "")
        target = _target_snapshot(document, new_branch)
        document["imports"] = [item.to_json() for item in target.installations]
        document["installation-shares"] = [
            item.to_json()
            for item in _merge_share_membership(
                document.get("installation-shares", []),
                target.installation_shares,
            )
        ]
        document["worktrees"] = [item.to_json() for item in current.worktrees]
        return document

    def after_update(document: dict[str, object]) -> None:
        final = BranchSnapshot.from_json(document, artifact="runtime.json")
        _align_physical_objects(git_root, old_installations, final.installations, final.installation_shares)

    store.update_runtime_json(update, after_update=after_update)


def run_pre_commit(git_root: Path) -> None:
    """Run the pre-commit work-model validation worker for one Git root."""

    store = RuntimeStore(git_root)
    if not store.workspace_path.is_dir():
        return
    result = validate_workflow.validate(store, model_structure=True)
    if not result.valid:
        raise CommandFailure(
            code="hook.pre-commit.validation.failed",
            summary="The pre-commit work-model validation failed.",
            subject={"kind": "workspace", "path": "/.doctidex-git"},
            details={"diagnostics": list(result.diagnostics)},
        )


def _save_snapshot(document: dict[str, object], branch: str) -> dict[str, object]:
    snapshot = BranchSnapshot.from_json(document, artifact="runtime.json")
    branch_snapshots = document.get("branch-snapshots")
    if not isinstance(branch_snapshots, dict):
        branch_snapshots = {}
        document["branch-snapshots"] = branch_snapshots
    branch_snapshots[branch] = snapshot.to_json()
    return document


def _target_snapshot(document: dict[str, object], branch: str) -> BranchSnapshot:
    branch_snapshots = document.get("branch-snapshots")
    if not isinstance(branch_snapshots, dict):
        return BranchSnapshot(installations=(), worktrees=(), installation_shares=())
    value = branch_snapshots.get(branch)
    if value is None:
        return BranchSnapshot(installations=(), worktrees=(), installation_shares=())
    return BranchSnapshot.from_json(value, artifact="runtime.json")


def _merge_share_membership(
    current_value: object,
    target_shares: tuple[InstallationShare, ...],
) -> tuple[InstallationShare, ...]:
    current_shares = tuple(
        InstallationShare.from_json(item, artifact="runtime.json")
        for item in _as_list(current_value)
    )
    target_by_key = {_share_key(item): item for item in target_shares}
    merged: list[InstallationShare] = []
    for current in current_shares:
        target = target_by_key.get(_share_key(current))
        if target is None:
            merged.append(replace(current, install_ids=(), context_references=()))
        else:
            merged.append(
                replace(
                    current,
                    install_ids=target.install_ids,
                    context_references=target.context_references,
                )
            )
    current_keys = {_share_key(item) for item in current_shares}
    merged.extend(item for item in target_shares if _share_key(item) not in current_keys)
    return tuple(merged)


def _align_physical_objects(
    git_root: Path,
    old_installations: object,
    new_installations: tuple[Installation, ...],
    shares: tuple[InstallationShare, ...],
) -> None:
    old = _installations_from_json(old_installations)
    shares_by_key = {_share_key(item): item for item in shares}
    new_paths = {item.install_path for item in new_installations}

    for installation in old:
        if not (installation.branch or installation.tag):
            continue
        if installation.install_path in new_paths:
            continue
        _remove_selector_symlink(git_root, installation.install_path)

    missing_shares: list[str] = []
    for share in shares:
        share_path = repo_path_to_fs(git_root, share.install_path)
        if not share_path.exists() and not share_path.is_symlink():
            missing_shares.append(share.install_path)

    if missing_shares:
        raise CommandFailure(
            code="hook.post-checkout.reconcile.failed",
            summary="The post-checkout runtime snapshot cannot be reconciled because a shared worktree is missing.",
            subject={"kind": "workspace", "path": "/.doctidex-git/runtime.json"},
            details={"operation": "physical-reconcile", "missing-share-worktrees": missing_shares},
        )

    for installation in new_installations:
        share = shares_by_key.get((installation.git_url, installation.commit_hash))
        if share is None:
            raise CommandFailure(
                code="hook.post-checkout.reconcile.failed",
                summary="The post-checkout runtime snapshot refers to an unknown Installation share.",
                subject={"kind": "installation", "install-id": installation.install_id},
                details={"operation": "physical-reconcile"},
            )
        if installation.branch or installation.tag:
            import_workflow.ensure_selector_symlink(
                RuntimeStore(git_root),
                installation.install_path,
                share.install_path,
            )


def _installations_from_json(value: object) -> tuple[Installation, ...]:
    return tuple(Installation.from_json(item, artifact="runtime.json") for item in _as_list(value))


def _share_key(share: InstallationShare) -> tuple[str, str]:
    return (share.git_url, share.commit_hash)


def _as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return value


def _remove_selector_symlink(git_root: Path, install_path: str) -> None:
    target = repo_path_to_fs(git_root, install_path)
    if target.is_symlink() or target.is_file():
        try:
            target.unlink()
        except OSError as exc:
            raise CommandFailure(
                code="hook.post-checkout.reconcile.failed",
                summary="The post-checkout runtime snapshot could not remove a stale selector symlink.",
                subject={"kind": "installation", "install-path": install_path},
                details={"operation": "remove-selector-symlink"},
            ) from exc


def _both_have_workspace(git_root: Path, old_branch: str, new_branch: str) -> bool:
    return branch_has_workspace(git_root, old_branch) and branch_has_workspace(git_root, new_branch)


def _hooks_path(git_root: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "-C", str(git_root), "rev-parse", "--git-path", "hooks"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise CommandFailure(
            code="hook.install.unavailable",
            summary="The Git hooks directory could not be resolved.",
            subject={"kind": "repository", "path": str(git_root)},
            details={"operation": "resolve-hooks-path"},
        ) from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        raise CommandFailure(
            code="hook.install.unavailable",
            summary="The Git hooks directory could not be resolved.",
            subject={"kind": "repository", "path": str(git_root)},
            details={"operation": "resolve-hooks-path"},
        )
    raw = completed.stdout.strip()
    path = Path(raw)
    if not path.is_absolute():
        path = git_root / path
    return path.resolve()


def _command_path() -> str:
    candidates: list[Path] = []
    argv0 = Path(sys.argv[0])
    if argv0.name == "doctidex-git" or "doctidex-git" in argv0.name:
        candidates.append(argv0.resolve())
    executable = shutil.which("doctidex-git")
    if executable is not None:
        candidates.append(Path(executable).resolve())
    adjacent = Path(sys.executable).resolve().parent / "doctidex-git"
    if adjacent.is_file():
        candidates.append(adjacent)
    prefix_adjacent = Path(sys.prefix) / "bin" / "doctidex-git"
    if prefix_adjacent.is_file():
        candidates.append(prefix_adjacent.resolve())
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise CommandFailure(
        code="hook.command.unavailable",
        summary="The doctidex-git command path could not be resolved for hook installation.",
        subject={"kind": "command", "name": "doctidex-git"},
        details={"operation": "install"},
    )


def _post_checkout_script(command_path: str) -> str:
    quoted = shlex.quote(command_path)
    return f"#!/bin/sh\nexec {quoted} hook post-checkout \"$@\"\n"


def _pre_commit_script(command_path: str) -> str:
    quoted = shlex.quote(command_path)
    return f"#!/bin/sh\nexec {quoted} hook pre-commit \"$@\"\n"


def _write_hook(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_bytes(path, content.encode(), store="hooks", phase="install")
        os.chmod(path, 0o755)
    except StoreFailure as exc:
        raise CommandFailure(
            code="hook.install.unavailable",
            summary="The Git hook could not be installed.",
            subject={"kind": "git-hook", "path": str(path)},
            details={"operation": "write"},
        ) from exc
    except OSError as exc:
        raise CommandFailure(
            code="hook.install.unavailable",
            summary="The Git hook could not be installed.",
            subject={"kind": "git-hook", "path": str(path)},
            details={"operation": "write"},
        ) from exc
