from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.document import DoctidexDocument
from whero.doctidex.protocol.tree import RootContext, inspect_path
from whero.doctidex.protocol.validation import validate_protocol

from .context import git_status, root_gitignore_status
from .mounts import GitMount, GitMountService, public_url
from .relations import current_root_reuse, git_branch, git_head, maintenance_reuse, repository_relation
from .repository import SourceRepository
from .state import StateStore


class MaintenanceService:
    def __init__(self, context: RootContext) -> None:
        self.context = context
        self.root = context.root
        self.store = StateStore(self.root)
        self.mounts = GitMountService(context)

    def scope(self, paths: list[Path]) -> list[dict[str, Any]]:
        scopes: dict[str, dict[str, Any]] = {}
        state = self.store.read()
        records = _maintenance_records(state)
        root_head = git_head(self.root, operation="maintenance_scope")
        root_branch = git_branch(self.root, operation="maintenance_scope")
        for path in paths or [self.root]:
            inspected = inspect_path(self.context, path)
            if inspected.source == "mount" and inspected.mount_path:
                mount, effective = self.mounts.effective(inspected.mount_path)
                target_branch = _target_branch(mount)
                relation = repository_relation(self.root, mount.url, effective, root_head=root_head)
                reuse = maintenance_reuse(
                    self.root,
                    mount.url,
                    effective,
                    relation,
                    records,
                    target_branch=target_branch,
                    root_branch=root_branch,
                )
                key = f"mount:{mount.mount_path}"
                scopes[key] = {
                    "kind": "mounted_source",
                    "mount_path": mount.mount_path,
                    "source": public_url(mount.url),
                    "declared_revision": mount.selector.as_dict(),
                    "base_commit": effective,
                    "target_branch": target_branch,
                    "read_only_path": str(self.root.joinpath(*mount.mount_path.lstrip("/").split("/"))),
                    "root_relation": relation,
                    "maintenance_reuse": reuse,
                    "write_action": _write_action(mount.mount_path, reuse),
                }
            else:
                key = f"root:{self.root}"
                scopes[key] = {
                    "kind": "host_root",
                    "root": str(self.root),
                    "base_commit": root_head,
                    "target_branch": root_branch,
                    "write_path": str(self.root),
                    "maintenance_reuse": current_root_reuse(self.root, root_branch),
                }
        return list(scopes.values())

    def guidance(self, mount_path: str) -> tuple[dict[str, str], dict[str, Any]]:
        mount, effective = self.mounts.effective(mount_path)
        relation = repository_relation(self.root, mount.url, effective)
        reuse = maintenance_reuse(
            self.root,
            mount.url,
            effective,
            relation,
            _maintenance_records(self.store.read()),
            target_branch=_target_branch(mount),
            root_branch=git_branch(self.root, operation="maintenance_guidance"),
        )
        return relation, reuse

    def open(self, mount_path: str) -> dict[str, Any]:
        mount, effective = self.mounts.effective(mount_path)
        if not effective:
            raise DoctidexError(
                f"The mount has no effective commit yet: {mount.mount_path}",
                operation="maintenance_open",
                affected=[mount.mount_path],
                actions=[f"Run doctidex-git mount prepare {mount.mount_path}, then retry maintenance open."],
                code="maintenance_source_not_prepared",
            )
        target_branch = _target_branch(mount)
        relation = repository_relation(self.root, mount.url, effective)
        reuse = maintenance_reuse(
            self.root,
            mount.url,
            effective,
            relation,
            _maintenance_records(self.store.read()),
            target_branch=target_branch,
            root_branch=git_branch(self.root, operation="maintenance_open"),
        )
        identifier = f"{int(time.time())}-{secrets.token_hex(4)}"
        repository = SourceRepository(mount.url)
        path = repository.open_maintenance(effective, identifier)

        def update(data: dict[str, Any]) -> None:
            data["maintenance"][identifier] = {
                "path": str(path),
                "host_root": str(self.root),
                "mount_path": mount.mount_path,
                "url": mount.url,
                "base_commit": effective,
                "target_branch": target_branch,
            }

        self.store.update(update)
        next_actions = [
            f"Maintain files under {path} using the source root index.md.",
            f"Run doctidex-git check {path}.",
            f"Run doctidex-git maintenance handoff {path}.",
        ]
        if reuse["status"] != "not_available":
            next_actions.insert(0, _reuse_notice(reuse))
        return {
            "status": "warning" if reuse["status"] != "not_available" else "ok",
            "operation": "maintenance_open",
            "root": str(self.root),
            "maintenance_root": str(path),
            "mount_path": mount.mount_path,
            "source": public_url(mount.url),
            "base_commit": effective,
            "target_branch": target_branch,
            "writable_root": str(path),
            "boundaries": {"writable": str(path), "host_mount": "read_only"},
            "root_relation": relation,
            "maintenance_reuse": reuse,
            "next_actions": next_actions,
            "changed": [],
            "result": "Independent maintenance root is ready."
            if reuse["status"] == "not_available"
            else "Independent maintenance root is ready; a compatible scope was already available.",
        }

    def status(self, maintenance_root: Path | None) -> list[dict[str, Any]]:
        contexts = self._select(maintenance_root)
        results: list[dict[str, Any]] = []
        for _identifier, item in contexts:
            path = Path(item["path"])
            changes = git_status(path) if path.is_dir() else []
            results.append(
                {
                    "maintenance_root": str(path),
                    "mount_path": item["mount_path"],
                    "source": public_url(item["url"]),
                    "base_commit": item["base_commit"],
                    "target_branch": item.get("target_branch"),
                    "state": "has_changes" if changes else "ready",
                    "change_count": len(changes),
                    "changes": changes,
                }
            )
        return results

    def handoff(self, maintenance_root: Path | None) -> dict[str, Any]:
        selected = self._select(maintenance_root)
        if len(selected) != 1:
            raise DoctidexError(
                "Select exactly one maintenance root for handoff.",
                operation="maintenance_handoff",
                affected=[item[1]["path"] for item in selected],
                actions=["Retry with the maintenance root path."],
                code="maintenance_root_ambiguous",
            )
        _, item = selected[0]
        path = Path(item["path"])
        index = DoctidexDocument.load(path / "index.md")
        protocol = validate_protocol(RootContext(path, index))
        changes = git_status(path)
        readiness = root_gitignore_status(path)
        semantic = list(protocol["semantic_candidates"])
        for change in changes:
            if not change["path"].endswith(("index.md", "log.md")):
                semantic.append(
                    {
                        "domain": "semantic_review",
                        "severity": "info",
                        "code": "git_change_review",
                        "path": change["path"],
                        "message": "Review whether this change requires index or log follow-up.",
                        "actions": ["Read the responsible index and applicable log before deciding."],
                    }
                )
        return {
            "status": "warning"
            if protocol["protocol_structure"] == "fail" or readiness["status"] == "blocked" or semantic
            else "ok",
            "operation": "maintenance_handoff",
            "maintenance_root": str(path),
            "mount_path": item["mount_path"],
            "source": public_url(item["url"]),
            "base_commit": item["base_commit"],
            "target_branch": item.get("target_branch"),
            "changes": changes,
            "change_count": len(changes),
            "protocol_structure": protocol["protocol_structure"],
            "semantic_review": "required" if semantic else "clear",
            "plugin_readiness": readiness["status"],
            "findings": protocol["findings"],
            "semantic_candidates": semantic,
            "result": "Maintenance result is preserved and ready for agent review.",
            "next_actions": [
                "Review the diff and semantic candidates.",
                "Ask the user to authorize the required commit, push, or merge actions.",
            ],
        }

    def close(self, maintenance_root: Path | None) -> dict[str, Any]:
        selected = self._select(maintenance_root)
        if len(selected) != 1:
            raise DoctidexError(
                "Select exactly one clean maintenance root to close.",
                operation="maintenance_close",
                affected=[item[1]["path"] for item in selected],
                actions=["Retry with the exact maintenance root path."],
                code="maintenance_root_ambiguous",
            )
        identifier, item = selected[0]
        path = Path(item["path"])
        changes = git_status(path)
        if changes:
            raise DoctidexError(
                "The maintenance result has uncommitted changes and was preserved.",
                operation="maintenance_close",
                affected=[str(path)],
                result=f"Maintenance root remains available at {path}.",
                actions=["Run maintenance handoff and decide the required Git actions before closing."],
                requires_user="git_action",
                code="maintenance_has_changes",
            )
        SourceRepository(item["url"]).remove_maintenance(path)
        self.store.update(lambda data: data["maintenance"].pop(identifier, None))
        return {
            "status": "ok",
            "operation": "maintenance_close",
            "maintenance_root": str(path),
            "changed": [],
            "result": "Clean maintenance context closed.",
        }

    def _select(self, maintenance_root: Path | None) -> list[tuple[str, dict[str, Any]]]:
        state = self.store.read()
        entries = list(state.get("maintenance", {}).items())
        if maintenance_root is None:
            return entries
        target = maintenance_root.absolute()
        return [(identifier, item) for identifier, item in entries if Path(item.get("path", "")).absolute() == target]


def _maintenance_records(state: dict[str, Any]) -> list[dict[str, Any]]:
    maintenance = state.get("maintenance")
    if not isinstance(maintenance, dict):
        return []
    return [item for item in maintenance.values() if isinstance(item, dict)]


def _target_branch(mount: GitMount) -> str | None:
    return mount.selector.value if mount.selector.kind == "branch" else None


def _write_action(mount_path: str, reuse: dict[str, Any]) -> str | None:
    if reuse["status"] == "recommended":
        return None
    if reuse["status"] == "selection_required":
        return "doctidex-git maintenance status --json"
    return f"doctidex-git maintenance open {mount_path}"


def _reuse_notice(reuse: dict[str, Any]) -> str:
    if reuse["status"] == "selection_required":
        return "Compatible same-commit maintenance scopes already exist; select one or keep this explicit isolation."
    return (
        f"A compatible {reuse['scope_kind']} was already available at {reuse['write_path']}; "
        "keep compatible changes in one scope unless isolation was intentional."
    )
