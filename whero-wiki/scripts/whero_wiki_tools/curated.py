"""Initialization and validation for Whero-maintained and curated documents."""

from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .diagnostics import Diagnostics
from .errors import WheroToolError
from .frontmatter import (
    frontmatter_is_true,
    read_frontmatter,
    read_markdown,
    scalar_text,
    write_markdown_atomic,
)
from .links import (
    HEADING_RE,
    heading_anchors,
    markdown_destinations,
    resolve_markdown_destination,
)
from .model import (
    INDEX_FILENAME,
    LOG_FILENAME,
    STATUS_FILENAME,
    CuratedCollection,
    discover_curated_collections,
    path_is_in_collection,
    require_framework_file,
    validate_wiki_root,
)
from .paths import (
    parse_relative_path,
    path_from_root,
    resolve_within,
    sha256_file,
)
from .provenance import validate_provenance


CURATION_MODES = {"adapted", "distilled", "synthesized"}
CURATION_STATUSES = {"draft", "reviewed", "needs-review", "deprecated"}
def _relative_directory(root: Path, raw: str) -> tuple[PurePosixPath | None, Path]:
    if raw.strip() in ("", "."):
        return None, root
    relative = parse_relative_path(raw, label="directory")
    directory = resolve_within(root, relative)
    if not directory.is_dir():
        raise WheroToolError(f"Wiki directory is not a directory: {relative}")
    return relative, directory


def init_index(
    raw_root: Path,
    directory_text: str,
    title: str,
    description: str,
    *,
    dry_run: bool = False,
) -> Path:
    root = validate_wiki_root(raw_root)
    _, directory = _relative_directory(root, directory_text)
    path = directory / INDEX_FILENAME
    if path.exists() or path.is_symlink():
        raise WheroToolError(f"refusing to overwrite existing index: {path}")
    fields = {
        "type": "Whero Wiki Index",
        "title": title,
        "description": description,
        "whero_maintenance": True,
        "whero_scope_required": True,
    }
    body = f"\n# {title}\n\n{description}\n"
    if not dry_run:
        write_markdown_atomic(path, fields, body)
    return path


def init_log(
    raw_root: Path,
    directory_text: str,
    title: str,
    *,
    dry_run: bool = False,
) -> Path:
    root = validate_wiki_root(raw_root)
    _, directory = _relative_directory(root, directory_text)
    path = directory / LOG_FILENAME
    if path.exists() or path.is_symlink():
        raise WheroToolError(f"refusing to overwrite existing log: {path}")
    fields = {
        "type": "Whero Wiki Log",
        "title": title,
        "whero_maintenance": True,
        "whero_scope_required": True,
    }
    body = f"\n# {title}\n\n## {date.today().isoformat()}\n\n- **Initialization**: Created this maintained log.\n"
    if not dry_run:
        write_markdown_atomic(path, fields, body)
    return path


def _body_links_to_directory(body: str, document: Path, target: Path) -> bool:
    for destination in markdown_destinations(body):
        resolved, _, _ = resolve_markdown_destination(
            document,
            destination,
            target.parent,
        )
        if resolved == target or resolved == target / INDEX_FILENAME:
            return True
    return False


