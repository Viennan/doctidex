from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit, urlunsplit

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.document import DoctidexDocument, markdown_links
from whero.doctidex.protocol.mounts import MountDeclaration, read_mounts
from whero.doctidex.protocol.paths import validate_mount_path
from whero.doctidex.protocol.tree import RootContext

from .context import root_gitignore_status
from .projection import build_projection, present_projection, remove_presentation
from .repository import RevisionSelector, SourceRepository
from .state import StateStore, file_lock

_T = TypeVar("_T")


def _serialized(method: Callable[..., _T]) -> Callable[..., _T]:
    @wraps(method)
    def locked(self: GitMountService, *args: Any, **kwargs: Any) -> _T:
        with file_lock(self.store.directory / "mount-operation.lock"):
            return method(self, *args, **kwargs)

    return locked


@dataclass(frozen=True, slots=True)
class GitMount:
    declaration: MountDeclaration
    selector: RevisionSelector

    @property
    def mount_path(self) -> str:
        return self.declaration.mount_path

    @property
    def url(self) -> str:
        return self.declaration.url


class GitMountService:
    def __init__(self, context: RootContext) -> None:
        self.context = context
        self.root = context.root
        self.store = StateStore(self.root)

    def list(self) -> list[dict[str, Any]]:
        state = self.store.read()
        results: list[dict[str, Any]] = []
        for mount in self.mounts():
            saved = _matching_state(state, mount)
            effective = saved.get("effective_commit") if saved else None
            destination = self.root.joinpath(*mount.mount_path.lstrip("/").split("/"))
            ready = bool(effective and (destination.exists() or destination.is_symlink()))
            results.append(
                {
                    "mount_path": mount.mount_path,
                    "source": public_url(mount.url),
                    "declared_revision": mount.selector.as_dict(),
                    "effective_commit": effective,
                    "state": "ready" if ready else "not_prepared",
                    "readable": ready,
                    "next_action": None if ready else f"doctidex-git mount prepare {mount.mount_path}",
                }
            )
        return results

    def mounts(self) -> list[GitMount]:
        mounts = []
        for declaration in read_mounts(self.context.index):
            if declaration.type != "git":
                continue
            _validate_url(declaration.url)
            mounts.append(GitMount(declaration, _selector(declaration)))
        return mounts

    @_serialized
    def add(
        self,
        *,
        url: str,
        selector: RevisionSelector,
        mount_path: str,
        apply: bool,
    ) -> dict[str, Any]:
        mount_path = validate_mount_path(mount_path)
        _validate_url(url)
        existing = self.mounts()
        for mount in existing:
            if (
                mount.mount_path == mount_path
                or mount.mount_path.startswith(mount_path + "/")
                or mount_path.startswith(mount.mount_path + "/")
            ):
                raise DoctidexError(
                    f"Mount path overlaps an existing declaration: {mount.mount_path}",
                    operation="mount_add",
                    affected=[mount_path, mount.mount_path],
                    actions=["Choose a non-overlapping mount path."],
                    code="mount_paths_overlap",
                )
        readiness = root_gitignore_status(self.root)
        if readiness["status"] != "ready":
            raise _readiness_error("mount_add", self.root, readiness)
        plan = {
            "status": "ok",
            "operation": "mount_add",
            "root": str(self.root),
            "mount_path": mount_path,
            "source": public_url(url),
            "declared_revision": selector.as_dict(),
            "network": False,
            "changed": [str(self.context.index.path)] if apply else [],
            "result": "Mount declaration added." if apply else "Mount declaration is valid and can be added.",
            "mount_state": "not_prepared",
        }
        if not apply:
            return plan
        document = DoctidexDocument.load(self.context.index.path)
        doctidex = document.doctidex
        if doctidex is None or not document.is_root:
            raise DoctidexError(
                "Git mounts can only be added to a root index.md.",
                operation="mount_add",
                affected=[str(document.path)],
                actions=["Select a doctidex root and retry."],
                code="mount_root_required",
            )
        raw_mounts = doctidex.get("mounts")
        if raw_mounts is None:
            raw_mounts = CommentedSeq()
            doctidex["mounts"] = raw_mounts
        if not isinstance(raw_mounts, list):
            raise DoctidexError(
                "doctidex.mounts must be a list before a mount can be added.",
                operation="mount_add",
                affected=[str(document.path)],
                actions=["Correct doctidex.mounts and retry."],
                code="mounts_not_list",
            )
        revision = CommentedMap()
        revision[selector.kind] = selector.value
        raw = CommentedMap()
        raw["type"] = "git"
        raw["url"] = url
        raw["revision"] = revision
        raw["mount_path"] = mount_path
        raw_mounts.append(raw)
        document.write()
        return plan

    @_serialized
    def remove(self, mount_path: str, *, apply: bool) -> dict[str, Any]:
        mount = self._require_mount(mount_path)
        references = self._references_to(mount.mount_path)
        if references:
            raise DoctidexError(
                f"Documents still reference {mount.mount_path}.",
                operation="mount_remove",
                affected=references,
                actions=["Update the references, then retry the mount removal."],
                requires_user="external_references",
                code="mount_still_referenced",
            )
        result = {
            "status": "ok",
            "operation": "mount_remove",
            "root": str(self.root),
            "mount_path": mount.mount_path,
            "changed": [str(self.context.index.path)] if apply else [],
            "result": "Mount declaration removed."
            if apply
            else "Mount can be removed without leaving parsed references.",
        }
        if not apply:
            return result
        document = DoctidexDocument.load(self.context.index.path)
        doctidex = document.doctidex or {}
        raw_mounts = doctidex.get("mounts", [])
        raw_mounts.remove(mount.declaration.raw)
        document.write()
        state = self.store.read()
        managed = mount.mount_path in state.get("mounts", {})
        remove_presentation(self.root, mount.mount_path, managed=managed)
        self.store.update(lambda data: data["mounts"].pop(mount.mount_path, None))
        return result

    @_serialized
    def prepare(self, mount_path: str) -> dict[str, Any]:
        mount = self._require_mount(mount_path)
        readiness = root_gitignore_status(self.root)
        if readiness["status"] != "ready":
            raise _readiness_error("mount_prepare", self.root, readiness)
        state = self.store.read()
        saved = _matching_state(state, mount)
        repository = SourceRepository(mount.url)
        effective = saved.get("effective_commit") if saved else None
        if not effective:
            effective = repository.resolve(mount.selector, refresh=False)
        view = repository.revision_view(effective)
        _validate_source_root(view, mount)
        projection = build_projection(self.root, mount.mount_path, view, effective)
        present_projection(self.root, mount.mount_path, projection, replace_managed=bool(saved))
        self._save_effective(mount, effective)
        return _mount_result("mount_prepare", self.root, mount, effective, "ready", True)

    @_serialized
    def sync(self, mount_path: str, *, apply: bool) -> dict[str, Any]:
        mount = self._require_mount(mount_path)
        state = self.store.read()
        saved = _matching_state(state, mount)
        old = saved.get("effective_commit") if saved else None
        repository = SourceRepository(mount.url)
        try:
            new = old if mount.selector.kind == "commit" and old else repository.resolve(mount.selector, refresh=True)
        except DoctidexError as exc:
            exc.affected = [mount.mount_path]
            if old:
                exc.result = f"Effective commit {old} remains readable."
            raise
        result = {
            "status": "ok",
            "operation": "mount_sync",
            "root": str(self.root),
            "mount_path": mount.mount_path,
            "source": public_url(mount.url),
            "declared_revision": mount.selector.as_dict(),
            "old_effective_commit": old,
            "new_effective_commit": new,
            "changed": old != new,
            "applied": apply,
            "result": "Mount is already current."
            if old == new
            else ("Mount synchronized." if apply else "A new effective commit is available."),
        }
        if not apply or old == new:
            return result
        readiness = root_gitignore_status(self.root)
        if readiness["status"] != "ready":
            raise _readiness_error("mount_sync", self.root, readiness)
        view = repository.revision_view(new)
        _validate_source_root(view, mount)
        projection = build_projection(self.root, mount.mount_path, view, new)
        present_projection(self.root, mount.mount_path, projection, replace_managed=bool(saved))
        self._save_effective(mount, new)
        return result

    def effective(self, mount_path: str) -> tuple[GitMount, str | None]:
        mount = self._require_mount(mount_path)
        state = self.store.read()
        saved = _matching_state(state, mount)
        return mount, saved.get("effective_commit") if saved else None

    def _require_mount(self, mount_path: str) -> GitMount:
        normalized = validate_mount_path(mount_path)
        matches = [mount for mount in self.mounts() if mount.mount_path == normalized]
        if not matches:
            raise DoctidexError(
                f"No Git mount is declared at {normalized}.",
                operation="mount",
                affected=[normalized],
                actions=["List mounts or add the declaration at the root index.md."],
                code="mount_not_declared",
            )
        return matches[0]

    def _save_effective(self, mount: GitMount, commit: str) -> None:
        def update(data: dict[str, Any]) -> None:
            data["mounts"][mount.mount_path] = {
                "url": mount.url,
                "selector": mount.selector.as_dict(),
                "effective_commit": commit,
                "presentation": "managed",
            }

        self.store.update(update)

    def _references_to(self, mount_path: str) -> list[str]:
        references: list[str] = []
        pattern = re.compile(re.escape(mount_path) + r"(?:/|\b)")
        for path in self.root.rglob("*.md"):
            if ".doctidex/mounts" in path.as_posix():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if any(pattern.search(link.target) for link in markdown_links(content)):
                references.append(str(path))
        return references


