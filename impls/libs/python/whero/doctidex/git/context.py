from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .runner import git


def git_worktree(path: Path) -> Path | None:
    result = git(["-C", str(path), "rev-parse", "--show-toplevel"], operation="git_context", check=False)
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def git_status(path: Path) -> list[dict[str, str]]:
    result = git(["-C", str(path), "status", "--porcelain=v1", "-z"], operation="git_changes")
    entries: list[dict[str, str]] = []
    chunks = result.stdout.split("\0")
    index = 0
    while index < len(chunks):
        chunk = chunks[index]
        if not chunk:
            index += 1
            continue
        status = chunk[:2]
        file_path = chunk[3:]
        entry = {"status": status, "path": file_path}
        if status[0] in {"R", "C"} and index + 1 < len(chunks):
            entry["original_path"] = chunks[index + 1]
            index += 1
        entries.append(entry)
        index += 1
    return entries


def root_gitignore_status(root: Path) -> dict[str, Any]:
    worktree = git_worktree(root)
    if worktree is None:
        return {"status": "not_applicable", "ignored": False, "tracked": []}
    mount_dir = root / ".doctidex" / "mounts"
    relative_mount = Path(os.path.relpath(mount_dir, worktree)).as_posix()
    probe = relative_mount + "/.doctidex-ignore-probe"
    ignored = git(
        ["-C", str(worktree), "check-ignore", "-v", "--no-index", probe],
        operation="gitignore_check",
        check=False,
    )
    root_ignore = root / ".gitignore"
    source = ignored.stdout.split(":", 1)[0] if ignored.returncode == 0 else ""
    covered_by_root = bool(source) and Path(source).resolve(strict=False) == root_ignore.resolve(strict=False)
    tracked_result = git(
        ["-C", str(worktree), "ls-files", "-z", "--", relative_mount],
        operation="gitignore_check",
    )
    tracked = [item for item in tracked_result.stdout.split("\0") if item]
    return {
        "status": "ready" if covered_by_root and not tracked else "blocked",
        "ignored": covered_by_root,
        "ignore_file": str(root_ignore),
        "tracked": tracked,
    }


def ensure_root_gitignore(root: Path) -> bool:
    path = root / ".gitignore"
    required = "/.doctidex/mounts/"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if any(line.strip() == required for line in existing.splitlines()):
        return False
    separator = "" if not existing or existing.endswith("\n") else "\n"
    path.write_text(existing + separator + required + "\n", encoding="utf-8")
    return True
