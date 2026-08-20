"""Installation-context detection, owner routing, and RuntimeStore variant."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Self

from whero.doctidex import imports as import_workflow
from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import BoundaryPoint, Installation, Ref, RuntimeState, Worktree
from whero.doctidex.paths import fs_path_to_repo_path, repo_path_to_fs
from whero.doctidex.store.runtime import RuntimeStore


@dataclass(frozen=True, slots=True)
class InstallationContext:
    """The owner root and repository-internal install path for one resolved Installation."""

    owner_root: Path
    install_path: str


def resolve_installation_context(root: Path) -> InstallationContext | None:
    """Return Installation context when ``root`` is inside an owner's Installation."""

    owners = _owner_roots(root)
    if len(owners) > 1:
        raise CommandFailure(
            code="installation.owner.ambiguous",
            summary="The requested path is nested in multiple Installation workspaces.",
            subject={"kind": "installation", "path": str(root)},
            details={"owner-paths": [str(owner) for owner in owners]},
        )
    if not owners:
        return None

    owner = owners[0]
    install_path = fs_path_to_repo_path(owner, root)
    return InstallationContext(owner_root=owner, install_path=install_path)


def _owner_roots(root: Path) -> tuple[Path, ...]:
    """Return owner roots from ancestor ``.doctidex-git`` directories, nearest first."""

    return tuple(parent.parent for parent in root.parents if parent.name == ".doctidex-git")


class InstallationRuntimeStore:
    """A RuntimeStore-shaped adapter backed by one owner work model."""

    def __init__(self, context: InstallationContext) -> None:
        self.context = context
        self.owner_store = RuntimeStore(context.owner_root)
        self.installation_store = RuntimeStore(repo_path_to_fs(context.owner_root, context.install_path))
        if not self.owner_store.workspace_path.is_dir():
            raise CommandFailure(
                code="work-model.uninitialized",
                summary="The Installation owner has not been initialized.",
                subject={"kind": "workspace", "path": "/.doctidex-git"},
                details={"required-command": "init", "owner-path": str(context.owner_root)},
            )
        if not self.installation_store.workspace_path.is_dir():
            raise _local_declaration_error(context)

    @property
    def git_root(self) -> Path:
        return self.context.owner_root

    @property
    def workspace_path(self) -> Path:
        return self.owner_store.workspace_path

    @property
    def transactions_path(self) -> Path:
        return self.owner_store.transactions_path

    def read_only_transaction(self) -> InstallationReadOnlyTransaction:
        return InstallationReadOnlyTransaction(self)

    def write_transaction(self) -> InstallationWriteTransaction:
        return InstallationWriteTransaction(self)

    def diagnostic_transaction(self):
        return self.owner_store.diagnostic_transaction()

    def read_state(self) -> RuntimeState:
        return self.owner_store.read_state()

    def restore_import(self, coordinator, install_id: str) -> Installation:
        """Restore an Installation-local import into the owner work model."""

        with self.installation_store.unlocked_read_only_transaction() as transaction:
            local = transaction.model_view().installation(install_id)
        if local is None:
            raise CommandFailure(
                code="installation.not-found",
                summary="The requested installation does not exist.",
                subject={"kind": "installation", "install-id": install_id},
                details={"operation": "find"},
            )
        owner_installation = import_workflow.install(
            self.owner_store,
            coordinator,
            tracked=False,
            git_url=local.git_url,
            branch="",
            tag="",
            commit=local.commit_hash,
            keys=list(local.keys),
        )
        return replace(
            local,
            presentation_path=str(
                repo_path_to_fs(self.owner_store.git_root, owner_installation.install_path)
            ),
        )