def _selector(declaration: MountDeclaration) -> RevisionSelector:
    raw = declaration.raw
    if "src_path" in raw:
        raise DoctidexError(
            "Git mount declarations do not support src_path.",
            operation="validate_mount",
            affected=[declaration.mount_path],
            actions=["Remove src_path and use a URL whose checkout root is the complete source tree."],
            code="git_mount_src_path",
        )
    revision = raw.get("revision")
    if not isinstance(revision, dict) or len(revision) != 1:
        raise DoctidexError(
            "Git mount revision must contain exactly one commit, tag, or branch.",
            operation="validate_mount",
            affected=[declaration.mount_path],
            actions=["Set revision to one non-empty commit, tag, or branch value."],
            code="git_mount_revision",
        )
    kind, value = next(iter(revision.items()))
    if kind not in {"commit", "tag", "branch"} or not isinstance(value, str) or not value:
        raise DoctidexError(
            "Git mount revision must contain exactly one non-empty commit, tag, or branch string.",
            operation="validate_mount",
            affected=[declaration.mount_path],
            actions=["Correct the revision mapping and retry."],
            code="git_mount_revision",
        )
    return RevisionSelector(kind, value)


def _matching_state(state: dict[str, Any], mount: GitMount) -> dict[str, Any] | None:
    saved = state.get("mounts", {}).get(mount.mount_path)
    if not isinstance(saved, dict):
        return None
    if saved.get("url") != mount.url or saved.get("selector") != mount.selector.as_dict():
        return None
    return saved