def init_curated_collection(
    raw_root: Path,
    scope_text: str,
    curated_text: str,
    title: str,
    description: str,
    *,
    with_log: bool = False,
    dry_run: bool = False,
) -> Path:
    root = validate_wiki_root(raw_root)
    scope = parse_relative_path(scope_text, label="top-level scope", single_component=True)
    curated = parse_relative_path(
        curated_text,
        label="curated collection path",
        single_component=True,
    )
    scope_root = resolve_within(root, scope)
    if not scope_root.is_dir():
        raise WheroToolError(f"top-level scope is not a directory: {scope}")
    top_index = scope_root / INDEX_FILENAME
    top_document = read_markdown(top_index)
    require_framework_file(top_index)
    existing = top_document.fields.get("whero_curated_path")
    if existing is not None and scalar_text(existing) != curated.as_posix():
        raise WheroToolError(
            f"top-level index already declares a different curated path: {existing}"
        )
    collection_root = scope_root / curated.as_posix()
    if collection_root.exists() or collection_root.is_symlink():
        raise WheroToolError(f"curated collection path already exists: {collection_root}")

    top_fields = dict(top_document.fields)
    top_fields["whero_curated_path"] = curated.as_posix()
    top_body = top_document.body.rstrip() + "\n"
    if not _body_links_to_directory(top_body, top_index, collection_root):
        top_body += (
            f"\n## Agent-Curated Knowledge\n\n"
            f"[{title}]({curated.as_posix()}/) {description}\n"
        )
    collection_fields = {
        "type": "Whero Curated Collection Index",
        "title": title,
        "description": description,
        "whero_maintenance": True,
        "whero_scope_required": True,
        "whero_curated_root": True,
        "whero_curated_format_version": "0.1",
    }
    collection_body = (
        f"\n# {title}\n\n{description}\n\n"
        "Collected source snapshots remain authoritative when a curated concept "
        "is ambiguous or conflicts with source material.\n"
    )
    if dry_run:
        return collection_root

    try:
        write_markdown_atomic(
            collection_root / INDEX_FILENAME,
            collection_fields,
            collection_body,
        )
        if with_log:
            log_fields = {
                "type": "Whero Wiki Log",
                "title": f"{title} Log",
                "whero_maintenance": True,
                "whero_scope_required": True,
            }
            log_body = (
                f"\n# {title} Log\n\n## {date.today().isoformat()}\n\n"
                "- **Initialization**: Created the curated collection.\n"
            )
            write_markdown_atomic(
                collection_root / LOG_FILENAME,
                log_fields,
                log_body,
            )
        write_markdown_atomic(
            top_index,
            top_fields,
            top_body,
            overwrite=True,
        )
    except WheroToolError:
        if collection_root.exists():
            shutil.rmtree(collection_root, ignore_errors=True)
        raise
    return collection_root


def _collection_for_concept(
    relative: PurePosixPath,
    collections: Iterable[CuratedCollection],
) -> CuratedCollection:
    matches = [collection for collection in collections if path_is_in_collection(relative, collection)]
    if len(matches) != 1:
        raise WheroToolError(
            f"concept path is not inside exactly one declared curated collection: {relative}"
        )
    return matches[0]


def _is_project_wiki(root: Path) -> bool:
    return frontmatter_is_true(
        read_frontmatter(root / "whero-wiki-meta.md"),
        "whero_project_wiki",
    )


def init_curated_concept(
    raw_root: Path,
    concept_text: str,
    concept_type: str,
    title: str,
    description: str,
    curation_mode: str,
    source_values: list[str],
    *,
    provenance: list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    status: str = "draft",
    dry_run: bool = False,
) -> Path:
    root = validate_wiki_root(raw_root)
    concept = parse_relative_path(concept_text, label="concept path")
    if concept.suffix.lower() != ".md" or concept.name in (INDEX_FILENAME, LOG_FILENAME):
        raise WheroToolError("concept path must name a non-reserved Markdown file")
    if curation_mode not in CURATION_MODES:
        raise WheroToolError(f"unsupported curation mode: {curation_mode}")
    if status not in CURATION_STATUSES:
        raise WheroToolError(f"unsupported curation status: {status}")
    collections, problems = discover_curated_collections(root)
    if problems:
        raise WheroToolError(problems[0])
    if not _is_project_wiki(root):
        _collection_for_concept(concept, collections)
    output = path_from_root(root, concept)
    if output.exists() or output.is_symlink():
        raise WheroToolError(f"refusing to overwrite existing concept: {output}")
    if not source_values and not provenance:
        raise WheroToolError("provide at least one source or provenance entry")

    sources: list[dict[str, str]] = []
    for source_text in source_values:
        source = parse_relative_path(source_text, label="source document")
        if any(path_is_in_collection(source, collection) for collection in collections):
            raise WheroToolError(
                f"source_documents must point to collected source snapshots: {source}"
            )
        source_path = resolve_within(root, source)
        if not source_path.is_file():
            raise WheroToolError(f"source document is not a regular file: {source}")
        sources.append({"path": source.as_posix(), "sha256": sha256_file(source_path)})

    fields: dict[str, Any] = {
        "type": concept_type,
        "title": title,
        "description": description,
        "whero_maintenance": True,
        "whero_curated": True,
        "curation_mode": curation_mode,
        "curation_status": status,
    }
    if sources:
        fields["source_documents"] = sources
    if provenance:
        fields["provenance"] = provenance
    if tags:
        fields["tags"] = tags
    fields["timestamp"] = date.today().isoformat()
    body = f"\n# {title}\n\n{description}\n"
    if not dry_run:
        write_markdown_atomic(output, fields, body)
    return output


