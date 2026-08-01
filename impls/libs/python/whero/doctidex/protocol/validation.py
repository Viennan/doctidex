from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from ruamel.yaml import YAML

from whero.doctidex.errors import DoctidexError
from whero.doctidex.results import envelope, finding, paginate_lists, query_identity

from .document import DoctidexDocument, markdown_links
from .root import RootContext, is_within

_CONFIG_FIELDS = ("boundary-set", "atomic-indexing", "unsafe")
_COMMENT = re.compile(r"\s*<!--(.*?)-->", re.DOTALL)


@dataclass(slots=True)
class IndexInfo:
    directory: Path
    document: DoctidexDocument
    entries: dict[str, list[Path]] = field(default_factory=lambda: {name: [] for name in _CONFIG_FIELDS})


@dataclass(frozen=True, slots=True)
class LinkFact:
    target: Path | None
    valid_edge: bool


def validate_protocol(
    context: RootContext,
    *,
    scopes: list[str] | None = None,
    limit: int = 100,
    cursor: str | None = None,
) -> dict[str, Any]:
    normalized_scopes = normalize_scopes(context.root, scopes or ["/"])
    coverage = "full" if normalized_scopes == ["/"] else "scoped"
    engine = _Validator(context, normalized_scopes)
    findings, semantic = engine.run()
    findings = _filter_scope(findings, context.root, normalized_scopes, engine.indexes, engine.support_paths)
    semantic = _filter_scope(semantic, context.root, normalized_scopes, engine.indexes, engine.support_paths)
    findings.sort(key=_item_sort_key)
    semantic.sort(key=_item_sort_key)

    identity = query_identity("validate", root=str(context.root), scopes=normalized_scopes, limit=limit)
    state = engine.fingerprint()
    try:
        pages, collection = paginate_lists(
            {"findings": findings, "semantic_candidates": semantic},
            limit=limit,
            identity=identity,
            state=state,
            cursor=cursor,
        )
    except ValueError as exc:
        raise DoctidexError(
            "The validation cursor no longer identifies the same root state and scope.",
            operation="validate",
            affected=[str(context.root)],
            actions=["Restart validation from the first page."],
            code="cursor_invalid",
            path=str(context.root),
        ) from exc

    protocol_fail = any(item["severity"] == "error" for item in findings)
    semantic_required = bool(semantic)
    return envelope(
        "validate",
        status="warning" if protocol_fail else "ok",
        result=(
            "Validation completed with protocol findings."
            if protocol_fail
            else "Validation completed for the requested coverage."
        ),
        root=str(context.root),
        findings=pages["findings"],
        collection=collection,
        coverage=coverage,
        scopes=normalized_scopes,
        protocol_structure="fail" if protocol_fail else "pass",
        scan_complete=engine.scan_complete,
        semantic_review="required" if semantic_required else "clear",
        semantic_candidates=pages["semantic_candidates"],
    )


