from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from whero.doctidex.errors import DoctidexError

from .constants import INDEX_NAME, LOG_NAME, MOUNT_EXCLUDE
from .document import DoctidexDocument
from .mounts import read_mounts
from .paths import filesystem_to_internal, mount_for_path
from .regex import DoctidexPattern, RegexCompileError


@dataclass(frozen=True, slots=True)
class RootContext:
    root: Path
    index: DoctidexDocument


@dataclass(slots=True)
class PathContext:
    host_root: Path
    path: Path
    internal_path: str
    source: str = "local"
    host_scope: str = "included"
    attributes: list[str] = field(default_factory=list)
    responsible_index: Path | None = None
    applicable_log: Path | None = None
    boundary_index: Path | None = None
    boundary_condition: dict[str, str] | None = None
    mount_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "host_root": str(self.host_root),
            "path": str(self.path),
            "internal_path": self.internal_path,
            "source": self.source,
            "host_scope": self.host_scope,
            "attributes": sorted(set(self.attributes)),
            "responsible_index": str(self.responsible_index) if self.responsible_index else None,
            "applicable_log": str(self.applicable_log) if self.applicable_log else None,
            "boundary_index": str(self.boundary_index) if self.boundary_index else None,
            "boundary_condition": self.boundary_condition,
            "mount_path": self.mount_path,
        }


def discover_roots(path: Path) -> list[RootContext]:
    current = Path(os.path.abspath(path))
    if current.is_file() or (not current.exists() and current.suffix):
        current = current.parent
    contexts: list[RootContext] = []
    for directory in (current, *current.parents):
        index_path = directory / INDEX_NAME
        if not index_path.is_file():
            continue
        try:
            document = DoctidexDocument.load(index_path)
        except DoctidexError:
            continue
        if document.is_root:
            contexts.append(RootContext(directory, document))
    return contexts


def require_root(path: Path, *, operation: str) -> RootContext:
    roots = discover_roots(path)
    if not roots:
        raise DoctidexError(
            f"No doctidex root contains {path}.",
            operation=operation,
            affected=[str(path)],
            actions=["Run doctidex-git init for the intended root or pass a path inside an existing root."],
            code="root_not_found",
        )
    exact_directory = Path(os.path.abspath(path))
    if exact_directory.is_file():
        exact_directory = exact_directory.parent
    exact = [root for root in roots if root.root == exact_directory]
    if len(exact) == 1:
        return exact[0]
    if len(roots) > 1:
        raise DoctidexError(
            f"More than one doctidex root contains {path}.",
            operation=operation,
            affected=[str(root.root) for root in roots],
            actions=["Retry with the exact doctidex root path."],
            requires_user="doctidex_root",
            code="root_ambiguous",
        )
    return roots[0]


def inspect_path(context: RootContext, path: Path) -> PathContext:
    root = Path(os.path.abspath(context.root))
    resolved = Path(os.path.abspath(path))
    internal = filesystem_to_internal(root, resolved)
    mounts = read_mounts(context.index)
    matched_mount = mount_for_path(internal, [mount.mount_path for mount in mounts])
    if matched_mount:
        return PathContext(
            host_root=root,
            path=resolved,
            internal_path=internal,
            source="mount",
            host_scope="excluded",
            attributes=["excluded", "mount"],
            boundary_index=context.index.path,
            boundary_condition={"path": MOUNT_EXCLUDE},
            mount_path=matched_mount,
        )

    relative = resolved.relative_to(root)
    active_index = context.index
    active_dir = root
    attributes: list[str] = []
    boundary: tuple[Path, dict[str, str]] | None = None
    parts = relative.parts

    for offset in range(len(parts)):
        target = root.joinpath(*parts[: offset + 1])
        rel_to_index = target.relative_to(active_dir).as_posix()
        matched = matching_filters(active_index, rel_to_index, target.is_dir())
        attributes.extend(item[0] for item in matched)
        excluded = next((item for item in matched if item[0] == "excluded"), None)
        if excluded:
            boundary = (active_index.path, excluded[1])
            break
        if "atomic" not in attributes and target.is_dir() and (target / INDEX_NAME).is_file():
            try:
                active_index = DoctidexDocument.load(target / INDEX_NAME)
                active_dir = target
            except DoctidexError:
                # Validation reports the malformed child index; its parent remains responsible
                # for deterministic traversal until the file can be parsed.
                pass

    if boundary:
        return PathContext(
            host_root=root,
            path=resolved,
            internal_path=internal,
            host_scope="excluded",
            attributes=attributes,
            boundary_index=boundary[0],
            boundary_condition=boundary[1],
        )

    applicable_log = _nearest_file(resolved if resolved.is_dir() else resolved.parent, root, LOG_NAME)
    return PathContext(
        host_root=root,
        path=resolved,
        internal_path=internal,
        attributes=attributes,
        responsible_index=active_index.path,
        applicable_log=applicable_log,
    )


