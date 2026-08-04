from __future__ import annotations

import os
import shlex
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.root import RootContext, root_at
from whero.doctidex.results import envelope, finding

from .runner import git
from .source import canonical_source, make_logically_read_only, make_logically_writable, move_detached_worktree
from .storage import RootStorage, directory_lock, source_mutation


class HookService:
    """Own the root-scoped post-checkout entrypoint and offline reconciliation."""

    def __init__(self, context: RootContext) -> None:
        self.context = context
        self.root = context.root
        self.storage = RootStorage(self.root)
        self.host_repository = _host_repository(self.root)

    def install(self) -> dict[str, Any]:
        hook_path = self._hook_path()
        script = _hook_script(self.root)
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = hook_path.parent / ".doctidex-git-post-checkout.lock"
        with directory_lock(lock_path, operation="hook_install"):
            if hook_path.exists() or hook_path.is_symlink():
                if hook_path.is_file() and not hook_path.is_symlink() and _is_managed_hook(
                    hook_path.read_text(encoding="utf-8"), self.root
                ):
                    if hook_path.stat().st_mode & 0o111:
                        if hook_path.read_text(encoding="utf-8") == script:
                            return self._install_result(hook_path, "unchanged")
                else:
                    raise DoctidexError(
                        "The host repository already has a post-checkout hook not managed by doctidex-git.",
                        operation="hook_install",
                        affected=[str(hook_path)],
                        actions=["Preserve the existing hook or remove it with explicit authority before retrying."],
                        code="hook_occupied",
                        domain="external",
                        path=str(hook_path),
                        fields={"host_repository": str(self.host_repository), "hook_path": str(hook_path)},
                    )
            _write_executable(hook_path, script)
        return self._install_result(hook_path, "installed")

    def run(self) -> dict[str, Any]:
        try:
            manifest = self.storage.read_manifest()
            runtime = self.storage.read_runtime()
        except DoctidexError as exc:
            raise _hook_state_error(exc) from exc
        items: dict[str, dict[str, Any]] = {}
        changed: list[Path] = []
        aligned_direct: set[str] = set()

        direct_ids = sorted(
            set(manifest["installs"])
            | {
                identifier
                for identifier, record in runtime["installs"].items()
                if record["role"] == "direct"
            }
        )
        for identifier in direct_ids:
            record = runtime["installs"].get(identifier)
            portable = manifest["installs"].get(identifier)
            if not isinstance(record, dict):
                items[identifier] = _item(
                    identifier,
                    "direct",
                    "ignored",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "info",
                        "direct_runtime_missing",
                        "The current manifest entry has no managed direct runtime record.",
                    ),
                )
                continue
            if not isinstance(portable, dict):
                items[identifier] = _item(
                    identifier,
                    "direct",
                    "ignored",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "info",
                        "direct_manifest_missing",
                        "The installed direct entry is not declared by the current manifest.",
                    ),
                )
                continue
            if record["role"] != "direct":
                items[identifier] = _item(
                    identifier,
                    record["role"],
                    "ignored",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "warning",
                        "direct_role_mismatch",
                        "The manifest entry does not have a direct runtime record.",
                    ),
                )
                continue
            if not self._path(record).exists():
                items[identifier] = _item(
                    identifier,
                    "direct",
                    "ignored",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "info",
                        "direct_payload_missing",
                        "The current manifest declares a direct install whose payload is not installed.",
                    ),
                )
                continue
            item, item_changed = self._align(identifier, portable, expected_role="direct")
            items[identifier] = item
            changed.extend(item_changed)
            if item["state"] in {"aligned", "unchanged"} and item["revision_alignment"] == "complete":
                aligned_direct.add(identifier)

        expanded: set[str] = set()
        for identifier in sorted(aligned_direct):
            self._walk_dependencies(identifier, items, changed, expanded, set())

        runtime = self.storage.read_runtime()
        for identifier, record in sorted(runtime["installs"].items()):
            if record["role"] != "dependency" or identifier in items:
                continue
            if record["managed_state"] == "hidden":
                items[identifier] = _item(
                    identifier,
                    "dependency",
                    "hidden",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "info",
                        "hidden_rechecked",
                        "The hidden dependency has no aligned direct ancestor in this checkout.",
                    ),
                )
            else:
                items[identifier] = _item(
                    identifier,
                    "dependency",
                    "ignored",
                    None,
                    "not_applicable",
                    finding(
                        "external",
                        "info",
                        "dependency_ancestor_unavailable",
                        "The dependency has no aligned direct ancestor in this checkout.",
                    ),
                )

        result_items = [items[identifier] for identifier in sorted(items)]
        counts = Counter(item["state"] for item in result_items)
        warning = any(
            item["state"] == "blocked" or item["revision_alignment"] == "metadata_warning"
            for item in result_items
        )
        return envelope(
            "hook_run",
            status="warning" if warning else "ok",
            result=(
                "Checkout reconciliation completed with preserved items."
                if warning
                else "Checkout reconciliation completed."
            ),
            root=str(self.root),
            changed=[str(path) for path in _unique_paths(changed)],
            host_repository=str(self.host_repository),
            items=result_items,
            counts={
                state: counts.get(state, 0)
                for state in ("aligned", "unchanged", "ignored", "hidden", "unhidden", "blocked")
            },
        )

    def _install_result(self, hook_path: Path, state: str) -> dict[str, Any]:
        return envelope(
            "hook_install",
            result=(
                "The post-checkout hook was installed."
                if state == "installed"
                else "The post-checkout hook is already installed."
            ),
            root=str(self.root),
            changed=[str(hook_path)] if state == "installed" else [],
            host_repository=str(self.host_repository),
            hook_path=str(hook_path),
            state=state,
        )

    def _hook_path(self) -> Path:
        result = git(
            ["-C", str(self.root), "rev-parse", "--path-format=absolute", "--git-path", "hooks/post-checkout"],
            operation="hook_install",
            check=False,
        )
        if result.returncode != 0:
            raise DoctidexError(
                "The selected doctidex root is not inside a Git working tree.",
                operation="hook_install",
                affected=[str(self.root)],
                actions=["Select a doctidex root inside one Git working tree."],
                code="host_git_not_found",
                domain="external",
            )
        return Path(result.stdout.strip()).absolute()

    def _walk_dependencies(
        self,
        parent_id: str,
        items: dict[str, dict[str, Any]],
        changed: list[Path],
        expanded: set[str],
        active: set[str],
    ) -> None:
        if parent_id in expanded or parent_id in active:
            return
        runtime = self.storage.read_runtime()
        parent = runtime["installs"].get(parent_id)
        if not isinstance(parent, dict) or parent["managed_state"] != "complete":
            return
        expanded.add(parent_id)
        active = {*active, parent_id}
        children = sorted(
            identifier
            for identifier, record in runtime["installs"].items()
            if record["role"] == "dependency" and parent_id in record["parents"]
        )
        for identifier in children:
            if identifier in active:
                continue
            runtime = self.storage.read_runtime()
            child = runtime["installs"].get(identifier)
            if not isinstance(child, dict):
                continue
            portable = self._child_metadata(parent, child)
            if portable is None:
                self._hide_subtree(identifier, items, changed, set())
                continue
            item, item_changed = self._align(identifier, portable, expected_role="dependency")
            items[identifier] = item
            changed.extend(item_changed)
            if item["state"] in {"aligned", "unchanged", "unhidden"} and item["revision_alignment"] == "complete":
                self._walk_dependencies(identifier, items, changed, expanded, active)

    def _hide_subtree(
        self,
        identifier: str,
        items: dict[str, dict[str, Any]],
        changed: list[Path],
        active: set[str],
    ) -> None:
        if identifier in active:
            return
        runtime = self.storage.read_runtime()
        record = runtime["installs"].get(identifier)
        if not isinstance(record, dict) or record["role"] != "dependency":
            return
        item, item_changed = self._hide(identifier)
        items[identifier] = item
        changed.extend(item_changed)
        active = {*active, identifier}
        for child_id, child in sorted(self.storage.read_runtime()["installs"].items()):
            if child["role"] == "dependency" and identifier in child["parents"]:
                self._hide_subtree(child_id, items, changed, active)

    def _child_metadata(self, parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any] | None:
        path = self._path(parent)
        content_context = root_at(path)
        if content_context is None:
            return None
        try:
            manifest = RootStorage(content_context.root).read_manifest(required=True)
        except DoctidexError:
            return None
        candidates = [
            record
            for record in manifest["installs"].values()
            if canonical_source(record["source_url"], cwd=content_context.root) == child["canonical_source"]
        ]
        matching_selector = [
            record for record in candidates if record["revision_selector"] == child["revision_selector"]
        ]
        if len(matching_selector) == 1:
            return matching_selector[0]
        return candidates[0] if len(candidates) == 1 else None

    def _align(
        self,
        identifier: str,
        portable: dict[str, Any],
        *,
        expected_role: str,
    ) -> tuple[dict[str, Any], list[Path]]:
        runtime = self.storage.read_runtime()
        initial = runtime["installs"].get(identifier)
        if not isinstance(initial, dict) or initial["role"] != expected_role:
            return (
                _item(
                    identifier,
                    expected_role,
                    "blocked",
                    portable.get("resolved_commit"),
                    "not_applicable",
                    finding(
                        "external",
                        "error",
                        "mapping_damaged",
                        "The dependency runtime record changed before checkout reconciliation.",
                    ),
                ),
                [],
            )
        canonical = initial["canonical_source"]
        try:
            with source_mutation(canonical, operation="hook_run"):
                with self.storage.mutation():
                    runtime = self.storage.read_runtime()
                    record = runtime["installs"].get(identifier)
                    if not isinstance(record, dict) or record["role"] != expected_role:
                        raise _reconciliation_error(
                            "mapping_damaged", "The managed install record changed during reconciliation."
                        )
                    if expected_role == "direct":
                        current = self.storage.read_manifest()["installs"].get(identifier)
                        if current != portable:
                            raise _reconciliation_error(
                                "index_update_conflict", "The current recovery manifest changed during reconciliation."
                            )
                    path = self._path(record)
                    if not path.exists():
                        return (
                            _item(
                                identifier,
                                expected_role,
                                "ignored",
                                None,
                                "not_applicable",
                                finding(
                                    "external",
                                    "info",
                                    "payload_missing",
                                    "The managed payload is absent and was not recreated by the hook.",
                                ),
                            ),
                            [],
                        )
                    payload_changed = _checkout_exact(path, portable["resolved_commit"])
                    was_hidden = record["managed_state"] == "hidden"
                    normal_path = self.storage.install_directory / identifier
                    moved = False
                    if was_hidden:
                        if normal_path.exists():
                            raise _reconciliation_error(
                                "install_path_conflict",
                                "The normal install path is occupied while the dependency is hidden.",
                            )
                        move_detached_worktree(path, normal_path, operation="hook_run")
                        path = normal_path
                        moved = True
                    expected = _runtime_from_portable(record, portable, state="complete")
                    runtime_changed = record != expected
                    if runtime_changed:
                        self.storage.update_runtime(
                            lambda value: value["installs"].__setitem__(identifier, expected)
                        )
                    state = "unhidden" if was_hidden else (
                        "aligned" if payload_changed or runtime_changed else "unchanged"
                    )
                    changed = [self.storage.runtime_path] if runtime_changed else []
                    if payload_changed or moved:
                        changed.insert(0, path)
                    return _item(identifier, expected_role, state, portable["resolved_commit"], "complete"), changed
        except DoctidexError as exc:
            return (
                _item(
                    identifier,
                    expected_role,
                    "blocked",
                    portable.get("resolved_commit"),
                    "not_applicable",
                    _finding_from_error(exc),
                ),
                [],
            )

    def _hide(self, identifier: str) -> tuple[dict[str, Any], list[Path]]:
        runtime = self.storage.read_runtime()
        initial = runtime["installs"].get(identifier)
        if not isinstance(initial, dict) or initial["role"] != "dependency":
            return (
                _item(
                    identifier,
                    "dependency",
                    "blocked",
                    None,
                    "not_applicable",
                    finding("external", "error", "mapping_damaged", "The dependency record cannot be hidden safely."),
                ),
                [],
            )
        try:
            with source_mutation(initial["canonical_source"], operation="hook_run"):
                with self.storage.mutation():
                    runtime = self.storage.read_runtime()
                    record = runtime["installs"].get(identifier)
                    if not isinstance(record, dict) or record["role"] != "dependency":
                        raise _reconciliation_error(
                            "mapping_damaged", "The managed dependency changed during reconciliation."
                        )
                    if record["managed_state"] == "hidden":
                        return _item(identifier, "dependency", "hidden", None, "not_applicable"), []
                    path = self._path(record)
                    hidden_path = self.storage.hidden_directory / identifier
                    changed: list[Path] = []
                    if path.exists():
                        if hidden_path.exists():
                            raise _reconciliation_error(
                                "install_path_conflict",
                                "The hidden install path is already occupied by different content.",
                            )
                        move_detached_worktree(path, hidden_path, operation="hook_run")
                        changed.append(hidden_path)
                    hidden = {
                        **record,
                        "install_path": f"/.doctidex/git/installs/.hidden/{identifier}",
                        "managed_state": "hidden",
                    }
                    self.storage.update_runtime(
                        lambda value: value["installs"].__setitem__(identifier, hidden)
                    )
                    changed.append(self.storage.runtime_path)
                    return _item(identifier, "dependency", "hidden", None, "not_applicable"), changed
        except DoctidexError as exc:
            return _item(identifier, "dependency", "blocked", None, "not_applicable", _finding_from_error(exc)), []

    def _path(self, record: dict[str, Any]) -> Path:
        return self.root.joinpath(*record["install_path"].lstrip("/").split("/"))


