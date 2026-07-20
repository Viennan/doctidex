#!/usr/bin/env python3
"""Build a partial Whero Wiki view with relative symbolic links."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn

from whero_wiki_tools.errors import WheroToolError
from whero_wiki_tools.frontmatter import (
    frontmatter_is_true as shared_frontmatter_is_true,
    read_flat_frontmatter,
    read_frontmatter as shared_read_frontmatter,
    scalar_text,
)
from whero_wiki_tools.model import (
    STATUS_FILENAME,
    WIKI_META_FILENAME,
    validate_wiki_root,
)
from whero_wiki_tools.git import GitRemote, preferred_remote
from whero_wiki_tools.mounts import WikiMount, discover_boundaries, mount_for_path
from whero_wiki_tools.preserved import (
    PreservedPath,
    preserved_for_path,
)


DEFAULT_COLLAPSE_THRESHOLD = 80.0


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


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _selection_candidate(
    source: Path,
    candidate: Path,
) -> tuple[PurePosixPath, bool] | None:
    logical = Path(os.path.abspath(candidate.expanduser()))
    try:
        resolved = logical.resolve(strict=False)
    except OSError:
        return None
    if not is_within(resolved, source):
        return None
    selected = logical if is_within(logical, source) else resolved
    try:
        relative = selected.relative_to(source)
    except ValueError:
        return None
    if not relative.parts:
        return PurePosixPath("."), logical.exists()
    return PurePosixPath(*relative.parts), logical.exists()


def parse_selection(
    raw: str,
    source: Path,
    *,
    additional_bases: list[Path] | None = None,
) -> PurePosixPath:
    value = raw.strip()
    if not value:
        fail("include paths must not be empty")
    supplied = Path(value).expanduser()
    raw_candidates = (
        [supplied]
        if supplied.is_absolute()
        else [
            source / supplied,
            Path.cwd() / supplied,
            *((base / supplied) for base in additional_bases or []),
        ]
    )
    candidate_states = {
        candidate: exists
        for raw_candidate in raw_candidates
        if (parsed := _selection_candidate(source, raw_candidate)) is not None
        for candidate, exists in [parsed]
    }
    if not candidate_states:
        fail(
            f"include path must resolve inside the source Wiki: {raw!r}"
        )
    existing = {path for path, exists in candidate_states.items() if exists}
    candidates = existing or set(candidate_states)
    if len(candidates) > 1:
        names = ", ".join(path.as_posix() for path in sorted(candidates, key=str))
        fail(
            f"include path is ambiguous across valid base directories: "
            f"{raw!r} -> [{names}]; use an absolute path"
        )
    result = next(iter(candidates))
    if result == PurePosixPath("."):
        fail("include path must identify an item below the source Wiki root")
    if result == PurePosixPath(STATUS_FILENAME):
        fail(f"{STATUS_FILENAME} is generated and cannot be selected from source")
    return result


def parse_collapse_threshold(raw: str) -> float:
    value = raw.strip()
    percent_form = value.endswith("%")
    if percent_form:
        value = value[:-1]
    try:
        threshold = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid collapse threshold: {raw!r}")
    if not percent_form and 0 < threshold <= 1:
        threshold *= 100
    if not 0 <= threshold <= 100:
        raise argparse.ArgumentTypeError("collapse threshold must be between 0 and 100")
    return threshold


def parse_view_name(raw: str) -> str:
    value = raw.strip()
    path = PurePosixPath(value)
    if not value or path.is_absolute() or len(path.parts) != 1 or value in (".", ".."):
        raise argparse.ArgumentTypeError(
            "view name must be one non-empty directory name"
        )
    return value


def collapse_selections(paths: set[PurePosixPath]) -> list[PurePosixPath]:
    ordered = sorted(paths, key=lambda path: (len(path.parts), str(path)))
    collapsed: list[PurePosixPath] = []
    for candidate in ordered:
        if any(
            candidate.parts[: len(parent.parts)] == parent.parts
            for parent in collapsed
        ):
            continue
        collapsed.append(candidate)
    return collapsed


def load_selections(
    source: Path,
    values: list[str],
    files: list[Path],
) -> list[PurePosixPath]:
    selections = {parse_selection(value, source) for value in values}
    for selection_file in files:
        try:
            resolved_file = selection_file.expanduser().resolve(strict=True)
            lines = resolved_file.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            fail(f"cannot read include file {selection_file}: {exc}")
        selections.update(
            parse_selection(
                line.strip(),
                source,
                additional_bases=[resolved_file.parent],
            )
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        )
    if not selections:
        fail("provide at least one --include or --include-from path")

    return collapse_selections(selections)


def read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        return shared_read_frontmatter(path)
    except WheroToolError as exc:
        fail(str(exc))


def frontmatter_is_true(fields: dict[str, Any], key: str) -> bool:
    return shared_frontmatter_is_true(fields, key)


def decode_frontmatter_string(value: Any) -> str:
    return scalar_text(value)


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
                changes.append(
                    SourceChange("worktree-content-changed", relative)
                )
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
        "Git worktree cannot provide a stable disclosure identity\n"
        f"what happened: uncommitted content, structure, or untracked material intersects "
        f"disclosed roots [{roots}] ({impact}): {paths}; no disclosure changes "
        "were applied"
    )
    if any(change.kind == "worktree-content-changed" for change in affected):
        message += (
            "; existing read-through symlinks may already expose the changed "
            "source bytes, but generated links and status were not updated"
            "\npossible handling: inspect the listed paths, then commit the intended "
            "source state or restore it to HEAD before repairing or rebuilding the "
            "affected disclosure"
        )
    fail(message)


def git_diff_command(
    git_source: GitSource,
    previous_commit: str,
    previous_wiki_path: PurePosixPath,
) -> str:
    import shlex

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
    fields: dict[str, str],
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
            f"structural diff analysis was skipped"
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
            f"forward, but source changes intersect disclosed roots "
            f"[{roots}] ({impact}); generated links and status were not updated, "
            "although existing read-through symlinks may already expose changed "
            "source bytes\n"
            "possible handling: inspect the Git change, repair or rebuild the "
            "affected disclosure for the new source state, and ask the user to "
            "review the proposed scope and content; "
            f"inspect with: {inspect_command}"
        )
    outside_count = len(changes)
    return (
        f"Git source advanced {previous_commit[:12]}..{git_source.commit[:12]}; "
        "no source change intersects the current disclosure"
        + (
            f" ({outside_count} source change(s) remain outside its roots)"
            if outside_count
            else ""
        )
        + f". Inspect if needed: {inspect_command}"
    )


def validate_wiki_meta(source: Path) -> None:
    try:
        validate_wiki_root(source)
    except WheroToolError as exc:
        fail(str(exc))


def is_scope_required_file(path: Path) -> bool:
    if path.name == STATUS_FILENAME:
        return False
    if path.suffix.lower() != ".md" or not path.is_file():
        return False
    try:
        fields = read_flat_frontmatter(path)
    except WheroToolError as exc:
        fail(str(exc))
    if not frontmatter_is_true(fields, "whero_scope_required"):
        return False
    if not frontmatter_is_true(fields, "whero_maintenance"):
        fail(
            f"scope-required file must set whero_maintenance: true: {path}"
        )
    return True


def add_path_scope_files(
    source: Path,
    requested: list[PurePosixPath],
    stop_at: set[PurePosixPath] | None = None,
) -> list[PurePosixPath]:
    expanded = set(requested)
    stop_at = stop_at or set()
    for selection in requested:
        source_item = source.joinpath(*selection.parts)
        try:
            resolved_item = source_item.resolve(strict=True)
        except OSError as exc:
            fail(f"source item does not exist: {selection} ({exc})")
        if not is_within(resolved_item, source):
            fail(f"source item resolves outside the source wiki: {selection}")

        owner_parts = (
            selection.parts if resolved_item.is_dir() else selection.parts[:-1]
        )
        for boundary in stop_at:
            if selection.parts[: len(boundary.parts)] == boundary.parts:
                owner_parts = boundary.parts[:-1]
                break
        for depth in range(len(owner_parts) + 1):
            directory = source.joinpath(*owner_parts[:depth])
            try:
                children = sorted(directory.iterdir(), key=lambda path: path.name)
            except OSError as exc:
                fail(f"cannot inspect source directory {directory}: {exc}")
            for child in children:
                if is_scope_required_file(child):
                    expanded.add(PurePosixPath(*child.relative_to(source).parts))
    return collapse_selections(expanded)


def source_files(
    source: Path,
    excluded_roots: set[PurePosixPath] | None = None,
) -> set[PurePosixPath]:
    files: set[PurePosixPath] = set()
    excluded_roots = excluded_roots or set()
    for directory, dirnames, filenames in os.walk(source, followlinks=False):
        current = Path(directory)
        relative_current = PurePosixPath(*current.relative_to(source).parts)
        dirnames[:] = [
            name
            for name in dirnames
            if name != ".git"
            and (
                relative_current / name if relative_current.parts else PurePosixPath(name)
            )
            not in excluded_roots
        ]
        for name in filenames:
            candidate = current / name
            if candidate.name == STATUS_FILENAME:
                continue
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                fail(f"cannot inspect source file {candidate}: {exc}")
            if not resolved.is_file():
                continue
            if not is_within(resolved, source):
                fail(f"source file resolves outside the source wiki: {candidate}")
            files.add(PurePosixPath(*candidate.relative_to(source).parts))
    return files


def disclosed_file_coverage(
    source: Path,
    selections: list[PurePosixPath],
    files: set[PurePosixPath],
) -> set[PurePosixPath]:
    covered: set[PurePosixPath] = set()
    for selection in selections:
        item = source.joinpath(*selection.parts)
        try:
            resolved = item.resolve(strict=True)
        except OSError as exc:
            fail(f"source item does not exist: {selection} ({exc})")
        if resolved.is_dir():
            covered.update(
                path
                for path in files
                if path.parts[: len(selection.parts)] == selection.parts
            )
        elif selection in files:
            covered.add(selection)
    return covered


def adaptively_collapse(
    source: Path,
    selections: list[PurePosixPath],
    threshold: float,
    excluded_roots: set[PurePosixPath] | None = None,
) -> tuple[list[PurePosixPath], list[PurePosixPath]]:
    if threshold == 0:
        return selections, []

    files = source_files(source, excluded_roots)
    blocked_directories: set[PurePosixPath] = set()
    for excluded in excluded_roots or set():
        for depth in range(1, len(excluded.parts) + 1):
            blocked_directories.add(PurePosixPath(*excluded.parts[:depth]))
    totals: dict[PurePosixPath, int] = {}
    for path in files:
        for depth in range(1, len(path.parts)):
            directory = PurePosixPath(*path.parts[:depth])
            totals[directory] = totals.get(directory, 0) + 1

    original = set(selections)
    current = selections
    while True:
        covered = disclosed_file_coverage(source, current, files)
        covered_totals: dict[PurePosixPath, int] = {}
        for path in covered:
            for depth in range(1, len(path.parts)):
                directory = PurePosixPath(*path.parts[:depth])
                covered_totals[directory] = covered_totals.get(directory, 0) + 1

        candidates = {
            directory
            for directory, total in totals.items()
            if covered_totals.get(directory, 0) * 100 >= threshold * total
            and directory not in blocked_directories
        }
        combined = collapse_selections(set(current) | candidates)
        if combined == current:
            break
        current = combined

    collapsed_directories = [
        path
        for path in current
        if path not in original
        and source.joinpath(*path.parts).resolve(strict=True).is_dir()
    ]
    return current, collapsed_directories


def directory_scope_expansion_notice(
    source: Path,
    baseline_selections: list[PurePosixPath],
    directory: PurePosixPath,
    label: str,
    threshold: float | None = None,
    excluded_roots: set[PurePosixPath] | None = None,
) -> str:
    files = source_files(source, excluded_roots)
    covered = disclosed_file_coverage(source, baseline_selections, files)
    contained = {
        path
        for path in files
        if path.parts[: len(directory.parts)] == directory.parts
    }
    previously_covered = contained & covered
    descendant_roots = [
        selection
        for selection in baseline_selections
        if selection.parts[: len(directory.parts)] == directory.parts
    ]
    percentage = len(previously_covered) * 100 / len(contained) if contained else 100
    threshold_text = f" (threshold {threshold:g}%)" if threshold is not None else ""
    return (
        f"{label}: {directory.as_posix()} had {percentage:.1f}% visible coverage"
        f"{threshold_text}; visible scope expands by "
        f"{len(contained) - len(previously_covered)} file(s), and "
        f"{len(descendant_roots)} descendant selection root(s) become one "
        "directory root"
    )


def adaptive_collapse_notices(
    source: Path,
    previous_selections: list[PurePosixPath],
    collapsed_directories: list[PurePosixPath],
    threshold: float,
    excluded_roots: set[PurePosixPath] | None = None,
) -> list[str]:
    return [
        directory_scope_expansion_notice(
            source,
            previous_selections,
            directory,
            "automatic collapse",
            threshold,
            excluded_roots,
        )
        for directory in collapsed_directories
    ]


def resolve_recorded_source(value: str, status_directory: Path) -> Path:
    recorded = Path(decode_frontmatter_string(value)).expanduser()
    if not recorded.is_absolute():
        recorded = status_directory / recorded
    return recorded.resolve(strict=False)


def validate_existing_status(
    source: Path,
    git_source: GitSource | None,
    output_root: Path,
) -> ExistingStatus:
    status = output_root / STATUS_FILENAME
    if not os.path.lexists(status):
        return ExistingStatus(None, False)
    if status.is_symlink() or not status.is_file():
        fail(f"status path is not a generated regular file: {status}")
    fields = read_frontmatter(status)
    if not frontmatter_is_true(fields, "whero_partial_disclosure"):
        fail(f"existing status file is not a Whero partial disclosure: {status}")

    if not fields.get("source"):
        fail(f"existing status file has no source: {status}")
    recorded_source = resolve_recorded_source(fields["source"], output_root)
    validation_mode = fields.get("source_validation", "path")
    if validation_mode == "git-commit":
        recorded_commit = decode_frontmatter_string(fields.get("source_commit", ""))
        if not recorded_commit:
            fail(f"git-commit status has no source_commit: {status}")
        if git_source is None:
            fail("existing disclosure requires a Git-controlled source")
        previous_git_path = recorded_git_path(fields, recorded_source, git_source)
        disclosed_roots = [
            PurePosixPath(path) for path in list_disclosed_symlinks(output_root)
        ]
        notice = validate_git_transition(
            git_source,
            recorded_commit.lower(),
            previous_git_path,
            disclosed_roots,
        )
        recorded_remote = decode_frontmatter_string(
            fields.get("source_git_remote_normalized", "")
        )
        current_remote = (
            git_source.remote.normalized_url if git_source.remote else ""
        )
        if recorded_remote and current_remote and recorded_remote != current_remote:
            remote_notice = (
                "Git remote metadata changed from "
                f"{recorded_remote} to {current_remote}; source identity still uses "
                "the validated commit and tree"
            )
            notice = f"{notice}\n{remote_notice}" if notice else remote_notice
        return ExistingStatus(recorded_source, recorded_source != source, notice)

    if validation_mode != "path":
        fail(f"unsupported source_validation mode: {validation_mode}")
    if recorded_source != source:
        fail(
            "existing disclosure uses a different source: "
            f"recorded {recorded_source}, supplied {source}"
        )
    return ExistingStatus(recorded_source, False)


def list_disclosed_symlinks(output_root: Path) -> list[str]:
    disclosed: list[str] = []
    for directory, dirnames, filenames in os.walk(output_root, followlinks=False):
        current = Path(directory)
        if current != output_root and (current / STATUS_FILENAME).is_file():
            dirnames[:] = []
            continue
        for name in [*dirnames, *filenames]:
            candidate = current / name
            if candidate.is_symlink():
                disclosed.append(candidate.relative_to(output_root).as_posix())
    return sorted(set(disclosed))


def nested_disclosure_roots(output_root: Path) -> set[PurePosixPath]:
    roots: set[PurePosixPath] = set()
    for directory, dirnames, filenames in os.walk(output_root, followlinks=False):
        current = Path(directory)
        if current != output_root and STATUS_FILENAME in filenames:
            roots.add(PurePosixPath(*current.relative_to(output_root).parts))
            dirnames[:] = []
    return roots


def resolved_link_target(link: Path) -> Path:
    raw_target = Path(os.readlink(link))
    if not raw_target.is_absolute():
        raw_target = link.parent / raw_target
    return raw_target.resolve(strict=False)


def refresh_source_symlinks(
    previous_source: Path,
    source: Path,
    output_root: Path,
    dry_run: bool,
) -> list[str]:
    messages: list[str] = []
    for relative_text in list_disclosed_symlinks(output_root):
        relative = PurePosixPath(relative_text)
        link = output_root.joinpath(*relative.parts)
        previous_item = previous_source.joinpath(*relative.parts).resolve(strict=False)
        try:
            source_item = source.joinpath(*relative.parts).resolve(strict=True)
        except OSError as exc:
            fail(f"relocated source item does not exist: {relative} ({exc})")
        if not is_within(source_item, source):
            fail(f"relocated source item resolves outside the source wiki: {relative}")
        actual = resolved_link_target(link)
        if actual == source_item:
            continue
        if actual != previous_item:
            fail(f"generated symlink no longer matches recorded source: {link}")

        desired_target = os.path.relpath(source_item, start=link.parent)
        if dry_run:
            messages.append(f"would relink {link} -> {desired_target}")
            continue

        temporary = link.with_name(f".{link.name}.whero-relink-{os.getpid()}")
        if os.path.lexists(temporary):
            fail(f"temporary relink path already exists: {temporary}")
        try:
            temporary.symlink_to(
                desired_target,
                target_is_directory=source_item.is_dir(),
            )
            os.replace(temporary, link)
        except OSError as exc:
            if os.path.lexists(temporary):
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            fail(f"cannot update generated symlink {link}: {exc}")
        messages.append(f"relinked {link} -> {desired_target}")
    return messages


def write_status(
    source: Path,
    git_source: GitSource | None,
    output_root: Path,
    collapse_threshold: float,
    dry_run: bool,
) -> str:
    status = output_root / STATUS_FILENAME
    if dry_run:
        action = "update" if status.exists() else "create"
        return f"would {action} status {status}"

    disclosed = list_disclosed_symlinks(output_root)
    relative_source = os.path.relpath(source, start=output_root)
    validation_mode = "git-commit" if git_source else "path"
    lines = [
        "---",
        "type: Whero Wiki Partial Disclosure",
        "title: Partial Disclosure Status",
        "description: Symlink-based partial view of selected Whero Wiki material.",
        "whero_maintenance: true",
        "whero_scope_required: true",
        "whero_partial_disclosure: true",
        f"source: {json.dumps(relative_source)}",
        f"source_validation: {validation_mode}",
    ]
    if git_source:
        lines.append(f"source_commit: {json.dumps(git_source.commit)}")
        lines.append(
            f"source_git_path: {json.dumps(git_source.wiki_path.as_posix())}"
        )
        if git_source.remote:
            lines.append(f"source_git_remote_name: {json.dumps(git_source.remote.name)}")
            lines.append(
                f"source_git_remote_url: {json.dumps(git_source.remote.fetch_url)}"
            )
            lines.append(
                "source_git_remote_normalized: "
                f"{json.dumps(git_source.remote.normalized_url)}"
            )
    delegated = sorted(path.as_posix() for path in nested_disclosure_roots(output_root))
    lines.extend([
        "layout: source-relative",
        f"view_name: {json.dumps(output_root.name)}",
        f"collapse_threshold: {collapse_threshold:g}",
        f"disclosed_symlinks: {len(disclosed)}",
        f"delegated_mounts: {len(delegated)}",
        "---",
        "",
        "# Partial Disclosure Status",
        "",
        "This directory is a partial disclosure of a source Whero Wiki.",
        "Selected and scope-required files retain their source-relative paths.",
        "The builder reconstructs this inventory from the filesystem on each run,",
        "so an interrupted status update does not prevent reading or later expansion.",
        "",
        "## Disclosed Symlink Roots",
        "",
    ])
    for path in disclosed:
        safe_path = path.replace("`", "\\`")
        lines.append(f"- `{safe_path}`")
    if delegated:
        lines.extend(["", "## Delegated Mounts", ""])
        for path in delegated:
            lines.append(f"- `{path}`")
    content = "\n".join(lines) + "\n"

    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_root,
            prefix=f".{STATUS_FILENAME}.",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_name = temporary.name
        os.replace(temporary_name, status)
    except OSError as exc:
        if temporary_name is not None:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        fail(f"cannot write disclosure status {status}: {exc}")
    return f"wrote status {status}"


def prepare_parent_directories(
    output_root: Path,
    relative: PurePosixPath,
    source: Path,
    create: bool,
    compatible_source: Path | None = None,
) -> bool:
    if os.path.lexists(output_root):
        if output_root.is_symlink():
            fail(f"disclosure root must not be a symlink: {output_root}")
        if not output_root.is_dir():
            fail(f"disclosure root is not a directory: {output_root}")
    elif create:
        output_root.mkdir(parents=True)

    current = output_root
    for index, part in enumerate(relative.parts[:-1], start=1):
        current /= part
        expected = source.joinpath(*relative.parts[:index]).resolve(strict=True)
        if os.path.lexists(current):
            if current.is_symlink():
                actual = resolved_link_target(current)
                if actual != expected:
                    compatible = (
                        compatible_source.joinpath(*relative.parts[:index]).resolve(
                            strict=False
                        )
                        if compatible_source
                        else None
                    )
                    if actual != compatible:
                        fail(f"target symlink collision: {current}")
                return False
            if not current.is_dir():
                fail(f"target path is not a directory: {current}")
        elif create:
            current.mkdir()
    return True


def expected_source_path(source: Path, relative: PurePosixPath) -> Path:
    try:
        expected = source.joinpath(*relative.parts).resolve(strict=True)
    except OSError as exc:
        fail(f"source item does not exist: {relative} ({exc})")
    if not is_within(expected, source):
        fail(f"source item resolves outside the source wiki: {relative}")
    return expected


def link_matches_source(
    link: Path,
    relative: PurePosixPath,
    source: Path,
    compatible_source: Path | None = None,
) -> bool:
    actual = resolved_link_target(link)
    if actual == expected_source_path(source, relative):
        return True
    if compatible_source is None:
        return False
    compatible = compatible_source.joinpath(*relative.parts).resolve(strict=False)
    return actual == compatible


def disclosed_selections(
    source: Path,
    output_root: Path,
    compatible_source: Path | None = None,
) -> list[PurePosixPath]:
    selections: list[PurePosixPath] = []
    for relative_text in list_disclosed_symlinks(output_root):
        relative = PurePosixPath(relative_text)
        link = output_root.joinpath(*relative.parts)
        if not link_matches_source(link, relative, source, compatible_source):
            fail(f"generated symlink does not match the active source: {link}")
        selections.append(relative)
    return collapse_selections(set(selections))


def validate_collapsible_directory(
    directory: Path,
    source: Path,
    output_root: Path,
    compatible_source: Path | None = None,
) -> None:
    pending = [directory]
    while pending:
        current = pending.pop()
        try:
            children = sorted(current.iterdir(), key=lambda path: path.name)
        except OSError as exc:
            fail(f"cannot inspect disclosure container {current}: {exc}")
        for child in children:
            relative = PurePosixPath(*child.relative_to(output_root).parts)
            if child.is_symlink():
                if not link_matches_source(
                    child,
                    relative,
                    source,
                    compatible_source,
                ):
                    fail(f"cannot collapse directory with unexpected symlink: {child}")
                continue
            if child.is_dir():
                expected = expected_source_path(source, relative)
                if not expected.is_dir():
                    fail(f"cannot collapse unexpected container directory: {child}")
                pending.append(child)
                continue
            fail(f"cannot collapse directory with non-generated content: {child}")


def collapse_directory_to_link(
    output_item: Path,
    resolved_item: Path,
    output_root: Path,
) -> str:
    try:
        backup_root = Path(
            tempfile.mkdtemp(
                prefix=".whero-collapse-",
                dir=output_root.parent,
            )
        )
    except OSError as exc:
        fail(f"cannot prepare directory collapse for {output_item}: {exc}")
    backup_item = backup_root / "previous"
    link_target = os.path.relpath(resolved_item, start=output_item.parent)
    try:
        os.replace(output_item, backup_item)
    except OSError as exc:
        try:
            shutil.rmtree(backup_root)
        except OSError:
            pass
        fail(f"cannot collapse disclosure directory {output_item}: {exc}")

    try:
        output_item.symlink_to(link_target, target_is_directory=True)
    except OSError as link_error:
        try:
            os.replace(backup_item, output_item)
        except OSError as restore_error:
            fail(
                f"cannot create collapsed link {output_item}: {link_error}; "
                f"automatic restore also failed: {restore_error}; "
                f"backup retained at {backup_item}"
            )
        try:
            shutil.rmtree(backup_root)
        except OSError:
            pass
        fail(f"cannot create collapsed link {output_item}: {link_error}")

    try:
        shutil.rmtree(backup_root)
    except OSError as exc:
        print(
            f"warning: collapsed {output_item}, but could not remove backup "
            f"{backup_root}: {exc}",
            file=sys.stderr,
        )
    return f"collapsed {output_item} -> {link_target}"


def create_link(
    source: Path,
    output_root: Path,
    relative: PurePosixPath,
    dry_run: bool,
    compatible_source: Path | None = None,
) -> str:
    source_item = source.joinpath(*relative.parts)
    try:
        resolved_item = source_item.resolve(strict=True)
    except OSError as exc:
        fail(f"source item does not exist: {relative} ({exc})")
    if not is_within(resolved_item, source):
        fail(f"source item resolves outside the source wiki: {relative}")

    output_item = output_root.joinpath(*relative.parts)
    if not prepare_parent_directories(
        output_root,
        relative,
        source,
        create=not dry_run,
        compatible_source=compatible_source,
    ):
        return f"covered by existing directory link: {output_item}"

    if os.path.lexists(output_item):
        if output_item.is_symlink():
            actual = resolved_link_target(output_item)
            if actual == resolved_item:
                return f"already linked: {output_item}"
            if compatible_source:
                compatible_item = compatible_source.joinpath(
                    *relative.parts
                ).resolve(strict=False)
                if actual == compatible_item:
                    return f"covered by planned source migration: {output_item}"
        elif output_item.is_dir() and resolved_item.is_dir():
            validate_collapsible_directory(
                output_item,
                source,
                output_root,
                compatible_source,
            )
            if dry_run:
                return f"would collapse {output_item} -> {resolved_item}"
            return collapse_directory_to_link(output_item, resolved_item, output_root)
        fail(f"target collision: {output_item}")

    if dry_run:
        return f"would link {output_item} -> {resolved_item}"

    link_target = os.path.relpath(resolved_item, start=output_item.parent)
    output_item.symlink_to(link_target, target_is_directory=resolved_item.is_dir())
    return f"linked {output_item} -> {link_target}"


def partition_mount_selections(
    requested: list[PurePosixPath],
    mounts: list[WikiMount],
    *,
    allow_plain_submodule_paths: bool,
    allow_mount_parent: bool,
) -> tuple[list[PurePosixPath], dict[WikiMount, list[PurePosixPath]]]:
    outer: list[PurePosixPath] = []
    delegated: dict[WikiMount, list[PurePosixPath]] = {}
    for selection in requested:
        descendants = [
            mount
            for mount in mounts
            if mount.path.parts[: len(selection.parts)] == selection.parts
            and mount.path != selection
        ]
        if descendants and not allow_mount_parent:
            names = ", ".join(mount.path.as_posix() for mount in descendants)
            fail(
                f"directory selection contains mounted repository boundaries: {selection} "
                f"contains [{names}]; select mount paths separately or use "
                "--allow-mount-parent to disclose them whole"
            )
        mount = mount_for_path(selection, mounts)
        if mount is None or selection == mount.path:
            outer.append(selection)
            continue
        inner = PurePosixPath(*selection.parts[len(mount.path.parts) :])
        if mount.kind not in ("whero-wiki", "partial-wiki"):
            if not allow_plain_submodule_paths:
                fail(
                    f"selection enters non-Whero submodule {mount.path}: {selection}; "
                    "select the submodule root or pass --allow-plain-submodule-paths"
                )
            outer.append(selection)
            continue
        delegated.setdefault(mount, []).append(inner)
    return collapse_selections(set(outer)), {
        mount: collapse_selections(set(paths)) for mount, paths in delegated.items()
    }


def promote_preserved_selections(
    selections: list[PurePosixPath],
    preserved: list[PreservedPath],
) -> tuple[list[PurePosixPath], dict[PurePosixPath, list[PurePosixPath]]]:
    promoted: set[PurePosixPath] = set()
    expansions: dict[PurePosixPath, list[PurePosixPath]] = {}
    for selection in selections:
        boundary = preserved_for_path(selection, preserved)
        if boundary is not None and selection != boundary.path:
            expansions.setdefault(boundary.path, []).append(selection)
            promoted.add(boundary.path)
        else:
            promoted.add(selection)
    return collapse_selections(promoted), expansions


def preserved_expansion_notices(
    expansions: dict[PurePosixPath, list[PurePosixPath]],
    *,
    label: str,
) -> list[str]:
    notices: list[str] = []
    for boundary, descendants in sorted(expansions.items(), key=lambda item: str(item[0])):
        names = ", ".join(path.as_posix() for path in sorted(descendants, key=str))
        notices.append(
            f"preserved boundary expansion ({label}): [{names}] selects whole "
            f"boundary {boundary.as_posix()}"
        )
    return notices


def run_delegated_disclosure(
    mount: WikiMount,
    selections: list[PurePosixPath],
    output_root: Path,
    collapse_threshold: float,
    dry_run: bool,
) -> str:
    mount_output_root = output_root.joinpath(*mount.path.parts)
    target_parent = mount_output_root.parent
    arguments = [
        "--source",
        str(mount.root),
        "--target",
        str(target_parent),
        "--view-name",
        mount_output_root.name,
        "--collapse-threshold",
        str(collapse_threshold),
    ]
    for selection in selections:
        arguments.extend(["--include", selection.as_posix()])
    if dry_run:
        arguments.append("--dry-run")
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            main(arguments)
    except SystemExit as exc:
        fail(
            f"delegated disclosure failed for mount {mount.path}: "
            f"{str(exc).removeprefix('error: ')}"
        )
    detail = captured.getvalue().strip().replace("\n", "; ")
    return (
        f"delegated mount {mount.path.as_posix()}: "
        f"{len(selections)} inner selection(s)"
        + (f"; {detail}" if detail and dry_run else "")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help=f"source Whero Wiki directory containing {WIKI_META_FILENAME}",
    )
    parser.add_argument(
        "--target",
        required=True,
        type=Path,
        help="parent directory for the disclosed wiki",
    )
    parser.add_argument(
        "--view-name",
        type=parse_view_name,
        help="disclosed wiki root name (default: source directory name)",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help=(
            "file or directory path; accepts source-relative, current-working-"
            "directory-relative, absolute, and user-home forms; repeat as needed"
        ),
    )
    parser.add_argument(
        "--include-from",
        action="append",
        default=[],
        type=Path,
        help="file containing selection paths, one per non-comment line",
    )
    parser.add_argument(
        "--collapse-threshold",
        default=DEFAULT_COLLAPSE_THRESHOLD,
        type=parse_collapse_threshold,
        help=(
            "recursively disclosed file percentage that selects a whole directory; "
            "accepts 80, 80%%, or 0.8; use 0 to disable (default: 80)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the plan without writing",
    )
    parser.add_argument(
        "--allow-plain-submodule-paths",
        action="store_true",
        help="permit explicit paths inside non-Whero submodules",
    )
    parser.add_argument(
        "--allow-mount-parent",
        action="store_true",
        help="permit a selected parent directory to disclose nested mounts whole",
    )
    args = parser.parse_args(argv)

    supplied_source = args.source.expanduser().absolute()
    try:
        source = supplied_source.resolve(strict=True)
    except OSError as exc:
        fail(f"cannot resolve source directory: {exc}")
    if not source.is_dir():
        fail("--source must be a directory")
    validate_wiki_meta(source)

    target_parent = args.target.expanduser().absolute()
    output_root = target_parent / (args.view_name or source.name)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output == source or is_within(resolved_output, source):
        fail("--target must not place the disclosure inside its source wiki")
    if os.path.lexists(output_root):
        if output_root.is_symlink():
            fail(f"disclosure root must not be a symlink: {output_root}")
        if not output_root.is_dir():
            fail(f"disclosure root is not a directory: {output_root}")

    git_source = git_source_identity(source)
    status_state = validate_existing_status(
        source,
        git_source,
        output_root,
    )
    requested_all = load_selections(source, args.include, args.include_from)
    mounts, preserved, preserved_problems = discover_boundaries(source)
    if preserved_problems:
        fail(preserved_problems[0])
    for entry in preserved:
        try:
            resolved_preserved = entry.root.resolve(strict=True)
        except OSError as exc:
            fail(f"declared preserved path does not exist: {entry.path} ({exc})")
        if not is_within(resolved_preserved, source):
            fail(f"preserved path resolves outside the source wiki: {entry.path}")
    requested_all, requested_preserved_expansions = promote_preserved_selections(
        requested_all,
        preserved,
    )
    requested, delegated_requests = partition_mount_selections(
        requested_all,
        mounts,
        allow_plain_submodule_paths=args.allow_plain_submodule_paths,
        allow_mount_parent=args.allow_mount_parent,
    )
    mount_roots = {mount.path for mount in mounts}
    preserved_roots = {entry.path for entry in preserved}
    protected_roots = mount_roots | preserved_roots
    compatible_source = (
        status_state.previous_source if status_state.source_moved else None
    )
    existing = disclosed_selections(source, output_root, compatible_source)
    existing, existing_preserved_expansions = promote_preserved_selections(
        existing,
        preserved,
    )
    scope_seeds = [mount.path for mount in delegated_requests]
    expanded = add_path_scope_files(
        source,
        collapse_selections(set(existing) | set(requested) | set(scope_seeds)),
        protected_roots,
    ) if requested or existing or scope_seeds else []
    expanded = [selection for selection in expanded if selection not in scope_seeds]
    pre_collapse_selections = expanded
    selections, adaptive_directories = adaptively_collapse(
        source,
        expanded,
        args.collapse_threshold,
        protected_roots,
    )
    validate_git_worktree_disclosure(
        source,
        git_source,
        collapse_selections(set(selections) | set(scope_seeds)),
    )
    notices: list[str] = []
    if status_state.git_notice:
        notices.append(status_state.git_notice)
    notices.extend(
        preserved_expansion_notices(
            requested_preserved_expansions,
            label="requested selection",
        )
    )
    notices.extend(
        preserved_expansion_notices(
            existing_preserved_expansions,
            label="existing view",
        )
    )
    notices.extend(
        adaptive_collapse_notices(
            source,
            pre_collapse_selections,
            adaptive_directories,
            args.collapse_threshold,
            protected_roots,
        )
    )
    explicit_directory_collapses = [
        selection
        for selection in selections
        if selection in requested
        and source.joinpath(*selection.parts).resolve(strict=True).is_dir()
        and any(
            existing_root.parts[: len(selection.parts)] == selection.parts
            and existing_root != selection
            for existing_root in existing
        )
    ]
    notices.extend(
        directory_scope_expansion_notice(
            source,
            existing,
            directory,
            "requested parent collapse",
            excluded_roots=protected_roots,
        )
        for directory in explicit_directory_collapses
    )

    migration_plan: list[str] = []
    if status_state.source_moved:
        assert status_state.previous_source is not None
        migration_plan = refresh_source_symlinks(
            status_state.previous_source,
            source,
            output_root,
            True,
        )
    link_plan = [
        create_link(
            source,
            output_root,
            selection,
            True,
            compatible_source,
        )
        for selection in selections
    ]

    for notice in notices:
        print(notice)
    delegated_preflight = [
        run_delegated_disclosure(
            mount,
            inner_selections,
            output_root,
            args.collapse_threshold,
            True,
        )
        for mount, inner_selections in delegated_requests.items()
    ]
    for notice in delegated_preflight:
        print(notice)
    if args.dry_run:
        planned_links = sum(
            message.startswith(("would link ", "would collapse "))
            for message in link_plan
        )
        status_action = write_status(
            source,
            git_source,
            output_root,
            args.collapse_threshold,
            True,
        )
        print(
            f"dry-run summary: {planned_links} link/collapse action(s), "
            f"{len(migration_plan)} source relink(s), "
            f"{len(delegated_preflight)} delegated mount(s), {status_action}"
        )
        return 0

    mutated = False
    migration_complete = not status_state.source_moved
    try:
        if status_state.source_moved:
            assert status_state.previous_source is not None
            migration_messages = refresh_source_symlinks(
                status_state.previous_source,
                source,
                output_root,
                False,
            )
            migration_complete = True
            mutated = mutated or bool(migration_messages)
            if migration_messages:
                print(
                    f"source relocation: updated {len(migration_messages)} "
                    "generated symlink(s)"
                )

        for selection in selections:
            message = create_link(source, output_root, selection, False)
            if message.startswith("linked "):
                mutated = True
            elif message.startswith("collapsed "):
                mutated = True
        for mount, inner_selections in delegated_requests.items():
            notice = run_delegated_disclosure(
                mount,
                inner_selections,
                output_root,
                args.collapse_threshold,
                False,
            )
            mutated = True
            print(notice)
        write_status(
            source,
            git_source,
            output_root,
            args.collapse_threshold,
            False,
        )
    except (SystemExit, OSError) as operation_error:
        if mutated and migration_complete:
            try:
                disclosed_selections(source, output_root)
                recovery = write_status(
                    source,
                    git_source,
                    output_root,
                    args.collapse_threshold,
                    False,
                )
                print(
                    f"warning: recovered disclosure status after failure: {recovery}",
                    file=sys.stderr,
                )
            except (SystemExit, OSError) as recovery_error:
                print(
                    "warning: disclosure links remain readable, but status recovery "
                    f"failed: {recovery_error}",
                    file=sys.stderr,
                )
        if isinstance(operation_error, SystemExit):
            raise
        fail(f"cannot update disclosure: {operation_error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
