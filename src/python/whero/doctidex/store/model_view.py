"""Work-model views bound to RuntimeStore transactions."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from functools import wraps
from typing import TYPE_CHECKING, cast

from whero.doctidex.model import (
    BoundaryPoint,
    BranchSnapshot,
    Installation,
    InstallationContextReference,
    InstallationShare,
    Ref,
    RuntimeState,
    Worktree,
)

if TYPE_CHECKING:
    from .runtime import (
        RuntimeRepairTransaction,
        RuntimeTransaction,
        RuntimeWriteTransaction,
    )

def _requires_current_indexes[**P, R](method: Callable[P, R]) -> Callable[P, R]:
    @wraps(method)
    def wrapper(self: RuntimeModelView, *args: P.args, **kwargs: P.kwargs) -> R:
        self._transaction.ensure_indexes_current()
        return method(self, *args, **kwargs)

    return wrapper


class RuntimeModelView:
    """Provide common work-model queries over one Transaction's maintained indexes."""

    def __init__(self, transaction: RuntimeTransaction) -> None:
        self._transaction = transaction

    @property
    def state(self) -> RuntimeState:
        """Return the current RuntimeState held by the transaction."""

        return self._transaction.state

    @property
    def installations(self) -> tuple[Installation, ...]:
        """Return all installations in the current state."""

        return self.state.installations

    @property
    def refs(self) -> tuple[Ref, ...]:
        """Return all refs in the current state."""

        return self.state.refs

    @property
    def worktrees(self) -> tuple[Worktree, ...]:
        """Return all worktrees in the current state."""

        return self.state.worktrees

    @property
    @_requires_current_indexes
    def boundary_points(self) -> tuple[BoundaryPoint, ...]:
        """Return all boundary points, including derived ones."""

        return self._transaction._boundary_points

    @_requires_current_indexes
    def installation(self, install_id: str) -> Installation | None:
        """Return the installation with ``install_id``, if present."""

        return self._transaction._installations_by_id.get(install_id)

    @_requires_current_indexes
    def installation_at(self, install_path: str) -> Installation | None:
        """Return the installation at ``install_path``, if present."""

        return self._transaction._installations_by_path.get(install_path)

    @_requires_current_indexes
    def installation_share(self, git_url: str, commit_hash: str) -> InstallationShare | None:
        """Return the installation share matching one Git URL and commit."""

        return self._transaction._installation_shares_by_commit.get((git_url, commit_hash))

    @_requires_current_indexes
    def context_reference(
        self, owner_install_id: str, install_id: str
    ) -> tuple[InstallationShare, InstallationContextReference] | None:
        """Return the owner share and context reference for one parent/sub-install pair."""

        return self._transaction._context_references_by_owner_install.get((owner_install_id, install_id))

    @_requires_current_indexes
    def ref(self, target_dir: str) -> Ref | None:
        """Return the Ref at ``target_dir``, if present."""

        return self._transaction._refs_by_target_dir.get(target_dir)

    @_requires_current_indexes
    def refs_for(self, installation: Installation) -> tuple[Ref, ...]:
        """Return the refs that point into ``installation``."""

        return self._transaction._refs_by_installation.get(installation.install_id, ())

    @_requires_current_indexes
    def worktree(self, work_path: str) -> Worktree | None:
        """Return the worktree at ``work_path``, if present."""

        return self._transaction._worktrees_by_path.get(work_path)

    @_requires_current_indexes
    def custom_boundary_point(self, path: str) -> BoundaryPoint | None:
        """Return the custom boundary point at ``path``, if present."""

        return self._transaction._custom_boundary_points_by_path.get(path)

    @_requires_current_indexes
    def boundary_point(self, path: str) -> BoundaryPoint | None:
        """Return the boundary point at exactly ``path``, if present."""

        return self._transaction._boundary_points_by_path.get(path)

    def first_boundary(self, path: str) -> BoundaryPoint | None:
        """Return the first boundary ancestor of ``path``."""

        return self.first_boundaries((path,))[0]

    @_requires_current_indexes
    def first_boundaries(self, paths: Iterable[str]) -> tuple[BoundaryPoint | None, ...]:
        """Return the first boundary ancestor for each requested path."""

        return tuple(
            next(
                (
                    self._transaction._boundary_points_by_path[ancestor]
                    for ancestor in _ancestor_paths(path)
                    if ancestor in self._transaction._boundary_points_by_path
                ),
                None,
            )
            for path in paths
        )

    def ref_for_boundary(self, boundary: BoundaryPoint | None) -> Ref | None:
        """Return the Ref represented by an import-ref boundary."""

        if boundary is None or boundary.type != "import-ref":
            return None
        return self.ref(boundary.path)

    def installation_for_boundary(self, boundary: BoundaryPoint | None) -> Installation | None:
        """Return the Installation represented by an import or import-ref boundary."""

        if boundary is None:
            return None
        if boundary.type == "import":
            return self.installation_at(boundary.path)
        reference = self.ref_for_boundary(boundary)
        return self.installation(reference.install_id) if reference is not None else None