def record_source_digests(
    raw_root: Path,
    concept_text: str,
    *,
    status: str | None = None,
    dry_run: bool = False,
) -> Path:
    root = validate_wiki_root(raw_root)
    concept = parse_relative_path(concept_text, label="concept path")
    concept_path = resolve_within(root, concept)
    document = read_markdown(concept_path)
    if not frontmatter_is_true(document.fields, "whero_curated"):
        raise WheroToolError(f"not a curated concept: {concept}")
    if status is not None and status not in CURATION_STATUSES:
        raise WheroToolError(f"unsupported curation status: {status}")
    sources = document.fields.get("source_documents")
    if not isinstance(sources, list) or not sources:
        raise WheroToolError(f"curated concept has no source_documents: {concept}")
    updated_sources: list[dict[str, Any]] = []
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise WheroToolError(f"invalid source_documents entry in {concept}")
        source = parse_relative_path(item["path"], label="source document")
        source_path = resolve_within(root, source)
        updated = dict(item)
        updated["sha256"] = sha256_file(source_path)
        updated_sources.append(updated)
    fields = dict(document.fields)
    fields["source_documents"] = updated_sources
    if status is not None:
        fields["curation_status"] = status
    fields["timestamp"] = date.today().isoformat()
    if not dry_run:
        write_markdown_atomic(concept_path, fields, document.body, overwrite=True)
    return concept_path


def _validate_local_links(
    root: Path,
    document: Path,
    body: str,
    diagnostics: Diagnostics,
    available: bool,
) -> set[Path]:
    resolved_targets: set[Path] = set()
    for destination in markdown_destinations(body):
        target, fragment, kind = resolve_markdown_destination(
            document,
            destination,
            root,
        )
        if kind == "external":
            continue
        if kind in ("invalid", "cross-boundary"):
            diagnostics.error(
                "LOCAL_LINK_INVALID",
                f"local Markdown target crosses its Wiki boundary: {destination}",
                document,
            )
            continue
        if not target.exists():
            reporter = diagnostics.notice if available else diagnostics.error
            reporter(
                "LOCAL_LINK_UNAVAILABLE" if available else "LOCAL_LINK_MISSING",
                f"local Markdown target is unavailable: {destination}",
                document,
            )
            continue
        resolved_targets.add(target)
        anchor_target = target / INDEX_FILENAME if target.is_dir() else target
        if fragment and anchor_target.is_file() and fragment not in heading_anchors(anchor_target):
            diagnostics.error(
                "LOCAL_LINK_ANCHOR",
                f"Markdown anchor does not exist: {destination}",
                document,
            )
    return resolved_targets


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timestamp_is_valid(value: Any) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False