def _host_repository(root: Path) -> Path:
    result = git(["-C", str(root), "rev-parse", "--show-toplevel"], operation="hook_run", check=False)
    if result.returncode != 0:
        raise DoctidexError(
            "The selected root is not inside a Git working tree.",
            operation="hook_run",
            affected=[str(root)],
            actions=["Select a doctidex root inside one Git working tree."],
            code="host_git_not_found",
            domain="external",
        )
    return Path(result.stdout.strip()).absolute()


_HOOK_HEADER = "#!/bin/sh\n# doctidex-git managed post-checkout hook\n"


def _hook_script(root: Path) -> str:
    command = f"exec {shlex.quote(str(_runtime_executable()))} hook --run --root {shlex.quote(str(root))}"
    return f"{_HOOK_HEADER}{command}\n"


def _runtime_executable() -> Path:
    directory = Path(sys.executable).absolute().parent
    name = "doctidex-git.exe" if os.name == "nt" else "doctidex-git"
    return directory / name


def _is_managed_hook(content: str, root: Path) -> bool:
    lines = content.splitlines()
    suffix = f" hook --run --root {shlex.quote(str(root))}"
    return (
        len(lines) == 3
        and lines[:2] == _HOOK_HEADER.splitlines()
        and lines[2].startswith("exec ")
        and lines[2].endswith(suffix)
    )


