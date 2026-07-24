from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.constants import MOUNT_EXCLUDE
from whero.doctidex.protocol.document import DoctidexDocument
from whero.doctidex.protocol.tree import discover_roots

from .context import ensure_root_gitignore, git_worktree


def initialize(path: Path, *, apply: bool) -> dict[str, Any]:
    requested = path.absolute()
    if requested.is_file():
        requested = requested.parent
    roots = discover_roots(requested)
    if len(roots) > 1:
        raise DoctidexError(
            "More than one doctidex root could be selected for initialization.",
            operation="init",
            affected=[str(item.root) for item in roots],
            actions=["Retry with the exact root directory."],
            requires_user="doctidex_root",
            code="root_ambiguous",
        )
    root = roots[0].root if roots else requested
    if git_worktree(root) is None:
        raise DoctidexError(
            "The selected directory is not inside a Git working tree.",
            operation="init",
            affected=[str(root)],
            actions=["Select a Git-managed directory and retry."],
            code="git_worktree_required",
        )

    index_path = root / "index.md"
    changes: list[str] = []
    if index_path.exists():
        document = DoctidexDocument.load(index_path)
    else:
        document = DoctidexDocument.new_root(index_path)
        changes.append(str(index_path))
    if _ensure_index_structure(document, root):
        if str(index_path) not in changes:
            changes.append(str(index_path))
    gitignore = root / ".gitignore"
    if not _has_required_gitignore(gitignore):
        changes.append(str(gitignore))

    candidates = (
        [
            str(child)
            for child in sorted(root.iterdir(), key=lambda item: item.name)
            if child.name not in {"index.md", ".git", ".doctidex"}
        ]
        if root.exists()
        else []
    )

    if apply:
        root.mkdir(parents=True, exist_ok=True)
        document.write()
        ensure_root_gitignore(root)
    return {
        "status": "ok",
        "operation": "init",
        "root": str(root),
        "index": str(index_path),
        "applied": apply,
        "network": False,
        "changed": changes if apply else [],
        "planned_changes": changes,
        "semantic_review": "required" if candidates else "clear",
        "semantic_candidates": [
            {
                "domain": "semantic_review",
                "severity": "info",
                "code": "index_reference_candidate",
                "path": item,
                "message": "Review whether the root index already contains a recognizable entry for this path.",
                "actions": ["Keep sufficient existing prose or write an index entry with an appropriate link."],
            }
            for item in candidates
        ],
        "plugin_readiness": "ready" if apply or not changes else "blocked",
        "result": "Root structure initialized; agent semantic review is next."
        if apply
        else "Initialization plan is ready.",
    }


def _ensure_index_structure(document: DoctidexDocument, root: Path) -> bool:
    changed = False
    if document.data.get("type") != "index":
        document.data["type"] = "index"
        changed = True
    doctidex = document.doctidex
    if doctidex is None:
        doctidex = CommentedMap()
        document.data["doctidex"] = doctidex
        changed = True
    if doctidex.get("type") != "index":
        doctidex["type"] = "index"
        changed = True
    if doctidex.get("root") is not True:
        doctidex["root"] = True
        changed = True
    excludes = doctidex.get("excludes")
    if not isinstance(excludes, list):
        excludes = CommentedSeq()
        doctidex["excludes"] = excludes
        changed = True
    required = [MOUNT_EXCLUDE]
    if (root / ".git").exists():
        required.append(".git")
    for value in required:
        if not any(isinstance(item, dict) and item.get("path") == value for item in excludes):
            excludes.append(CommentedMap({"path": value}))
            changed = True
    return changed


def _has_required_gitignore(path: Path) -> bool:
    if not path.is_file():
        return False
    return any(line.strip() == "/.doctidex/mounts/" for line in path.read_text(encoding="utf-8").splitlines())