def normalize_scopes(root: Path, values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not value.startswith("/") or "#" in value:
            _scope_error(root, value)
        parts: list[str] = []
        for part in value.split("/"):
            if part in {"", "."}:
                continue
            if part == "..":
                if not parts:
                    _scope_error(root, value)
                parts.pop()
            else:
                parts.append(part)
        internal = "/" + "/".join(parts) if parts else "/"
        target = root.joinpath(*parts)
        if not target.is_dir() or not os.access(target, os.R_OK):
            _scope_error(root, value)
        normalized.append(internal)
    retained: list[str] = []
    for value in sorted(set(normalized), key=lambda item: (item.count("/"), item)):
        if any(value == parent or value.startswith(parent.rstrip("/") + "/") for parent in retained):
            continue
        retained.append(value)
    return sorted(retained)


class _Validator:
    def __init__(self, context: RootContext, scopes: list[str]) -> None:
        self.context = context
        self.root = context.root
        self.scope_paths = (
            None if scopes == ["/"] else [self.root.joinpath(*value.lstrip("/").split("/")) for value in scopes]
        )
        self.findings: list[dict[str, Any]] = []
        self.semantic: list[dict[str, Any]] = []
        self.indexes: dict[Path, IndexInfo] = {}
        self.markdown: dict[Path, str] = {}
        self.paths: set[Path] = set()
        self.support_paths: set[Path] = set()
        self.scan_complete = True

    def run(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        self._scan()
        self._validate_indexes()
        self._validate_configs()
        self._validate_atomic_and_logs()
        edges = self._validate_links()
        self._validate_reachability(edges)
        return self.findings, self.semantic

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        for path in sorted(self.paths, key=lambda item: item.as_posix()):
            try:
                stat = path.lstat()
                relative = path.relative_to(self.root).as_posix()
                digest.update(f"{relative}\0{stat.st_mode}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
            except OSError:
                digest.update(f"missing:{path}\n".encode())
        return digest.hexdigest()

    def _scan(self) -> None:
        if self.scope_paths is None:
            self._scan_tree(self.root)
        else:
            for scope in self.scope_paths:
                self._scan_tree(scope)
                current = scope
                while True:
                    self.paths.add(current)
                    index = current / "index.md"
                    if index.is_file():
                        self._read_markdown(index, support=True)
                    if current == self.root:
                        break
                    current = current.parent
            self._scan_navigation_support()

        self.indexes.setdefault(self.root, IndexInfo(self.root, self.context.index))
        self.paths.add(self.context.index.path)

    def _scan_tree(self, start: Path) -> None:
        for directory, dirnames, filenames in os.walk(start, followlinks=False):
            current = Path(directory)
            all_directories = sorted(dirnames)
            for name in all_directories:
                self.paths.add(current / name)
            dirnames[:] = [name for name in all_directories if not (current / name).is_symlink()]
            for name in sorted(filenames):
                path = current / name
                self.paths.add(path)
                if path.suffix.lower() != ".md":
                    continue
                self._read_markdown(path)

    def _read_markdown(self, path: Path, *, support: bool = False) -> None:
        if support:
            self.support_paths.add(path)
        if path in self.markdown:
            return
        self.paths.add(path)
        try:
            raw = path.read_text(encoding="utf-8")
            self.markdown[path] = raw
        except (OSError, UnicodeDecodeError):
            self.scan_complete = False
            self.findings.append(
                _protocol_finding("document_unreadable", path, "Required Markdown content is not readable UTF-8.")
            )
            return
        if path.name != "index.md":
            return
        try:
            document = DoctidexDocument.load(path)
        except DoctidexError:
            self.findings.append(
                _protocol_finding("frontmatter_invalid", path, "index.md must contain valid mapping frontmatter.")
            )
            return
        self.indexes[path.parent] = IndexInfo(path.parent, document)

    def _scan_navigation_support(self) -> None:
        pending = list(self.support_paths)
        expanded: set[Path] = set()
        while pending:
            path = pending.pop(0)
            if path in expanded or path not in self.markdown:
                continue
            expanded.add(path)
            for link in markdown_links(_body_without_frontmatter(self.markdown[path])):
                target = _resolve_link(path, self.root, link.target)
                if (
                    target is None
                    or not is_within(target, self.root)
                    or target.suffix.lower() != ".md"
                    or not target.is_file()
                ):
                    continue
                was_loaded = target in self.markdown
                self._read_markdown(target, support=True)
                if not was_loaded:
                    pending.append(target)

    def _validate_indexes(self) -> None:
        root = self.indexes[self.root].document
        self._validate_marker(root, expected="index", root=True)
        if not self.root.name:
            self.findings.append(
                _protocol_finding("root_invalid", self.root, "A doctidex root must have a non-empty directory name.")
            )
        for directory, info in sorted(self.indexes.items()):
            self._validate_marker(info.document, expected="index", root=directory == self.root)
            current = directory
            while current != self.root:
                current = current.parent
                if current not in self.indexes:
                    self.findings.append(
                        _protocol_finding(
                            "index_continuity_invalid",
                            info.document.path,
                            "Every directory from a child index to the root must contain index.md.",
                        )
                    )
                    break
            if not info.document.body.strip():
                self.semantic.append(
                    _semantic_candidate(
                        "index_description_review",
                        info.document.path,
                        info.document.path,
                        "Review whether this index gives a sufficient concise entry into its scope.",
                    )
                )

    def _validate_marker(self, document: DoctidexDocument, *, expected: str, root: bool) -> None:
        doctidex = document.doctidex
        valid = (
            document.data.get("type") == expected and isinstance(doctidex, dict) and doctidex.get("type") == expected
        )
        if root:
            valid = valid and doctidex is not None and doctidex.get("root") is True
        elif doctidex is not None and "root" in doctidex and not isinstance(doctidex.get("root"), bool):
            valid = False
        if not valid:
            self.findings.append(
                _protocol_finding(
                    "root_invalid" if root else "frontmatter_invalid",
                    document.path,
                    f"{expected}.md has invalid type or root marker fields.",
                )
            )

    def _validate_configs(self) -> None:
        takeover_dirs = set(self.indexes)
        for directory, info in sorted(self.indexes.items()):
            mapping = info.document.doctidex or {}
            for field_name in _CONFIG_FIELDS:
                raw = mapping.get(field_name, [])
                if not isinstance(raw, list):
                    self.findings.append(
                        _protocol_finding(
                            "local_config_invalid",
                            info.document.path,
                            f"doctidex.{field_name} must be a list.",
                        )
                    )
                    continue
                seen: set[Path] = set()
                for item in raw:
                    if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not item["path"]:
                        self.findings.append(
                            _protocol_finding(
                                "local_config_invalid",
                                info.document.path,
                                f"Every doctidex.{field_name} item must provide a non-empty path string.",
                            )
                        )
                        continue
                    target = _normalize_entry_path(directory, self.root, item["path"])
                    if target is None:
                        self.findings.append(
                            _protocol_finding(
                                "local_config_invalid",
                                info.document.path,
                                f"doctidex.{field_name} contains a path outside the root.",
                            )
                        )
                        continue
                    crossed = [
                        child for child in takeover_dirs if child != directory and _strictly_inside(target, child)
                    ]
                    if any(is_within(child, directory) for child in crossed):
                        self.findings.append(
                            _protocol_finding(
                                "local_config_scope_invalid",
                                info.document.path,
                                f"doctidex.{field_name} cannot declare a target inside a child index scope.",
                            )
                        )
                        continue
                    if target in seen:
                        continue
                    seen.add(target)
                    if field_name in {"boundary-set", "atomic-indexing"} and target.exists() and not target.is_dir():
                        self.findings.append(
                            _protocol_finding(
                                "local_config_invalid",
                                info.document.path,
                                f"doctidex.{field_name} must identify a directory when the target exists.",
                            )
                        )
                        continue
                    info.entries[field_name].append(target)
                    if field_name == "unsafe":
                        self.semantic.append(
                            _semantic_candidate(
                                "unsafe_scope_review",
                                target,
                                info.document.path,
                                "Review whether the unsafe declaration is as narrow as the content requires.",
                            )
                        )

    def _validate_atomic_and_logs(self) -> None:
        for path in sorted(self.paths):
            responsible = self._responsible_index(path)
            if responsible is None:
                continue
            if self._matches(path, responsible, "atomic-indexing") and path.name in {"index.md", "log.md"}:
                self.findings.append(
                    _protocol_finding(
                        "atomic_indexing_invalid",
                        path,
                        "An atomic-indexing directory cannot contain index.md or log.md.",
                    )
                )
            if path.name != "log.md" or self._matches(path, responsible, "unsafe"):
                continue
            try:
                document = DoctidexDocument.load(path)
                self._validate_marker(document, expected="log", root=False)
            except DoctidexError:
                self.findings.append(
                    _protocol_finding("frontmatter_invalid", path, "A safe log.md must contain valid log frontmatter.")
                )
            current = path.parent
            while current != self.root:
                current = current.parent
                if self._path_is_unsafe(current):
                    break
                if not (current / "log.md").is_file():
                    self.findings.append(
                        _protocol_finding(
                            "log_continuity_invalid",
                            path,
                            "Every directory from a safe child log to the root must contain log.md.",
                        )
                    )
                    break

    def _validate_links(self) -> dict[Path, list[Path]]:
        graph: dict[Path, list[Path]] = {}
        for path, raw in sorted(self.markdown.items()):
            responsible = self._responsible_index(path)
            if responsible is None or self._matches(path, responsible, "atomic-indexing"):
                continue
            source_unsafe = self._matches(path, responsible, "unsafe")
            facts: list[LinkFact] = []
            annotations = _link_annotations(raw)
            for link in markdown_links(_body_without_frontmatter(raw)):
                target = _resolve_link(path, self.root, link.target)
                if source_unsafe:
                    if target is not None and target.exists() and os.access(target, os.R_OK):
                        facts.append(LinkFact(target, True))
                    continue
                if target is None:
                    if _is_file_link(link.target):
                        self.findings.append(
                            _protocol_finding(
                                "link_path_invalid",
                                path,
                                f"The link target escapes or cannot be resolved: {link.target}",
                            )
                        )
                    continue
                if not target.exists() or not os.access(target, os.R_OK):
                    self.findings.append(
                        _protocol_finding(
                            "link_path_invalid", path, f"The link target is missing or unreadable: {link.target}"
                        )
                    )
                    facts.append(LinkFact(target, False))
                    continue
                target_responsible = self._responsible_index(target)
                target_unsafe = bool(target_responsible and self._matches(target, target_responsible, "unsafe"))
                annotation, annotation_error = annotations.get(link.order, (None, None))
                boundary = self._first_boundary(path.parent, target, responsible)
                valid = True
                if annotation_error:
                    self.findings.append(_protocol_finding("link_annotation_invalid", path, annotation_error))
                    valid = False
                if boundary is not None and path.name != "index.md":
                    declared = annotation.get("cross-boundary-point") if annotation else None
                    declared_path = (
                        _resolve_annotation_path(path, self.root, declared) if isinstance(declared, str) else None
                    )
                    if declared_path != boundary:
                        self.findings.append(
                            _protocol_finding(
                                "link_annotation_invalid",
                                path,
                                "A non-index cross-boundary link must identify its first boundary point.",
                            )
                        )
                        valid = False
                elif annotation and "cross-boundary-point" in annotation:
                    declared_path = _resolve_annotation_path(path, self.root, annotation["cross-boundary-point"])
                    if boundary is None or declared_path != boundary:
                        self.findings.append(
                            _protocol_finding(
                                "link_annotation_invalid",
                                path,
                                "The declared cross-boundary point is not the first boundary.",
                            )
                        )
                        valid = False
                if not source_unsafe and target_unsafe and (not annotation or annotation.get("unsafe") is not True):
                    self.findings.append(
                        _protocol_finding(
                            "link_annotation_invalid",
                            path,
                            "A safe document link to unsafe content must declare unsafe: true.",
                        )
                    )
                    valid = False
                if annotation and "unsafe" in annotation and not isinstance(annotation["unsafe"], bool):
                    self.findings.append(
                        _protocol_finding(
                            "link_annotation_invalid", path, "The link annotation unsafe field must be boolean."
                        )
                    )
                    valid = False
                facts.append(LinkFact(target, valid))
            graph[path] = [fact.target for fact in facts if fact.valid_edge and fact.target is not None]
        return graph

    def _validate_reachability(self, graph: dict[Path, list[Path]]) -> None:
        for directory, info in sorted(self.indexes.items()):
            reachable: set[Path] = {info.document.path}
            queue = [info.document.path]
            expanded: set[Path] = set()
            while queue:
                current = queue.pop(0)
                if current in expanded:
                    continue
                expanded.add(current)
                for target in graph.get(current, []):
                    if not is_within(target, directory):
                        continue
                    cursor = target
                    while is_within(cursor, directory):
                        reachable.add(cursor)
                        if cursor == directory:
                            break
                        cursor = cursor.parent
                    if target.suffix.lower() == ".md" and target not in expanded and target in graph:
                        target_index_dir = target.parent if target.name == "index.md" else None
                        if target_index_dir is None or target_index_dir == directory:
                            queue.append(target)

            for target in sorted(self._required_targets(directory, info)):
                if target not in reachable:
                    self.findings.append(
                        _protocol_finding(
                            "path_unreachable",
                            target,
                            "The responsible index does not provide a Markdown link path to this target.",
                        )
                    )

    def _required_targets(self, directory: Path, info: IndexInfo) -> set[Path]:
        required: set[Path] = set()
        for path in self.paths:
            if not is_within(path, directory) or path == info.document.path:
                continue
            owner = self._responsible_index(path)
            if owner is None:
                continue
            if owner.directory != directory:
                child = owner.directory
                if child.parent == directory or self._responsible_index(child.parent) == info:
                    required.update({child, owner.document.path})
                continue
            if any(_strictly_inside(path, entry) for entry in info.entries["atomic-indexing"] + info.entries["unsafe"]):
                continue
            required.add(path)
        return required

    def _responsible_index(self, path: Path) -> IndexInfo | None:
        candidate = path if path.is_dir() else path.parent
        matches = [info for directory, info in self.indexes.items() if is_within(candidate, directory)]
        return max(matches, key=lambda info: len(info.directory.parts), default=None)

    @staticmethod
    def _matches(path: Path, info: IndexInfo, field_name: str) -> bool:
        return any(path == entry or _strictly_inside(path, entry) for entry in info.entries[field_name])

    def _path_is_unsafe(self, path: Path) -> bool:
        responsible = self._responsible_index(path)
        return bool(responsible and self._matches(path, responsible, "unsafe"))

    def _first_boundary(self, source: Path, target: Path, info: IndexInfo) -> Path | None:
        route = _directory_route(source, target if target.is_dir() else target.parent)
        for before, after in zip(route, route[1:], strict=False):
            for boundary in info.entries["boundary-set"]:
                if is_within(before, boundary) != is_within(after, boundary):
                    return boundary
        return None


def _scope_error(root: Path, value: str) -> None:
    raise DoctidexError(
        "A validation scope must be an existing readable root-absolute directory path.",
        operation="validate",
        affected=[value],
        actions=["Pass / for the whole root or a path such as /docs/api."],
        code="scope_invalid",
        path=str(root),
    )


def _normalize_entry_path(directory: Path, root: Path, value: str) -> Path | None:
    if value.startswith("/"):
        return None
    parts = list(directory.relative_to(root).parts)
    for part in PurePosixPath(value).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return root.joinpath(*parts)


def _resolve_link(document: Path, root: Path, value: str) -> Path | None:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return None
    path_value = unquote(parsed.path)
    if not path_value:
        return document
    parts = [] if path_value.startswith("/") else list(document.parent.relative_to(root).parts)
    for part in path_value.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return root.joinpath(*parts)


def _resolve_annotation_path(document: Path, root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or "#" in value:
        return None
    return _resolve_link(document, root, value)


def _is_file_link(value: str) -> bool:
    parsed = urlsplit(value)
    return not parsed.scheme and not parsed.netloc


def _link_annotations(raw: str) -> dict[int, tuple[dict[str, Any] | None, str | None]]:
    body = _body_without_frontmatter(raw)
    results: dict[int, tuple[dict[str, Any] | None, str | None]] = {}
    yaml = YAML(typ="safe")
    yaml.allow_duplicate_keys = False
    for order, cursor in enumerate(_source_link_ends(body)):
        found: list[dict[str, Any]] = []
        while True:
            comment = _COMMENT.match(body, cursor)
            if not comment:
                break
            cursor = comment.end()
            content = comment.group(1).strip()
            if not content.startswith("doctidex:"):
                continue
            try:
                value = yaml.load(content[len("doctidex:") :].strip())
                if not isinstance(value, dict):
                    raise ValueError
                found.append(dict(value))
            except Exception:
                results[order] = (None, "The doctidex link annotation must be a valid YAML flow mapping.")
                break
        else:
            pass
        if order in results:
            continue
        if len(found) > 1:
            results[order] = (None, "A link can have at most one doctidex annotation.")
        else:
            results[order] = (found[0] if found else None, None)
    return results


def _source_link_ends(body: str) -> list[int]:
    """Locate source ends for the links that markdown-it accepted."""
    from markdown_it import MarkdownIt

    parser = MarkdownIt("commonmark")
    environment: dict[str, Any] = {}
    parser.parse(body, environment)
    parsed = markdown_links(body)
    references = environment.get("references", {})
    ends: list[int] = []
    expected = 0
    cursor = 0
    while cursor < len(body) and expected < len(parsed):
        opening = body.find("[", cursor)
        if opening < 0:
            break
        cursor = opening + 1
        if opening > 0 and body[opening - 1] == "!":
            continue
        backslashes = 0
        position = opening - 1
        while position >= 0 and body[position] == "\\":
            backslashes += 1
            position -= 1
        if backslashes % 2:
            continue

        label_end = _closing_delimiter(body, opening, "[", "]")
        if label_end is None:
            continue
        end = label_end + 1
        if end < len(body) and body[end] == "(":
            destination_end = _closing_delimiter(body, end, "(", ")")
            if destination_end is None:
                continue
            end = destination_end + 1
        elif end < len(body) and body[end] == "[":
            reference_end = _closing_delimiter(body, end, "[", "]")
            if reference_end is None:
                continue
            end = reference_end + 1
        elif end < len(body) and body[end] == ":":
            continue

        candidate = body[opening:end]
        tokens = parser.parseInline(candidate, {"references": references})
        hrefs = [
            child.attrGet("href") for token in tokens for child in (token.children or []) if child.type == "link_open"
        ]
        if len(hrefs) == 1 and hrefs[0] == parsed[expected].target:
            ends.append(end)
            expected += 1
        cursor = end
    return ends


def _closing_delimiter(value: str, opening: int, left: str, right: str) -> int | None:
    depth = 1
    cursor = opening + 1
    while cursor < len(value):
        if value[cursor] == "\\":
            cursor += 2
            continue
        if value[cursor] == left:
            depth += 1
        elif value[cursor] == right:
            depth -= 1
            if depth == 0:
                return cursor
        cursor += 1
    return None


def _body_without_frontmatter(raw: str) -> str:
    if not raw.startswith("---"):
        return raw
    match = re.match(r"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)", raw, re.DOTALL)
    return raw[match.end() :] if match else raw


def _directory_route(source: Path, target: Path) -> list[Path]:
    source_parts = source.parts
    target_parts = target.parts
    common = 0
    while common < min(len(source_parts), len(target_parts)) and source_parts[common] == target_parts[common]:
        common += 1
    route = [source]
    current = source
    while len(current.parts) > common:
        current = current.parent
        route.append(current)
    for part in target_parts[common:]:
        current = current / part
        route.append(current)
    return route


def _strictly_inside(path: Path, directory: Path) -> bool:
    return path != directory and is_within(path, directory)


def _protocol_finding(code: str, path: Path, message: str) -> dict[str, Any]:
    return finding(
        "protocol",
        "error",
        code,
        message,
        path=str(path),
        actions=["Correct the reported structure and rerun doctidex-git validate."],
    )


def _semantic_candidate(code: str, path: Path, responsible: Path, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "path": str(path),
        "responsible_index": str(responsible),
        "message": message,
        "actions": ["Read the candidate and responsible index, then make a semantic judgment."],
    }


def _filter_scope(
    items: list[dict[str, Any]],
    root: Path,
    scopes: list[str],
    indexes: dict[Path, IndexInfo],
    support_paths: set[Path],
) -> list[dict[str, Any]]:
    if scopes == ["/"]:
        return items
    scope_paths = [root.joinpath(*value.lstrip("/").split("/")) for value in scopes]
    support = {root / "index.md", *support_paths}
    for scope in scope_paths:
        for directory, info in indexes.items():
            if is_within(scope, directory) or is_within(directory, scope):
                support.add(info.document.path)
    filtered = []
    for item in items:
        path_value = item.get("path")
        if not isinstance(path_value, str):
            continue
        path = Path(path_value)
        if path in support or any(is_within(path, scope) for scope in scope_paths):
            filtered.append(item)
    return filtered


def _item_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (str(item.get("path") or ""), str(item.get("code") or ""), str(item.get("message") or ""))