def _validate_concept(
    root: Path,
    concept: Path,
    collections: list[CuratedCollection],
    diagnostics: Diagnostics,
    available: bool,
    strict_stale: bool,
    collection_root: Path | None = None,
) -> None:
    try:
        document = read_markdown(concept)
    except WheroToolError as exc:
        diagnostics.error("CURATED_FRONTMATTER", str(exc), concept)
        return
    fields = document.fields
    for key in ("type", "title", "description"):
        if not _is_nonempty_string(fields.get(key)):
            diagnostics.error("CURATED_REQUIRED_FIELD", f"missing non-empty {key}", concept)
    if not frontmatter_is_true(fields, "whero_maintenance"):
        diagnostics.error(
            "CURATED_MAINTENANCE",
            "curated concept must set whero_maintenance: true",
            concept,
        )
    if not frontmatter_is_true(fields, "whero_curated"):
        diagnostics.error(
            "CURATED_MARKER",
            "curated concept must set whero_curated: true",
            concept,
        )
    if frontmatter_is_true(fields, "whero_scope_required"):
        diagnostics.error(
            "CURATED_SCOPE_REQUIRED",
            "curated concepts must not set whero_scope_required: true",
            concept,
        )
    mode = scalar_text(fields.get("curation_mode"))
    if mode not in CURATION_MODES:
        diagnostics.error("CURATED_MODE", f"unsupported curation_mode: {mode!r}", concept)
    status = scalar_text(fields.get("curation_status"))
    if status not in CURATION_STATUSES:
        diagnostics.error(
            "CURATED_STATUS",
            f"unsupported curation_status: {status!r}",
            concept,
        )
    elif status in ("draft", "needs-review"):
        diagnostics.warning(
            "CURATED_REVIEW_STATUS",
            f"concept remains {status}",
            concept,
        )
    if not _timestamp_is_valid(fields.get("timestamp")):
        diagnostics.error("CURATED_TIMESTAMP", "missing or invalid timestamp", concept)
    if collection_root is not None:
        relative_parent = concept.parent.relative_to(collection_root)
        depth = 1 + len(relative_parent.parts)
        if depth > 3:
            diagnostics.warning(
                "CURATED_DEPTH",
                f"curated concept is at depth {depth}; justify depth beyond three levels",
                concept,
            )

    sources = fields.get("source_documents")
    if isinstance(sources, list):
        for item in sources:
            if not isinstance(item, dict):
                continue
            try:
                source = parse_relative_path(
                    scalar_text(item.get("path")),
                    label="source document",
                )
            except WheroToolError:
                continue
            if any(path_is_in_collection(source, collection) for collection in collections):
                diagnostics.error(
                    "CURATED_SOURCE_IS_CURATED",
                    f"source_documents must point to collected sources: {source}",
                    concept,
                )
    validate_provenance(
        root,
        concept,
        fields,
        diagnostics,
        available=available,
        strict_stale=strict_stale,
    )

    title = scalar_text(fields.get("title"))
    first_heading = HEADING_RE.search(document.body)
    if title and (first_heading is None or first_heading.group(1).strip() != title):
        diagnostics.error(
            "CURATED_TITLE_HEADING",
            "first Markdown heading must match the frontmatter title",
            concept,
        )
    _validate_local_links(root, concept, document.body, diagnostics, available)


