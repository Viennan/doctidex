"""Structured request, plan, result, and source identity types for Views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .git import GitRemote


@dataclass(frozen=True)
class GitSource:
    commit: str
    root: Path
    wiki_path: PurePosixPath
    remote: GitRemote | None = None


@dataclass(frozen=True)
class GitTreeNode:
    kind: str
    identity: str = ""


@dataclass(frozen=True)
class SourceChange:
    kind: str
    path: PurePosixPath


@dataclass(frozen=True)
class ExistingStatus:
    previous_source: Path | None
    source_moved: bool
    git_notice: str | None = None
    requested_selections: tuple[PurePosixPath, ...] = ()
    effective_roots: tuple[PurePosixPath, ...] = ()


@dataclass(frozen=True)
class ViewRequest:
    source: Path | None
    target: Path
    view_name: str | None
    includes: tuple[str, ...]
    include_files: tuple[Path, ...]
    collapse_threshold: float
    dry_run: bool = False
    allow_path_relocation: bool = False


@dataclass(frozen=True)
class ViewPlan:
    request: ViewRequest
    source: Path
    output_root: Path
    git_source: GitSource | None
    status: ExistingStatus
    relocated_source: Path | None
    requested_selections: tuple[PurePosixPath, ...]
    selections: tuple[PurePosixPath, ...]
    notices: tuple[str, ...]
    relink_plan: tuple[str, ...]
    link_plan: tuple[str, ...]


@dataclass(frozen=True)
class OperationResult:
    messages: tuple[str, ...]
    mutated: bool = False
