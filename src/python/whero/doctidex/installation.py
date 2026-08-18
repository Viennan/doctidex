"""Installation-context detection and owner routing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whero.doctidex.errors import CommandFailure
from whero.doctidex.paths import fs_path_to_repo_path


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


__all__ = ["InstallationContext", "resolve_installation_context"]