def _write_executable(path: Path, content: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".post-checkout.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o755)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _checkout_exact(path: Path, commit: str) -> bool:
    head = git(["-C", str(path), "rev-parse", "HEAD"], operation="hook_run", check=False)
    if head.returncode != 0:
        raise _reconciliation_error("install_damaged", "The managed payload is not a readable Git worktree.", path)
    status = git(["-C", str(path), "status", "--porcelain"], operation="hook_run", check=False)
    if status.returncode != 0:
        raise _reconciliation_error("install_damaged", "The managed payload cannot report its Git status.", path)
    if status.stdout.strip():
        raise _reconciliation_error(
            "worktree_changed", "The managed payload has local changes and was preserved.", path
        )
    exists = git(["-C", str(path), "cat-file", "-e", f"{commit}^{{commit}}"], operation="hook_run", check=False)
    if exists.returncode != 0:
        raise _reconciliation_error(
            "revision_not_found",
            "The manifest commit is unavailable in the existing local Git objects.",
            path,
        )
    if head.stdout.strip().lower() == commit:
        return False
    make_logically_writable(path)
    try:
        checkout = git(
            ["-C", str(path), "checkout", "--detach", "--quiet", commit], operation="hook_run", check=False
        )
        if checkout.returncode != 0:
            raise _reconciliation_error(
                "source_access_failed", "Git could not switch the managed payload to the manifest commit.", path
            )
    finally:
        make_logically_read_only(path)
    return True


def _runtime_from_portable(record: dict[str, Any], portable: dict[str, Any], *, state: str) -> dict[str, Any]:
    identifier = record["install_id"]
    role = record["role"]
    return {
        "install_id": identifier,
        "install_path": f"/.doctidex/git/installs/{identifier}",
        "source_url": portable["source_url"],
        "canonical_source": record["canonical_source"],
        "source_relation": portable["source_relation"],
        "revision_selector": portable["revision_selector"],
        "default_branch": portable["default_branch"],
        "resolved_commit": portable["resolved_commit"],
        "requested_default": portable["default_branch"] is not None,
        "role": role,
        "parents": [] if role == "direct" else record["parents"],
        "managed_state": state,
    }


def _item(
    identifier: str,
    role: str,
    state: str,
    commit: str | None,
    revision_alignment: str,
    *findings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "install_id": identifier,
        "install_role": role,
        "state": state,
        "resolved_commit": commit,
        "revision_alignment": revision_alignment,
        "metadata_mismatches": [],
        "findings": list(findings),
    }


def _finding_from_error(error: DoctidexError) -> dict[str, Any]:
    return finding(error.domain, "error", error.code, error.message, path=error.path, actions=error.actions)


def _reconciliation_error(code: str, message: str, path: Path | None = None) -> DoctidexError:
    return DoctidexError(
        message,
        operation="hook_run",
        affected=[str(path)] if path else [],
        actions=["Preserve the current payload and inspect it before retrying checkout reconciliation."],
        code=code,
        domain="external",
        path=str(path) if path else None,
    )


def _hook_state_error(error: DoctidexError) -> DoctidexError:
    return DoctidexError(
        error.message,
        operation="hook_run",
        affected=error.affected,
        result=error.result,
        actions=error.actions,
        requires_user=error.requires_user,
        code=error.code,
        domain=error.domain,
        path=error.path,
        network=error.network,
        details=error.details,
        fields=error.fields,
    )


def _unique_paths(values: list[Path]) -> list[Path]:
    return list(dict.fromkeys(values))