def _validate_source_root(view: Path, mount: GitMount) -> None:
    index = view / "index.md"
    if not index.is_file():
        raise DoctidexError(
            "The Git checkout root does not contain a doctidex root index.md.",
            operation="mount_prepare",
            affected=[mount.mount_path],
            actions=["Use a Git URL whose checkout root is the complete doctidex source tree."],
            requires_user="source_url",
            code="source_root_missing",
        )
    if not DoctidexDocument.load(index).is_root:
        raise DoctidexError(
            "The Git checkout index.md is not a doctidex root.",
            operation="mount_prepare",
            affected=[mount.mount_path],
            actions=["Correct the source root or choose a different Git URL."],
            requires_user="source_url",
            code="source_root_invalid",
        )


def _readiness_error(operation: str, root: Path, readiness: dict[str, Any]) -> DoctidexError:
    actions = []
    if not readiness.get("ignored"):
        actions.append(f"Add /.doctidex/mounts/ to {root / '.gitignore'}.")
    if readiness.get("tracked"):
        actions.append(
            "Ask the user how to remove tracked mount content from the Git index without deleting working files."
        )
    return DoctidexError(
        "The mount path is not ready for safe Git-backed presentation.",
        operation=operation,
        affected=[str(root / ".doctidex" / "mounts")],
        actions=actions or ["Correct the Git ignore state and retry."],
        requires_user="git_index" if readiness.get("tracked") else None,
        code="plugin_not_ready",
        details={
            "ignored_by_root_gitignore": readiness.get("ignored"),
            "tracked_count": len(readiness.get("tracked", [])),
        },
    )


def _mount_result(
    operation: str, root: Path, mount: GitMount, commit: str | None, state: str, readable: bool
) -> dict[str, Any]:
    return {
        "status": "ok",
        "operation": operation,
        "root": str(root),
        "mount_path": mount.mount_path,
        "source": public_url(mount.url),
        "declared_revision": mount.selector.as_dict(),
        "effective_commit": commit,
        "mount_state": state,
        "readable": readable,
        "changed": [],
        "result": "The external directory tree is readable." if readable else "The mount remains lazily unprepared.",
    }


def _validate_url(url: str) -> None:
    if not url.strip() or "\n" in url or "\r" in url:
        raise DoctidexError(
            "Git URL must be a non-empty single-line string.",
            operation="mount_add",
            actions=["Provide the Git repository URL or local repository path."],
            code="git_url_invalid",
        )
    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and (parsed.username is not None or parsed.password is not None):
        raise DoctidexError(
            "Git URL must not contain embedded credentials.",
            operation="validate_mount",
            actions=["Remove credentials from the URL and use the configured Git credential provider."],
            requires_user="repository_access",
            code="git_url_credentials",
        )


def public_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or "@" not in parsed.netloc:
        return url
    host = parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
