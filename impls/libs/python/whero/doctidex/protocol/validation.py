from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from whero.doctidex.errors import DoctidexError

from .constants import INDEX_NAME, LOG_NAME, MOUNT_EXCLUDE
from .document import DoctidexDocument, MarkdownLink, markdown_links
from .mounts import read_mounts
from .paths import internal_to_filesystem, normalize_internal_path
from .tree import RootContext, inspect_path, matching_filters, validate_filter_conditions, walk_content


def validate_protocol(context: RootContext) -> dict[str, Any]:
    root = context.root
    findings: list[dict[str, Any]] = []
    semantic: list[dict[str, Any]] = []

    _validate_document_markers(context.index, "index", findings)
    doctidex = context.index.doctidex
    if not doctidex or doctidex.get("root") is not True:
        findings.append(_finding("root_marker", context.index.path, "Root index.md must declare doctidex.root: true."))
    if not _has_mount_exclude(context.index):
        findings.append(
            _finding("mount_exclude", context.index.path, f"Root excludes must contain path: {MOUNT_EXCLUDE}.")
        )

    documents: dict[Path, DoctidexDocument] = {context.index.path: context.index}
    _validate_atomic_entries(context, findings)
    for path in walk_content(root, context):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".md" and path.name not in {INDEX_NAME, LOG_NAME}:
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            _validate_links(context, path, markdown_links(content), findings)
            continue
        if path.name not in {INDEX_NAME, LOG_NAME}:
            continue
        if path == context.index.path:
            continue
        try:
            document = DoctidexDocument.load(path)
        except DoctidexError as exc:
            findings.extend(exc.as_result(str(root))["findings"])
            continue
        documents[path] = document
        expected = "index" if path.name == INDEX_NAME else "log"
        _validate_document_markers(document, expected, findings)
        _validate_links(context, document.path, document.links(), findings)
        findings.extend(validate_filter_conditions(document) if expected == "index" else [])
        _validate_continuity(root, path, expected, findings)

    findings.extend(validate_filter_conditions(context.index))
    _validate_links(context, context.index.path, context.index.links(), findings)
    try:
        mounts = read_mounts(context.index)
    except DoctidexError as exc:
        findings.extend(exc.as_result(str(root))["findings"])
        mounts = []

    for document in documents.values():
        if document.path.name != INDEX_NAME:
            continue
        semantic.extend(_index_candidates(context, document))
        if document.path != context.index.path and document.doctidex and "mounts" in document.doctidex:
            findings.append(
                _finding("mounts_on_non_root", document.path, "Only the root index.md may declare doctidex.mounts.")
            )

    return {
        "protocol_structure": "fail" if any(item.get("severity") == "error" for item in findings) else "pass",
        "semantic_review": "required" if semantic else "clear",
        "findings": findings,
        "semantic_candidates": semantic,
        "mount_count": len(mounts),
    }


def _validate_document_markers(document: DoctidexDocument, expected: str, findings: list[dict[str, Any]]) -> None:
    if document.data.get("type") != expected:
        findings.append(_finding("top_level_type", document.path, f"Top-level type must be {expected}."))
    doctidex = document.doctidex
    if not doctidex or doctidex.get("type") != expected:
        findings.append(_finding("doctidex_type", document.path, f"doctidex.type must be {expected}."))


def _validate_continuity(root: Path, path: Path, kind: str, findings: list[dict[str, Any]]) -> None:
    name = INDEX_NAME if kind == "index" else LOG_NAME
    current = path.parent.parent
    while current == root or root in current.parents:
        if not (current / name).is_file():
            findings.append(_finding(f"{kind}_continuity", path, f"Ancestor directory {current} is missing {name}."))
            return
        if current == root:
            return
        current = current.parent


def _has_mount_exclude(document: DoctidexDocument) -> bool:
    doctidex = document.doctidex or {}
    excludes = doctidex.get("excludes", [])
    return isinstance(excludes, list) and any(
        isinstance(item, dict) and item.get("path") == MOUNT_EXCLUDE for item in excludes
    )


def _validate_links(
    context: RootContext,
    document_path: Path,
    links: list[MarkdownLink],
    findings: list[dict[str, Any]],
) -> None:
    document_relative = document_path.parent.relative_to(context.root).as_posix()
    for link in links:
        parsed = urlsplit(link.target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        raw_path = unquote(parsed.path)
        candidate = raw_path if raw_path.startswith("/") else f"/{document_relative}/{raw_path}"
        try:
            normalize_internal_path(candidate)
        except DoctidexError:
            findings.append(
                _finding("link_path_escape", document_path, f"Link crosses its doctidex link root: {link.target}")
            )


def _validate_atomic_entries(context: RootContext, findings: list[dict[str, Any]]) -> None:
    for directory, dirnames, _ in os.walk(context.root, followlinks=False):
        current = Path(directory)
        retained: list[str] = []
        for name in dirnames:
            child = current / name
            if child.is_symlink():
                continue
            inspected = inspect_path(context, child)
            if inspected.host_scope == "excluded":
                continue
            if "atomic" in inspected.attributes:
                prohibited = sorted(
                    path for path in child.rglob("*") if path.is_file() and path.name in {INDEX_NAME, LOG_NAME}
                )
                for path in prohibited:
                    findings.append(
                        _finding("atomic_document", path, "Atomic entries must not contain index.md or log.md.")
                    )
                continue
            retained.append(name)
        dirnames[:] = retained


def _index_candidates(context: RootContext, document: DoctidexDocument) -> list[dict[str, Any]]:
    index_dir = document.path.parent
    linked: set[Path] = set()
    for link in document.links():
        target = urlsplit(link.target)
        if target.scheme or target.netloc:
            continue
        raw_path = unquote(target.path)
        if not raw_path:
            continue
        try:
            if raw_path.startswith("/"):
                resolved = internal_to_filesystem(context.root, raw_path)
            else:
                resolved = (index_dir / raw_path).resolve(strict=False)
            linked.add(resolved)
        except (DoctidexError, ValueError):
            continue

    candidates: list[dict[str, Any]] = []
    for child in _responsible_paths(context, document):
        if child.resolve(strict=False) not in linked:
            candidates.append(
                {
                    "domain": "semantic_review",
                    "severity": "info",
                    "code": "index_reference_candidate",
                    "index": str(document.path),
                    "path": str(child),
                    "message": "No machine-parsable Markdown link to this entry was found; review the index prose.",
                    "actions": [
                        "Confirm that existing prose is a recognizable index entry or add an appropriate index entry."
                    ],
                }
            )
    return candidates


def _responsible_paths(context: RootContext, document: DoctidexDocument) -> list[Path]:
    index_dir = document.path.parent
    results: list[Path] = []

    def visit(directory: Path) -> None:
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            if child == document.path or child.is_symlink():
                continue
            relative = child.relative_to(index_dir).as_posix()
            matches = matching_filters(document, relative, child.is_dir())
            attributes = {attribute for attribute, _ in matches}
            if "excluded" in attributes:
                continue
            results.append(child)
            if not child.is_dir() or "atomic" in attributes or (child / INDEX_NAME).is_file():
                continue
            visit(child)

    visit(index_dir)
    return results


def _finding(code: str, path: Path, message: str) -> dict[str, Any]:
    return {
        "domain": "protocol_structure",
        "severity": "error",
        "code": code,
        "path": str(path),
        "message": message,
        "actions": ["Correct the referenced protocol structure and rerun doctidex-git check."],
    }