class RuntimeWriteModelView(RuntimeModelView):
    """Provide standard work-model updates through a write Transaction."""

    def set_installation_tracking(self, installation: Installation, *, tracked: bool) -> Installation:
        """Return the installation with the requested tracking state, persisted in place."""

        replacement = replace(installation, tracked=tracked)
        self.upsert_installation(replacement)
        return replacement

    def upsert_custom_boundary_points(self, points: Iterable[BoundaryPoint]) -> None:
        """Insert or replace custom boundary points by path."""

        replacements = {point.path: point for point in points}
        if not replacements:
            return
        updated = tuple(replacements.pop(current.path, current) for current in self.state.custom_boundary_points)
        updated = (*updated, *replacements.values())
        if updated != self.state.custom_boundary_points:
            self._write_transaction._replace_collections(custom_boundary_points=updated)

    def remove_custom_boundary_points(self, paths: Iterable[str]) -> None:
        """Remove custom boundary points whose paths are selected."""

        selected_paths = set(paths)
        if not selected_paths:
            return
        updated = tuple(item for item in self.state.custom_boundary_points if item.path not in selected_paths)
        if updated != self.state.custom_boundary_points:
            self._write_transaction._replace_collections(custom_boundary_points=updated)

    def upsert_installation(self, installation: Installation) -> None:
        """Insert or replace one installation by install-id."""

        installations = tuple(
            installation if item.install_id == installation.install_id else item for item in self.state.installations
        )
        if self.installation(installation.install_id) is None:
            installations = (*installations, installation)
        self._write_transaction._replace_collections(installations=installations)

    def remove_installations(self, install_ids: Iterable[str]) -> None:
        """Remove installations whose install-ids are selected."""

        selected_ids = set(install_ids)
        self._write_transaction._replace_collections(
            installations=tuple(item for item in self.state.installations if item.install_id not in selected_ids)
        )

    def upsert_installation_share(self, share: InstallationShare) -> None:
        """Insert or replace one installation share by Git URL and commit."""

        shares = tuple(
            share
            if (item.git_url, item.commit_hash) == (share.git_url, share.commit_hash)
            else item
            for item in self.state.installation_shares
        )
        if self.installation_share(share.git_url, share.commit_hash) is None:
            shares = (*shares, share)
        self._write_transaction._replace_collections(installation_shares=shares)

    def remove_installation_share(self, git_url: str, commit_hash: str) -> None:
        """Remove the installation share for one Git URL and commit."""

        self._write_transaction._replace_collections(
            installation_shares=tuple(
                item
                for item in self.state.installation_shares
                if (item.git_url, item.commit_hash) != (git_url, commit_hash)
            )
        )

    def replace_installation_shares(self, shares: Iterable[InstallationShare]) -> None:
        """Replace the complete active Installation share collection."""

        self._write_transaction._replace_collections(installation_shares=tuple(shares))

    def upsert_ref(self, reference: Ref) -> None:
        """Insert or replace one Ref by target-dir."""

        refs = tuple(reference if item.target_dir == reference.target_dir else item for item in self.state.refs)
        if self.ref(reference.target_dir) is None:
            refs = (*refs, reference)
        self._write_transaction._replace_collections(refs=refs)

    def remove_ref(self, target_dir: str) -> None:
        """Remove the Ref at ``target_dir``."""

        self._write_transaction._replace_collections(
            refs=tuple(item for item in self.state.refs if item.target_dir != target_dir)
        )

    def upsert_worktree(self, worktree: Worktree) -> None:
        """Insert or replace one worktree by work-path."""

        worktrees = tuple(worktree if item.work_path == worktree.work_path else item for item in self.state.worktrees)
        if self.worktree(worktree.work_path) is None:
            worktrees = (*worktrees, worktree)
        self._write_transaction._replace_collections(worktrees=worktrees)

    def remove_worktrees(self, work_paths: Iterable[str]) -> None:
        """Remove worktrees whose work-paths are selected."""

        selected_paths = set(work_paths)
        self._write_transaction._replace_collections(
            worktrees=tuple(item for item in self.state.worktrees if item.work_path not in selected_paths)
        )

    def replace_branch_snapshots(self, branch_snapshots: dict[str, BranchSnapshot]) -> None:
        """Replace the branch snapshot map in the current state."""

        self._write_transaction._replace_collections(branch_snapshots=branch_snapshots)

    def remove_branch_snapshots(self, branch_names: Iterable[str]) -> None:
        """Remove branch snapshots whose branch names are selected."""

        selected_names = set(branch_names)
        if not selected_names:
            return
        updated = {
            branch: snapshot
            for branch, snapshot in self.state.branch_snapshots.items()
            if branch not in selected_names
        }
        if updated != self.state.branch_snapshots:
            self.replace_branch_snapshots(updated)

    @property
    def _write_transaction(self) -> RuntimeWriteTransaction:
        return cast("RuntimeWriteTransaction", self._transaction)


class RuntimeRepairModelView(RuntimeModelView):
    """Expose the narrowly-scoped model correction permitted to repair."""

    def remove_refs(self, target_dirs: Iterable[str]) -> None:
        """Remove refs whose target-dirs are selected, using repair's direct publication."""

        selected_paths = set(target_dirs)
        if not selected_paths:
            return
        self._repair_transaction.replace_refs_for_repair(
            tuple(reference for reference in self.state.refs if reference.target_dir not in selected_paths)
        )

    @property
    def _repair_transaction(self) -> RuntimeRepairTransaction:
        return cast("RuntimeRepairTransaction", self._transaction)


def _ancestor_paths(path: str) -> tuple[str, ...]:
    if path == "/":
        return ("/",)
    components = path.strip("/").split("/")
    return ("/", *(f"/{'/'.join(components[:index])}" for index in range(1, len(components) + 1)))


__all__ = ["RuntimeModelView", "RuntimeRepairModelView", "RuntimeWriteModelView"]
