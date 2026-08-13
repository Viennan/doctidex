"""Shared views over the doctidex work model and current tree links."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, cast
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from markdown_it.rules_inline.link import link as _markdown_link_rule
from markdown_it.rules_inline.state_inline import StateInline

from whero.doctidex.model import BoundaryPoint, Installation, Ref, RuntimeState, Worktree
from whero.doctidex.paths import normalize_repo_path, repo_path_to_fs

if TYPE_CHECKING:
    from whero.doctidex.store.runtime import RuntimeTransaction, RuntimeWriteTransaction


class RuntimeModelView:
    """Provide common work-model queries over one Transaction's maintained indexes."""

    def __init__(self, transaction: RuntimeTransaction) -> None:
        self._transaction = transaction

    @property
    def state(self) -> RuntimeState:
        """Return the Transaction's current complete state."""

        return self._transaction.state

    @property
    def installations(self) -> tuple[Installation, ...]:
        """Return all Installation records in stable state order."""

        return self.state.installations

    @property
    def refs(self) -> tuple[Ref, ...]:
        """Return all managed Ref records in stable state order."""

        return self.state.refs

    @property
    def worktrees(self) -> tuple[Worktree, ...]:
        """Return all Worktree records in stable state order."""

        return self.state.worktrees

    @property
    def boundary_points(self) -> tuple[BoundaryPoint, ...]:
        """Return the full custom and model-derived BoundaryPoint view."""

        return self._transaction._boundary_points

    def installation(self, install_id: str) -> Installation | None:
        """Find an Installation by its stable identifier."""

        return self._transaction._installations_by_id.get(install_id)

    def installation_at(self, install_path: str) -> Installation | None:
        """Find the Installation that owns an install-path."""

        return self._transaction._installations_by_path.get(install_path)

    def installation_for_selector(self, git_url: str, *, branch: str, tag: str) -> Installation | None:
        """Find the branch or tag Installation for one Git URL and selector."""

        return self._transaction._installations_by_source.get((git_url, branch, tag))

    def installation_for_commit(self, git_url: str, commit_hash: str) -> Installation | None:
        """Find an Installation for one Git URL and final commit hash."""

        return self._transaction._installations_by_commit.get((git_url, commit_hash))

    def ref(self, target_dir: str) -> Ref | None:
        """Find the Ref that owns a target directory."""

        return self._transaction._refs_by_target_dir.get(target_dir)

    def refs_for(self, installation: Installation) -> tuple[Ref, ...]:
        """Return every Ref associated with an Installation."""

        return self._transaction._refs_by_installation.get(installation.install_id, ())

    def worktree(self, work_path: str) -> Worktree | None:
        """Find the Worktree that owns a work path."""

        return self._transaction._worktrees_by_path.get(work_path)

    def custom_boundary_point(self, path: str) -> BoundaryPoint | None:
        """Find a custom BoundaryPoint by its path."""

        return self._transaction._custom_boundary_points_by_path.get(path)

    def boundary_point(self, path: str) -> BoundaryPoint | None:
        """Find a custom or model-derived BoundaryPoint by its exact path."""

        return self._transaction._boundary_points_by_path.get(path)

    def first_boundary(self, path: str) -> BoundaryPoint | None:
        """Return the first BoundaryPoint crossed from the repository root."""

        return self.first_boundaries((path,))[0]

    def first_boundaries(self, paths: Iterable[str]) -> tuple[BoundaryPoint | None, ...]:
        """Return the first crossed BoundaryPoint for every path in input order."""

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
        """Return the Ref represented by an import-ref BoundaryPoint."""

        if boundary is None or boundary.type != "import-ref":
            return None
        return self.ref(boundary.path)

    def installation_for_boundary(self, boundary: BoundaryPoint | None) -> Installation | None:
        """Associate import and import-ref BoundaryPoints with their Installation."""

        if boundary is None:
            return None
        if boundary.type == "import":
            return self.installation_at(boundary.path)
        reference = self.ref_for_boundary(boundary)
        return self.installation(reference.install_id) if reference is not None else None


