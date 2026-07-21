"""Git source identity and transition checks for the View runtime."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

from .git import preferred_remote
from .model import STATUS_FILENAME
from .view_errors import fail
from .view_source import decode_frontmatter_string
from .view_types import GitSource, GitTreeNode, SourceChange


def git_output(directory: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_command(directory: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        fail(f"cannot run Git for {directory}: {exc}")


def git_source_identity(source: Path) -> GitSource | None:
    inside_work_tree = git_output(source, "rev-parse", "--is-inside-work-tree")
    if inside_work_tree != "true":
        return None
    tracked_files = git_output(source, "ls-files", "--", ".")
    if not tracked_files:
        return None

    commit = git_output(source, "rev-parse", "HEAD")
    if (
        not commit
        or len(commit) < 40
        or any(character not in "0123456789abcdefABCDEF" for character in commit)
    ):
        fail(f"cannot determine a valid Git commit for source {source}")
    root_text = git_output(source, "rev-parse", "--show-toplevel")
    if not root_text:
        fail(f"cannot determine the Git worktree root for source {source}")
    root = Path(root_text).resolve(strict=True)
    try:
        relative = source.relative_to(root)
    except ValueError:
        fail(f"source {source} is outside its reported Git worktree {root}")
    wiki_path = PurePosixPath(".") if not relative.parts else PurePosixPath(*relative.parts)
    return GitSource(commit.lower(), root, wiki_path, preferred_remote(source))


def decode_git_path(raw: bytes) -> str:
    return raw.decode("utf-8", errors="surrogateescape")


def relative_git_tree_path(
    repository_path: str,
    wiki_path: PurePosixPath,
) -> PurePosixPath | None:
    path = PurePosixPath(repository_path)
    if wiki_path == PurePosixPath("."):
        return path
    if path.parts[: len(wiki_path.parts)] != wiki_path.parts:
        return None
    remainder = path.parts[len(wiki_path.parts) :]
    return PurePosixPath(*remainder) if remainder else None


def git_tree_inventory(
    git_source: GitSource,
    commit: str,
    wiki_path: PurePosixPath,
) -> dict[PurePosixPath, GitTreeNode]:
    arguments = ["ls-tree", "-r", "-z", "--full-tree", commit]
    if wiki_path != PurePosixPath("."):
        arguments.extend(["--", wiki_path.as_posix()])
    result = git_command(git_source.root, *arguments)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(
            f"cannot inspect Git tree {commit[:12]} for {wiki_path}: "
            f"{detail or 'git ls-tree failed'}"
        )

    inventory: dict[PurePosixPath, GitTreeNode] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, separator, raw_path = record.partition(b"\t")
        if not separator:
            fail(f"cannot parse Git tree entry at commit {commit[:12]}")
        fields = metadata.split()
        if len(fields) != 3:
            fail(f"cannot parse Git tree metadata at commit {commit[:12]}")
        mode = fields[0].decode("ascii", errors="replace")
        object_type = fields[1].decode("ascii", errors="replace")
        object_id = fields[2].decode("ascii", errors="replace")
        relative = relative_git_tree_path(decode_git_path(raw_path), wiki_path)
        if relative is None:
            continue
        if mode == "120000":
            node = GitTreeNode("symlink", object_id)
        elif mode == "160000" or object_type == "commit":
            node = GitTreeNode("gitlink", object_id)
        else:
            node = GitTreeNode("file", object_id)
        inventory[relative] = node
        for depth in range(1, len(relative.parts)):
            directory = PurePosixPath(*relative.parts[:depth])
            inventory.setdefault(directory, GitTreeNode("directory"))
    return inventory


def tree_changes(
    previous: dict[PurePosixPath, GitTreeNode],
    current: dict[PurePosixPath, GitTreeNode],
) -> list[SourceChange]:
    changes: list[SourceChange] = []
    for path in sorted(set(previous) | set(current), key=str):
        old = previous.get(path)
        new = current.get(path)
        if old is None:
            changes.append(SourceChange("added", path))
        elif new is None:
            changes.append(SourceChange("removed", path))
        elif old != new:
            kind = (
                "content-changed"
                if old.kind == new.kind == "file"
                else "type-or-link-changed"
            )
            changes.append(SourceChange(kind, path))
    return changes


def paths_intersect(left: PurePosixPath, right: PurePosixPath) -> bool:
    shared = min(len(left.parts), len(right.parts))
    return left.parts[:shared] == right.parts[:shared]


def affected_source_changes(
    changes: list[SourceChange],
    disclosed_roots: list[PurePosixPath],
) -> tuple[list[SourceChange], list[PurePosixPath]]:
    affected = [
        change
        for change in changes
        if any(paths_intersect(change.path, root) for root in disclosed_roots)
    ]
    affected_roots = sorted(
        {
            root
            for root in disclosed_roots
            if any(paths_intersect(change.path, root) for change in affected)
        },
        key=str,
    )
    return affected, affected_roots


def _git_paths(
    git_source: GitSource,
    *arguments: str,
) -> list[PurePosixPath]:
    result = git_command(git_source.root, *arguments)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(f"cannot inspect Git worktree: {detail or 'Git command failed'}")
    paths: list[PurePosixPath] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = relative_git_tree_path(
            decode_git_path(raw),
            git_source.wiki_path,
        )
        if relative is not None:
            paths.append(relative)
    return paths


def worktree_blob_identity(
    source: Path,
    git_source: GitSource,
    relative: PurePosixPath,
) -> str | None:
    source_item = source.joinpath(*relative.parts)
    repository_relative = (
        relative
        if git_source.wiki_path == PurePosixPath(".")
        else git_source.wiki_path / relative
    )
    result = git_command(
        git_source.root,
        "hash-object",
        f"--path={repository_relative.as_posix()}",
        "--",
        str(source_item),
    )
    if result.returncode != 0:
        return None
    value = result.stdout.decode("ascii", errors="replace").strip()
    return value or None


def validate_git_worktree_disclosure(
    source: Path,
    git_source: GitSource | None,
    disclosed_roots: list[PurePosixPath],
) -> None:
    if git_source is None or not disclosed_roots:
        return
    pathspec = git_source.wiki_path.as_posix()
    result = git_command(
        git_source.root,
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        "HEAD",
        "--",
        pathspec,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(f"cannot inspect Git worktree: {detail or 'git diff failed'}")
    fields = [field for field in result.stdout.split(b"\0") if field]
    if len(fields) % 2:
        fail("cannot parse Git worktree status")

    head_tree = git_tree_inventory(
        git_source,
        git_source.commit,
        git_source.wiki_path,
    )
    changes: list[SourceChange] = []
    for offset in range(0, len(fields), 2):
        status = decode_git_path(fields[offset])
        relative = relative_git_tree_path(
            decode_git_path(fields[offset + 1]),
            git_source.wiki_path,
        )
        if relative is None:
            continue
        head_node = head_tree.get(relative)
        current = source.joinpath(*relative.parts)
        regular_file = (
            status == "M"
            and head_node is not None
            and head_node.kind == "file"
            and current.is_file()
            and not current.is_symlink()
        )
        if regular_file:
            current_identity = worktree_blob_identity(
                source,
                git_source,
                relative,
            )
            if current_identity != head_node.identity:
                changes.append(SourceChange("worktree-content-changed", relative))
        else:
            changes.append(SourceChange(f"worktree-{status.lower()}", relative))

    untracked = _git_paths(
        git_source,
        "ls-files",
        "-z",
        "--full-name",
        "--others",
        "--exclude-standard",
        "--",
        pathspec,
    )
    ignored = _git_paths(
        git_source,
        "ls-files",
        "-z",
        "--full-name",
        "--others",
        "--ignored",
        "--exclude-standard",
        "--",
        pathspec,
    )
    changes.extend(SourceChange("untracked", path) for path in untracked)
    changes.extend(SourceChange("ignored", path) for path in ignored)
    for root in disclosed_roots:
        if root not in head_tree and not any(
            paths_intersect(change.path, root) for change in changes
        ):
            changes.append(SourceChange("untracked-root", root))

    affected, affected_roots = affected_source_changes(changes, disclosed_roots)
    if not affected:
        return
    counts: dict[str, int] = {}
    for change in affected:
        counts[change.kind] = counts.get(change.kind, 0) + 1
    impact = ", ".join(
        f"{kind}={count}" for kind, count in sorted(counts.items())
    )
    roots = ", ".join(path.as_posix() for path in affected_roots)
    paths = ", ".join(sorted({change.path.as_posix() for change in affected}))
    message = (
        "Git worktree cannot provide a stable View identity\n"
        "what happened: uncommitted content, structure, or untracked material "
        f"intersects effective roots [{roots}] ({impact}): {paths}; no View update "
        "changes were applied"
    )
    if any(change.kind == "worktree-content-changed" for change in affected):
        message += (
            "; existing read-through symlinks may already expose the changed "
            "source bytes, but generated links and status were not updated"
            "\npossible handling: inspect the listed paths, then commit the intended "
            "source state or restore it to HEAD before repairing or rebuilding the "
            "affected View"
        )
    fail(message)


def git_diff_command(
    git_source: GitSource,
    previous_commit: str,
    previous_wiki_path: PurePosixPath,
) -> str:
    command = [
        "git",
        "-C",
        str(git_source.root),
        "diff",
        "--name-status",
        "--find-renames",
        f"{previous_commit}..{git_source.commit}",
        "--",
        previous_wiki_path.as_posix(),
    ]
    if git_source.wiki_path != previous_wiki_path:
        command.append(git_source.wiki_path.as_posix())
    return " ".join(shlex.quote(part) for part in command)


def recorded_git_path(
    fields: dict[str, Any],
    recorded_source: Path,
    current: GitSource,
) -> PurePosixPath:
    raw = fields.get("source_git_path")
    if raw:
        value = decode_frontmatter_string(raw)
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            fail(f"invalid source_git_path in {STATUS_FILENAME}: {value!r}")
        return PurePosixPath(".") if value in ("", ".") else path
    try:
        relative = recorded_source.relative_to(current.root)
    except ValueError:
        relative = None
    if relative is not None:
        return (
            PurePosixPath(".")
            if not relative.parts
            else PurePosixPath(*relative.parts)
        )
    if recorded_source.exists():
        inferred = git_source_identity(recorded_source)
        if inferred:
            return inferred.wiki_path
    return current.wiki_path


def require_forward_commit(
    git_source: GitSource,
    previous_commit: str,
) -> None:
    remote_hint = (
        f"; source remote: {git_source.remote.fetch_url}"
        if git_source.remote
        else ""
    )
    result = git_command(
        git_source.root,
        "merge-base",
        "--is-ancestor",
        previous_commit,
        git_source.commit,
    )
    if result.returncode == 0:
        return
    if result.returncode not in (0, 1):
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(
            "source Git ancestry could not be verified\n"
            f"what happened: Git could not compare recorded commit "
            f"{previous_commit} with supplied commit {git_source.commit}; "
            "structural diff analysis was skipped"
            + (f"; Git reported: {detail}" if detail else "")
            + "\nno repair plan was generated because the commit relationship "
            "is unknown"
            + remote_hint
        )
    fail(
        "source Git commit is not an accepted forward update\n"
        f"what happened: recorded commit {previous_commit} is not an ancestor of "
        f"supplied commit {git_source.commit}; structural diff analysis was skipped\n"
        "no repair plan was generated because the commit history is not an "
        "accepted forward transition"
        + remote_hint
    )


def validate_git_transition(
    git_source: GitSource,
    previous_commit: str,
    previous_wiki_path: PurePosixPath,
    disclosed_roots: list[PurePosixPath],
) -> str | None:
    if previous_commit == git_source.commit:
        return None
    require_forward_commit(git_source, previous_commit)
    previous_tree = git_tree_inventory(
        git_source,
        previous_commit,
        previous_wiki_path,
    )
    current_tree = git_tree_inventory(
        git_source,
        git_source.commit,
        git_source.wiki_path,
    )
    changes = tree_changes(previous_tree, current_tree)
    affected, affected_roots = affected_source_changes(changes, disclosed_roots)
    inspect_command = git_diff_command(
        git_source,
        previous_commit,
        previous_wiki_path,
    )
    if affected:
        counts: dict[str, int] = {}
        for change in affected:
            counts[change.kind] = counts.get(change.kind, 0) + 1
        impact = ", ".join(
            f"{kind}={count}" for kind, count in sorted(counts.items())
        )
        roots = ", ".join(path.as_posix() for path in affected_roots)
        content_changed = any(
            change.kind == "content-changed" for change in affected
        )
        change_subject = "content or structure" if content_changed else "structure"
        fail(
            f"forward Git update changes the disclosed {change_subject}\n"
            f"what happened: {previous_commit[:12]}..{git_source.commit[:12]} is "
            f"forward, but source changes intersect effective roots "
            f"[{roots}] ({impact}); generated links and status were not updated, "
            "although existing read-through symlinks may already expose changed "
            "source bytes\n"
            "possible handling: inspect the Git change, repair or rebuild the "
            "affected View for the new source state, and ask the user to "
            "review the proposed selection and content; "
            f"inspect with: {inspect_command}"
        )
    outside_count = len(changes)
    return (
        f"Git source advanced {previous_commit[:12]}..{git_source.commit[:12]}; "
        "no source change intersects the current View"
        + (
            f" ({outside_count} source change(s) remain outside its roots)"
            if outside_count
            else ""
        )
        + f". Inspect if needed: {inspect_command}"
    )
