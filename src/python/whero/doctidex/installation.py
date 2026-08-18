"""Installation-context detection, owner routing, and RuntimeStore variant."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import BoundaryPoint, Installation, ModelFormatError, Ref, RuntimeState, Worktree
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
        if not self.owner_store.workspace_path.is_dir():
            raise CommandFailure(
                code="work-model.uninitialized",
                summary="The Installation owner has not been initialized.",
                subject={"kind": "workspace", "path": "/.doctidex-git"},
                details={"required-command": "init", "owner-path": str(context.owner_root)},
            )

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

    def diagnostic_transaction(self):
        return self.owner_store.diagnostic_transaction()

    def write_transaction(self):
        raise CommandFailure(
            code="installation.context.unavailable",
            summary="Write transactions are not yet available inside an import Installation.",
            subject={"kind": "installation", "install-path": self.context.install_path},
            details={"owner-path": str(self.context.owner_root), "next-phase": "4"},
        )

    def read_state(self) -> RuntimeState:
        return self.owner_store.read_state()


@dataclass(frozen=True, slots=True)
class _LocalDeclarations:
    installations: tuple[Installation, ...]
    refs: tuple[Ref, ...]


class InstallationReadOnlyTransaction:
    """Read-only transaction exposing an Installation-scoped RuntimeModelView."""

    def __init__(self, store: InstallationRuntimeStore) -> None:
        self.store = store
        self.state = RuntimeState.empty()
        self._owner_transaction = None
        self._installations_by_id: dict[str, Installation] = {}
        self._installations_by_path: dict[str, Installation] = {}
        self._installations_by_source: dict[tuple[str, str, str], Installation] = {}
        self._installations_by_commit: dict[tuple[str, str], Installation] = {}
        self._refs_by_target_dir: dict[str, Ref] = {}
        self._refs_by_installation: dict[str, tuple[Ref, ...]] = {}
        self._worktrees_by_path: dict[str, Worktree] = {}
        self._custom_boundary_points_by_path: dict[str, BoundaryPoint] = {}
        self._boundary_points: tuple[BoundaryPoint, ...] = ()
        self._boundary_points_by_path: dict[str, BoundaryPoint] = {}

    def __enter__(self) -> Self:
        owner_transaction = self.store.owner_store.read_only_transaction()
        owner_transaction.__enter__()
        self._owner_transaction = owner_transaction
        try:
            owner_state = owner_transaction.state
            self._set_state(self._scoped_state(owner_state))
        except Exception:
            owner_transaction.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        assert self._owner_transaction is not None
        return self._owner_transaction.__exit__(exc_type, exc, traceback)

    def model_view(self):
        """Return the current Installation-scoped RuntimeModelView."""

        from whero.doctidex.store.model_view import RuntimeModelView

        return RuntimeModelView(self)

    def _scoped_state(self, owner_state: RuntimeState) -> RuntimeState:
        parent = next(
            (
                item
                for item in owner_state.installations
                if item.install_path == self.store.context.install_path
            ),
            None,
        )
        if parent is None:
            raise CommandFailure(
                code="installation.context.unavailable",
                summary="The requested Installation is not recorded in its owner work model.",
                subject={"kind": "installation", "install-path": self.store.context.install_path},
                details={"owner-path": str(self.store.context.owner_root), "reason": "installation-not-found"},
            )

        local = _read_local_declarations(self.store.context)
        owner_by_commit = {(item.git_url, item.commit_hash): item for item in owner_state.installations}
        matched: dict[str, Installation] = {}
        local_ids: dict[str, Installation] = {}
        local_paths: dict[str, Installation] = {}
        for declaration in local.installations:
            owner_installation = owner_by_commit.get((declaration.git_url, declaration.commit_hash))
            if owner_installation is None:
                continue
            matched[owner_installation.install_id] = owner_installation
            local_ids[declaration.install_id] = owner_installation
            local_paths[declaration.install_path] = owner_installation

        installations = tuple(matched.values())
        refs = tuple(ref for ref in owner_state.refs if ref.install_id in matched)
        state = RuntimeState(
            custom_boundary_points=(),
            installations=installations,
            refs=refs,
            worktrees=(),
        )
        self._local_ids = local_ids
        self._local_paths = local_paths
        self._owner_boundary_points = owner_state.boundary_points
        self._set_state(state)
        return state

    def _set_state(self, state: RuntimeState) -> None:
        self.state = state
        self._reindex()

    def _reindex(self) -> None:
        self._installations_by_id = {item.install_id: item for item in self.state.installations}
        self._installations_by_id.update(getattr(self, "_local_ids", {}))
        self._installations_by_path = {item.install_path: item for item in self.state.installations}
        self._installations_by_path.update(getattr(self, "_local_paths", {}))
        self._installations_by_source = {}
        self._installations_by_commit = {}
        for item in self.state.installations:
            if item.branch or item.tag:
                self._installations_by_source.setdefault((item.git_url, item.branch, item.tag), item)
            self._installations_by_commit.setdefault((item.git_url, item.commit_hash), item)
        self._refs_by_target_dir = {item.target_dir: item for item in self.state.refs}
        refs_by_installation: dict[str, list[Ref]] = {}
        for reference in self.state.refs:
            refs_by_installation.setdefault(reference.install_id, []).append(reference)
        self._refs_by_installation = {
            install_id: tuple(references) for install_id, references in refs_by_installation.items()
        }
        self._worktrees_by_path = {}
        self._custom_boundary_points_by_path = {}
        self._boundary_points = tuple(self._owner_boundary_points)
        self._boundary_points_by_path = {}
        for point in self._owner_boundary_points:
            local_key = _local_boundary_key(self.store.context.install_path, point.path)
            if local_key is not None:
                self._boundary_points_by_path.setdefault(local_key, point)


def _read_local_declarations(context: InstallationContext) -> _LocalDeclarations:
    root = repo_path_to_fs(context.owner_root, context.install_path)
    workspace = root / ".doctidex-git"
    imports_path = workspace / "imports.json"
    refs_path = workspace / "import-refs.json"
    try:
        imports = json.loads(imports_path.read_text()) if imports_path.is_file() else []
        refs = json.loads(refs_path.read_text()) if refs_path.is_file() else []
    except (OSError, json.JSONDecodeError) as exc:
        raise _local_declaration_error(context) from exc
    if not isinstance(imports, list) or not isinstance(refs, list):
        raise _local_declaration_error(context)
    try:
        installations = tuple(Installation.from_json(item, artifact="imports.json") for item in imports)
        references = tuple(Ref.from_json(item, artifact="import-refs.json") for item in refs)
    except ModelFormatError as exc:
        raise _local_declaration_error(context) from exc
    return _LocalDeclarations(installations=installations, refs=references)


def _local_declaration_error(context: InstallationContext) -> CommandFailure:
    return CommandFailure(
        code="installation.context.unavailable",
        summary="The Installation work model declarations cannot be read.",
        subject={"kind": "installation", "install-path": context.install_path},
        details={"owner-path": str(context.owner_root), "reason": "declarations-invalid"},
    )


def _local_boundary_key(install_path: str, owner_path: str) -> str | None:
    if install_path == "/":
        return owner_path
    if owner_path == install_path:
        return "/"
    prefix = f"{install_path.rstrip('/')}/"
    if owner_path.startswith(prefix):
        return f"/{owner_path[len(prefix):]}"
    return None


__all__ = ["InstallationContext", "InstallationRuntimeStore", "resolve_installation_context"]