class RuntimeWriteModelView(RuntimeModelView):
    """Provide standard work-model updates through a write Transaction."""

    @property
    def _write_transaction(self) -> RuntimeWriteTransaction:
        return cast("RuntimeWriteTransaction", self._transaction)

    def set_installation_tracking(self, installation: Installation, *, tracked: bool) -> Installation:
        """Change only an Installation's tracked projection state."""

        replacement = replace(installation, tracked=tracked)
        self.upsert_installation(replacement)
        return replacement

    def upsert_custom_boundary_points(self, points: Iterable[BoundaryPoint]) -> None:
        """Add or replace custom BoundaryPoints in one collection update."""

        replacements = {point.path: point for point in points}
        if not replacements:
            return
        updated = tuple(
            replacements.pop(current.path, current) for current in self.state.custom_boundary_points
        )
        updated = (*updated, *replacements.values())
        if updated != self.state.custom_boundary_points:
            self._write_transaction._replace_collections(custom_boundary_points=updated)

    def remove_custom_boundary_points(self, paths: Iterable[str]) -> None:
        """Remove custom BoundaryPoints in one collection update."""

        selected_paths = set(paths)
        if not selected_paths:
            return
        updated = tuple(item for item in self.state.custom_boundary_points if item.path not in selected_paths)
        if updated != self.state.custom_boundary_points:
            self._write_transaction._replace_collections(custom_boundary_points=updated)

    def upsert_installation(self, installation: Installation) -> None:
        """Add or replace an Installation by install-id."""

        installations = tuple(
            installation if item.install_id == installation.install_id else item for item in self.state.installations
        )
        if self.installation(installation.install_id) is None:
            installations = (*installations, installation)
        self._write_transaction._replace_collections(installations=installations)

    def replace_installation(self, existing: Installation, replacement: Installation) -> None:
        """Replace an Installation and retain any managed Ref relationships."""

        installations = tuple(
            replacement if item.install_id == existing.install_id else item for item in self.state.installations
        )
        refs = tuple(
            replace(item, install_id=replacement.install_id) if item.install_id == existing.install_id else item
            for item in self.state.refs
        )
        self._write_transaction._replace_collections(installations=installations, refs=refs)

    def remove_installations(self, install_ids: Iterable[str]) -> None:
        """Remove the selected Installation records without changing Ref records."""

        selected_ids = set(install_ids)
        self._write_transaction._replace_collections(
            installations=tuple(item for item in self.state.installations if item.install_id not in selected_ids)
        )

    def upsert_ref(self, reference: Ref) -> None:
        """Add or replace a Ref by target directory."""

        refs = tuple(reference if item.target_dir == reference.target_dir else item for item in self.state.refs)
        if self.ref(reference.target_dir) is None:
            refs = (*refs, reference)
        self._write_transaction._replace_collections(refs=refs)

    def remove_ref(self, target_dir: str) -> None:
        """Remove the Ref at the selected target directory."""

        self._write_transaction._replace_collections(
            refs=tuple(item for item in self.state.refs if item.target_dir != target_dir)
        )

    def upsert_worktree(self, worktree: Worktree) -> None:
        """Add or replace a Worktree by work path."""

        worktrees = tuple(worktree if item.work_path == worktree.work_path else item for item in self.state.worktrees)
        if self.worktree(worktree.work_path) is None:
            worktrees = (*worktrees, worktree)
        self._write_transaction._replace_collections(worktrees=worktrees)

    def remove_worktrees(self, work_paths: Iterable[str]) -> None:
        """Remove Worktree records by work path."""

        selected_paths = set(work_paths)
        self._write_transaction._replace_collections(
            worktrees=tuple(item for item in self.state.worktrees if item.work_path not in selected_paths)
        )


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """One local Markdown link and its work-model association."""

    path: str
    line: int
    link_path: str
    target_path: str | None
    boundary_point: BoundaryPoint | None
    installation: Installation | None
    ref: Ref | None

    def reference_details(self) -> dict[str, object]:
        """Return the common structured link location used by command diagnostics."""

        return {"path": self.path, "line": self.line, "link-path": self.link_path}