def matching_filters(
    index: DoctidexDocument,
    relative_path: str,
    is_directory: bool,
) -> list[tuple[str, dict[str, str]]]:
    doctidex = index.doctidex or {}
    matches: list[tuple[str, dict[str, str]]] = []
    mapping = {
        "atomic_entries": "atomic",
        "excludes": "excluded",
        "protected": "protected",
    }
    for field_name, attribute in mapping.items():
        raw_conditions = doctidex.get(field_name, [])
        if not isinstance(raw_conditions, list):
            continue
        for raw in raw_conditions:
            if not isinstance(raw, dict) or len(raw) != 1:
                continue
            condition = {str(key): str(value) for key, value in raw.items()}
            if attribute == "atomic" and not is_directory:
                continue
            if _condition_matches(condition, relative_path):
                matches.append((attribute, condition))
    if any(attribute == "excluded" for attribute, _ in matches):
        return [(attribute, condition) for attribute, condition in matches if attribute == "excluded"]
    return matches


def validate_filter_conditions(document: DoctidexDocument) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    doctidex = document.doctidex
    if not doctidex:
        return findings
    for field_name in ("atomic_entries", "excludes", "protected"):
        conditions = doctidex.get(field_name, [])
        if conditions is None:
            continue
        if not isinstance(conditions, list):
            findings.append(_finding("error", "filter_not_list", document.path, f"doctidex.{field} must be a list."))
            continue
        for position, condition in enumerate(conditions):
            location = f"{document.path}:doctidex.{field_name}[{position}]"
            if not isinstance(condition, dict) or len(condition) != 1:
                findings.append(
                    _finding("error", "filter_shape", location, "Filter must contain exactly one path or regex field.")
                )
                continue
            key, value = next(iter(condition.items()))
            if key not in {"path", "regex"} or not isinstance(value, str) or not value:
                findings.append(
                    _finding(
                        "error", "filter_value", location, "Filter must contain one non-empty path or regex string."
                    )
                )
                continue
            if key == "path":
                if value.startswith("/") or ".." in Path(value).parts:
                    findings.append(
                        _finding(
                            "error",
                            "filter_path",
                            location,
                            "Filter path must be relative and remain inside the doctidex root.",
                        )
                    )
                continue
            try:
                DoctidexPattern(value)
            except RegexCompileError as exc:
                findings.append(
                    _finding("error", "filter_regex", location, f"Regex VERSION1 pattern is invalid: {exc}.")
                )
    return findings


def walk_content(root: Path, context: RootContext | None = None) -> Iterable[Path]:
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        retained: list[str] = []
        for name in dirnames:
            child = current / name
            if child.is_symlink():
                continue
            if context is not None:
                inspected = inspect_path(context, child)
                if inspected.host_scope == "excluded" or "atomic" in inspected.attributes:
                    continue
            retained.append(name)
        dirnames[:] = retained
        for name in sorted(dirnames):
            yield current / name
        for name in sorted(filenames):
            yield current / name


def _condition_matches(condition: dict[str, str], relative_path: str) -> bool:
    key, value = next(iter(condition.items()))
    candidates = _path_prefixes(relative_path)
    if key == "path":
        normalized = value.strip("/")
        return any(candidate == normalized for candidate in candidates)
    pattern = DoctidexPattern(value)
    return any(pattern.search(candidate) for candidate in candidates)


def _path_prefixes(value: str) -> list[str]:
    parts = [part for part in value.split("/") if part]
    return ["/".join(parts[:index]) for index in range(1, len(parts) + 1)]


def _nearest_file(start: Path, root: Path, name: str) -> Path | None:
    current = start
    while True:
        candidate = current / name
        if candidate.is_file():
            return candidate
        if current == root:
            return None
        current = current.parent


def _finding(severity: str, code: str, path: Path | str, message: str) -> dict[str, Any]:
    return {
        "domain": "protocol_structure",
        "severity": severity,
        "code": code,
        "path": str(path),
        "message": message,
        "actions": ["Correct the referenced structure and rerun doctidex-git check."],
    }