def validate_wiki(
    raw_root: Path,
    *,
    mode: str = "auto",
    strict_stale: bool = False,
) -> Diagnostics:
    if mode not in ("auto", "full", "available"):
        raise WheroToolError(f"unsupported validation mode: {mode}")
    candidate_root = raw_root.expanduser().resolve(strict=False)
    available = mode == "available" or (
        mode == "auto" and (candidate_root / STATUS_FILENAME).is_file()
    )
    root = validate_wiki_root(raw_root, allow_symlink_meta=available)
    diagnostics = Diagnostics(root)
    project_wiki = _is_project_wiki(root)
    collections, discovery_problems = discover_curated_collections(root)
    for problem in discovery_problems:
        diagnostics.error("CURATED_DECLARATION", problem)

    declared_roots = {collection.root.resolve(strict=False) for collection in collections}
    top_indexes = {collection.top_index for collection in collections}
    from .mounts import walk_owned_files

    owned_markdown = [
        path for path in walk_owned_files(root) if path.suffix.lower() == ".md"
    ]
    project_indexed_targets: set[Path] = set()
    for candidate in (path for path in owned_markdown if path.name == INDEX_FILENAME):
        try:
            fields = read_frontmatter(candidate)
        except WheroToolError as exc:
            diagnostics.error("INDEX_FRONTMATTER", str(exc), candidate)
            continue
        if frontmatter_is_true(fields, "whero_curated_root"):
            if (
                candidate.parent.resolve(strict=False) not in declared_roots
                and not (project_wiki and candidate == root / INDEX_FILENAME)
            ):
                diagnostics.error(
                    "CURATED_ROOT_UNDECLARED",
                    "curated root is not declared by a top-level index",
                    candidate,
                )

    for maintained in owned_markdown:
        try:
            document = read_markdown(maintained)
        except WheroToolError as exc:
            if maintained.name in (INDEX_FILENAME, LOG_FILENAME):
                diagnostics.error("FRAMEWORK_FRONTMATTER", str(exc), maintained)
            continue
        fields = document.fields
        if frontmatter_is_true(fields, "whero_scope_required") and not frontmatter_is_true(
            fields, "whero_maintenance"
        ):
            diagnostics.error(
                "SCOPE_REQUIRED_MAINTENANCE",
                "scope-required file must set whero_maintenance: true",
                maintained,
            )
        if frontmatter_is_true(fields, "whero_maintenance"):
            inside_curated = any(
                maintained == collection.root
                or collection.root in maintained.parents
                for collection in collections
            )
            if maintained not in top_indexes and not inside_curated:
                linked = _validate_local_links(
                    root,
                    maintained,
                    document.body,
                    diagnostics,
                    available,
                )
                if project_wiki and maintained.name == INDEX_FILENAME:
                    project_indexed_targets.update(linked)

    for collection in collections:
        try:
            top_fields = require_framework_file(
                collection.top_index,
                allow_symlink=available,
            )
        except WheroToolError as exc:
            diagnostics.error("CURATED_TOP_INDEX", str(exc), collection.top_index)
            top_fields = {}
        if not collection.root.is_dir():
            reporter = diagnostics.notice if available else diagnostics.error
            reporter(
                "CURATED_COLLECTION_UNAVAILABLE" if available else "CURATED_COLLECTION_MISSING",
                f"declared curated collection is unavailable: {collection.relative_root}",
                collection.top_index,
            )
            continue
        try:
            collection_fields = require_framework_file(
                collection.collection_index,
                allow_symlink=available,
            )
        except WheroToolError as exc:
            diagnostics.error(
                "CURATED_COLLECTION_INDEX",
                str(exc),
                collection.collection_index,
            )
            collection_fields = {}
        if collection_fields and not frontmatter_is_true(
            collection_fields, "whero_curated_root"
        ):
            diagnostics.error(
                "CURATED_ROOT_MARKER",
                "collection index must set whero_curated_root: true",
                collection.collection_index,
            )
        if scalar_text(collection_fields.get("whero_curated_format_version")) != "0.1":
            diagnostics.error(
                "CURATED_FORMAT_VERSION",
                'collection index must set whero_curated_format_version: "0.1"',
                collection.collection_index,
            )
        if top_fields:
            try:
                top_document = read_markdown(collection.top_index)
                linked = _validate_local_links(
                    root,
                    collection.top_index,
                    top_document.body,
                    diagnostics,
                    available,
                )
                if collection.root.resolve(strict=False) not in linked and collection.collection_index.resolve(
                    strict=False
                ) not in linked:
                    diagnostics.error(
                        "CURATED_TOP_INDEX_LINK",
                        "top-level index body must link the declared curated collection",
                        collection.top_index,
                    )
            except WheroToolError as exc:
                diagnostics.error("CURATED_TOP_INDEX", str(exc), collection.top_index)

        indexed_targets: set[Path] = set()
        for index in collection.root.rglob(INDEX_FILENAME):
            try:
                index_fields = require_framework_file(index, allow_symlink=available)
                if not index_fields:
                    continue
                index_document = read_markdown(index)
            except WheroToolError as exc:
                diagnostics.error("CURATED_INDEX", str(exc), index)
                continue
            indexed_targets.update(
                _validate_local_links(
                    root,
                    index,
                    index_document.body,
                    diagnostics,
                    available,
                )
            )
        for log in collection.root.rglob(LOG_FILENAME):
            try:
                require_framework_file(log, allow_symlink=available)
            except WheroToolError as exc:
                diagnostics.error("CURATED_LOG", str(exc), log)

        concepts = sorted(
            path
            for path in collection.root.rglob("*.md")
            if path.name not in (INDEX_FILENAME, LOG_FILENAME)
        )
        for concept in concepts:
            _validate_concept(
                root,
                concept,
                collections,
                diagnostics,
                available,
                strict_stale,
                collection.root,
            )
            if concept.resolve(strict=False) not in indexed_targets:
                diagnostics.error(
                    "CURATED_INDEX_COVERAGE",
                    "curated concept is not linked from a collection index",
                    concept,
                )
    if project_wiki:
        for concept in owned_markdown:
            if concept.name in (INDEX_FILENAME, LOG_FILENAME, "whero-wiki-meta.md"):
                continue
            try:
                fields = read_frontmatter(concept)
            except WheroToolError:
                continue
            if frontmatter_is_true(fields, "whero_curated") and not any(
                collection.root == concept.parent or collection.root in concept.parents
                for collection in collections
            ):
                _validate_concept(
                    root,
                    concept,
                    collections,
                    diagnostics,
                    available,
                    strict_stale,
                    root,
                )
                if concept.resolve(strict=False) not in project_indexed_targets:
                    diagnostics.error(
                        "CURATED_INDEX_COVERAGE",
                        "project concept is not linked from a maintained index",
                        concept,
                    )
    return diagnostics