def scan_markdown_links(
    git_root: Path,
    model: RuntimeModelView,
    *,
    scope: str = "/",
) -> tuple[MarkdownLink, ...]:
    """Scan Markdown links in the current doctidex tree without entering boundaries."""

    scope = normalize_repo_path(scope, parameter="scope")
    root = repo_path_to_fs(git_root, scope)
    candidates: list[tuple[str, int, str, str | None]] = []
    boundaries = {point.path for point in model.boundary_points}

    for directory, child_directories, files in os.walk(root):
        current_path = fs_path_to_repo_path(git_root, Path(directory))
        child_directories[:] = [
            name
            for name in child_directories
            if name != ".doctidex-git" and _join_repo_path(current_path, name) not in boundaries
        ]
        for name in files:
            document = Path(directory) / name
            if not name.endswith(".md") or fs_path_to_repo_path(git_root, document) in boundaries:
                continue
            try:
                content = document.read_text()
            except OSError:
                continue
            document_path = fs_path_to_repo_path(git_root, document)
            for line, link_path in _local_link_paths(content):
                target_path = resolve_local_link(document_path, link_path)
                candidates.append((document_path, line, link_path, target_path))

    boundaries = iter(model.first_boundaries(item[3] for item in candidates if item[3] is not None))
    links: list[MarkdownLink] = []
    for document_path, line, link_path, target_path in candidates:
        boundary = next(boundaries) if target_path is not None else None
        links.append(
            MarkdownLink(
                path=document_path,
                line=line,
                link_path=link_path,
                target_path=target_path,
                boundary_point=boundary,
                installation=model.installation_for_boundary(boundary),
                ref=model.ref_for_boundary(boundary),
            )
        )
    return tuple(links)


def resolve_local_link(document_path: str, link_path: str) -> str | None:
    """Resolve a local Markdown link lexically to a repository-internal path."""

    parsed = urlsplit(link_path)
    if not parsed.path or parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    candidate = path if path.startswith("/") else _join_repo_path(_parent_path(document_path), path)
    try:
        return normalize_repo_path(candidate, parameter="link-path")
    except Exception:
        return None


def fs_path_to_repo_path(git_root: Path, path: Path) -> str:
    """Convert an in-root filesystem path to its repository-internal absolute path."""

    relative_path = path.relative_to(git_root).as_posix()
    return "/" if relative_path == "." else f"/{relative_path}"


def _ancestor_paths(path: str) -> tuple[str, ...]:
    """Return repository-internal ancestors ordered from root to ``path``."""

    if path == "/":
        return ("/",)
    components = path.strip("/").split("/")
    return ("/", *(f"/{'/'.join(components[:index])}" for index in range(1, len(components) + 1)))


def _join_repo_path(parent: str, child: str) -> str:
    return f"{parent.rstrip('/')}/{child}" if parent != "/" else f"/{child}"


def _parent_path(path: str) -> str:
    parent = path.rsplit("/", maxsplit=1)[0]
    return parent or "/"


def _local_link_paths(content: str) -> tuple[tuple[int, str], ...]:
    matches: list[tuple[int, str]] = []
    for token in _MARKDOWN.parse(content):
        if token.type != "inline" or token.map is None:
            continue
        for child in token.children or ():
            if child.type != "link_open":
                continue
            link_path = child.attrGet("href")
            if link_path is None:
                continue
            offset = child.meta.get("source-offset", 0)
            line = token.map[0] + token.content[:offset].count("\n") + 1
            matches.append((line, link_path))
    return tuple(matches)


def _link_with_source_offset(state: StateInline, silent: bool) -> bool:
    """Annotate links recognized by markdown-it with their inline source offset."""

    start = state.pos
    token_count = len(state.tokens)
    matched = _markdown_link_rule(state, silent)
    if matched and not silent:
        for token in state.tokens[token_count:]:
            if token.type == "link_open":
                token.meta["source-offset"] = start
    return matched


_MARKDOWN = MarkdownIt("commonmark")
_MARKDOWN.inline.ruler.at("link", _link_with_source_offset)