class InstallationRuntimeModelView:
    """Coordinate owner and Installation RuntimeModelViews without merging state."""

    def __init__(
        self,
        context: InstallationContext,
        owner_view,
        installation_view,
    ) -> None:
        self.context = context
        self._owner_view = owner_view
        self._installation_view = installation_view

    @property
    def state(self) -> RuntimeState:
        return self._installation_view.state

    @property
    def installations(self) -> tuple[Installation, ...]:
        return tuple(self._mapped_installation(item) for item in self._installation_view.installations)

    @property
    def refs(self) -> tuple[Ref, ...]:
        return self._installation_view.refs

    @property
    def worktrees(self) -> tuple[Worktree, ...]:
        return self._installation_view.worktrees

    @property
    def boundary_points(self) -> tuple[BoundaryPoint, ...]:
        return self._installation_view.boundary_points

    def installation(self, install_id: str) -> Installation | None:
        return self._mapped_installation(self._installation_view.installation(install_id))

    def installation_at(self, install_path: str) -> Installation | None:
        return self._mapped_installation(self._installation_view.installation_at(install_path))

    def installation_for_selector(self, git_url: str, *, branch: str, tag: str) -> Installation | None:
        return self._mapped_installation(
            self._installation_view.installation_for_selector(git_url, branch=branch, tag=tag)
        )

    def installation_for_commit(self, git_url: str, commit_hash: str) -> Installation | None:
        return self._mapped_installation(
            self._installation_view.installation_for_commit(git_url, commit_hash)
        )

    def ref(self, target_dir: str) -> Ref | None:
        return self._installation_view.ref(target_dir)

    def refs_for(self, installation: Installation) -> tuple[Ref, ...]:
        return self._installation_view.refs_for(installation)

    def worktree(self, work_path: str) -> Worktree | None:
        return self._installation_view.worktree(work_path)

    def custom_boundary_point(self, path: str) -> BoundaryPoint | None:
        return self._installation_view.custom_boundary_point(path)

    def boundary_point(self, path: str) -> BoundaryPoint | None:
        return self._installation_view.boundary_point(path)

    def first_boundary(self, path: str) -> BoundaryPoint | None:
        return self._installation_view.first_boundary(path)

    def first_boundaries(self, paths) -> tuple[BoundaryPoint | None, ...]:
        return self._installation_view.first_boundaries(paths)

    def ref_for_boundary(self, boundary: BoundaryPoint | None) -> Ref | None:
        return self._installation_view.ref_for_boundary(boundary)

    def installation_for_boundary(self, boundary: BoundaryPoint | None) -> Installation | None:
        return self._installation_view.installation_for_boundary(boundary)

    def _mapped_installation(self, local: Installation | None) -> Installation | None:
        if local is None:
            return None
        owner_installation = self._owner_view.installation_for_commit(local.git_url, local.commit_hash)
        if owner_installation is None:
            return None
        return replace(
            local,
            presentation_path=str(
                repo_path_to_fs(self.context.owner_root, owner_installation.install_path)
            ),
        )


class InstallationReadOnlyTransaction:
    """Read-only transaction exposing an InstallationRuntimeModelView."""

    def __init__(self, store: InstallationRuntimeStore) -> None:
        self.store = store
        self._owner_transaction = None
        self._installation_transaction = None
        self._model_view = None

    def __enter__(self) -> Self:
        owner_transaction = self.store.owner_store.read_only_transaction()
        owner_transaction.__enter__()
        self._owner_transaction = owner_transaction
        try:
            installation_transaction = self.store.installation_store.unlocked_read_only_transaction()
            installation_transaction.__enter__()
            self._installation_transaction = installation_transaction
            owner_view = owner_transaction.model_view()
            self._model_view = InstallationRuntimeModelView(
                self.store.context,
                owner_view,
                installation_transaction.model_view(),
            )
        except Exception:
            exc_info = _current_exc_info()
            if self._installation_transaction is not None:
                self._installation_transaction.__exit__(*exc_info)
            owner_transaction.__exit__(*exc_info)
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        assert self._owner_transaction is not None
        if self._installation_transaction is not None:
            self._installation_transaction.__exit__(exc_type, exc, traceback)
        return self._owner_transaction.__exit__(exc_type, exc, traceback)

    def model_view(self):
        assert self._model_view is not None
        return self._model_view


class InstallationWriteTransaction:
    """Write transaction for ``import restore`` that only mutates owner."""

    def __init__(self, store: InstallationRuntimeStore) -> None:
        self.store = store
        self._owner_transaction = None
        self._installation_transaction = None
        self._model_view = None

    def __enter__(self) -> Self:
        owner_transaction = self.store.owner_store.write_transaction()
        owner_transaction.__enter__()
        self._owner_transaction = owner_transaction
        try:
            installation_transaction = self.store.installation_store.unlocked_read_only_transaction()
            installation_transaction.__enter__()
            self._installation_transaction = installation_transaction
            owner_view = owner_transaction.model_view()
            self._model_view = InstallationRuntimeModelView(
                self.store.context,
                owner_view,
                installation_transaction.model_view(),
            )
        except Exception:
            exc_info = _current_exc_info()
            if self._installation_transaction is not None:
                self._installation_transaction.__exit__(*exc_info)
            owner_transaction.__exit__(*exc_info)
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        assert self._owner_transaction is not None
        if self._installation_transaction is not None:
            self._installation_transaction.__exit__(exc_type, exc, traceback)
        return self._owner_transaction.__exit__(exc_type, exc, traceback)

    def write_model_view(self):
        assert self._model_view is not None
        return self._model_view


def _local_declaration_error(context: InstallationContext) -> CommandFailure:
    return CommandFailure(
        code="installation.context.unavailable",
        summary="The Installation work model declarations cannot be read.",
        subject={"kind": "installation", "install-path": context.install_path},
        details={"owner-path": str(context.owner_root), "reason": "declarations-invalid"},
    )


def _current_exc_info():
    import sys

    return sys.exc_info()


__all__ = [
    "InstallationContext",
    "InstallationRuntimeModelView",
    "InstallationRuntimeStore",
    "resolve_installation_context",
]
