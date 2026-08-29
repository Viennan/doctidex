"""Markdown link scanning and annotation parsing."""

from __future__ import annotations

import functools
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt
from markdown_it.rules_inline.link import link as _markdown_link_rule
from markdown_it.rules_inline.state_inline import StateInline

from whero.doctidex.errors import CommandFailure
from whero.doctidex.model import BoundaryPoint, InlineAnnotation, Installation, Ref
from whero.doctidex.paths import fs_path_to_repo_path, normalize_repo_path, repo_path_to_fs
from whero.doctidex.store.model_view import RuntimeModelView


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    """One local Markdown link and its work-model association."""

    path: str
    line: int
    link_path: str
    source_end: int | None
    target_path: str | None
    boundary_point: BoundaryPoint | None
    installation: Installation | None
    ref: Ref | None

    def reference_details(self) -> dict[str, object]:
        """Return the source location of this link for diagnostics."""

        return {"path": self.path, "line": self.line, "link-path": self.link_path}


def scan_cross_boundary_links(
    git_root: Path,
    model: RuntimeModelView,
    *,
    scope: str = "/",
) -> tuple[MarkdownLink, ...]:
    """Scan Markdown under ``scope`` and return only links that cross a boundary."""

    scope = normalize_repo_path(scope, parameter="scope")
    root = repo_path_to_fs(git_root, scope)
    boundaries = {point.path for point in model.boundary_points}
    documents = _rg_candidate_documents(git_root, root, boundaries, model) if _rg_available() else None
    if documents is None:
        documents = _walk_candidate_documents(git_root, root, boundaries)
    return _precise_scan_documents(documents, git_root, model)


def resolve_local_link(document_path: str, link_path: str) -> str | None:
    """Resolve one local Markdown link to a normalized repository path."""

    parsed = urlsplit(link_path)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path) if parsed.path else document_path
    candidate = path if path.startswith("/") else _join_repo_path(_parent_path(document_path), path)
    try:
        return normalize_repo_path(candidate, parameter="link-path")
    except Exception:
        return None


@functools.lru_cache(maxsize=1)
def _rg_available() -> bool:
    """Return whether ripgrep with PCRE2 support is available."""

    if shutil.which("rg") is None:
        return False
    try:
        completed = subprocess.run(
            ["rg", "--pcre2-version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return completed.returncode == 0


def _rg_candidate_documents(
    git_root: Path,
    root: Path,
    boundaries: set[str],
    model: RuntimeModelView,
) -> set[str] | None:
    """Return documents that may contain a boundary-crossing link, or ``None`` on fallback."""

    documents: set[str] = set()
    try:
        for pattern in (_INLINE_CANDIDATE_PATTERN, _REFERENCE_CANDIDATE_PATTERN):
            for document_path, raw_candidate in _iter_rg_candidates(git_root, root, boundaries, pattern):
                classification, target = _coarse_classify(document_path, raw_candidate)
                if classification == "outside-repository":
                    continue
                if classification == "unresolved" or (
                    target is not None and model.first_boundary(target) is not None
                ):
                    documents.add(document_path)
    except (_RipgrepFailure, OSError, ValueError):
        return None
    return documents


def _walk_candidate_documents(git_root: Path, root: Path, boundaries: set[str]) -> set[str]:
    """Return in-scope Markdown documents using the current filesystem walk."""

    documents: set[str] = set()
    for directory, child_directories, files in os.walk(root):
        current_path = fs_path_to_repo_path(git_root, Path(directory))
        child_directories[:] = [
            name
            for name in child_directories
            if name != ".doctidex-git" and _join_repo_path(current_path, name) not in boundaries
        ]
        for name in files:
            document = Path(directory) / name
            if not name.endswith(".md"):
                continue
            document_path = fs_path_to_repo_path(git_root, document)
            if document_path in boundaries:
                continue
            documents.add(document_path)
    return documents


def _precise_scan_documents(
    documents: set[str],
    git_root: Path,
    model: RuntimeModelView,
) -> tuple[MarkdownLink, ...]:
    """Precisely parse selected documents and return only cross-boundary links."""

    links: list[MarkdownLink] = []
    for document_path in sorted(documents):
        document = repo_path_to_fs(git_root, document_path)
        try:
            content = document.read_text()
        except OSError:
            continue
        for link in _local_link_paths(content):
            target_path = resolve_local_link(document_path, link.link_path)
            if target_path is None:
                continue
            boundary = model.first_boundary(target_path)
            if boundary is None:
                continue
            links.append(
                MarkdownLink(
                    path=document_path,
                    line=link.line,
                    link_path=link.link_path,
                    source_end=link.source_end,
                    target_path=target_path,
                    boundary_point=boundary,
                    installation=model.installation_for_boundary(boundary),
                    ref=model.ref_for_boundary(boundary),
                )
            )
    return tuple(links)


def parse_inline_annotation(content: str, position: int) -> InlineAnnotation | None:
    """Parse the doctidex annotation immediately following ``position``."""

    index = position
    while True:
        while index < len(content) and content[index].isspace():
            index += 1
        if not content.startswith("<!--", index):
            return None
        end = content.find("-->", index + len("<!--"))
        if end < 0:
            return None
        annotation = _parse_annotation_block(content[index + len("<!--") : end])
        if annotation is not None:
            return annotation
        index = end + len("-->")


def resolve_inline_annotation_boundary(
    document_path: str,
    link_path: str,
    annotation: InlineAnnotation,
) -> str | None:
    """Resolve a cross-boundary annotation to its repository-internal path."""

    link = urlsplit(link_path)
    annotation_path = urlsplit(annotation.cross_boundary_point)
    if (
        link.scheme
        or link.netloc
        or annotation_path.scheme
        or annotation_path.netloc
        or annotation_path.query
        or annotation_path.fragment
        or not _path_prefix(annotation_path.path, link.path)
    ):
        return None
    return resolve_local_link(document_path, annotation.cross_boundary_point)


def _parse_annotation_block(block: str) -> InlineAnnotation | None:
    payload = block.lstrip()
    prefix = "doctidex:"
    if not payload.startswith(prefix):
        return None
    try:
        value = yaml.safe_load(payload.removeprefix(prefix))
    except yaml.YAMLError:
        return None
    cross_boundary_point = value.get("cross-boundary-point") if isinstance(value, dict) else None
    if not isinstance(cross_boundary_point, str):
        return None
    return InlineAnnotation(cross_boundary_point=cross_boundary_point)


_INLINE_CANDIDATE_PATTERN = (
    r"\]\(\K(?<dest>(?:[^()\\]|\\.|\((?:[^()\\]|\\.|(?&dest))*\))*)(?=\))"
)
_REFERENCE_CANDIDATE_PATTERN = r"(?m)^ {0,3}\[[^\]\n]+\]:[ \t]*\K[^\n]*"


class _RipgrepFailure(Exception):
    """Ripgrep could not produce a reliable candidate stream."""


def _rg_command(root: Path, boundaries: set[str], pattern: str) -> list[str]:
    command = [
        "rg",
        "--json",
        "-U",
        "--pcre2",
        "--multiline-dotall",
        "--hidden",
        "--no-ignore",
        "--no-messages",
        "-g",
        "*.md",
        "-g",
        "!.doctidex-git",
        "-g",
        "!.doctidex-git/**",
    ]
    for boundary in sorted(boundaries):
        if boundary == "/" or boundary == "/.doctidex-git" or boundary.startswith("/.doctidex-git/"):
            continue
        relative = boundary.lstrip("/")
        command.extend(("-g", f"!{relative}", "-g", f"!{relative}/**"))
    command.extend(("--", pattern, str(root)))
    return command


def _iter_rg_candidates(
    git_root: Path,
    root: Path,
    boundaries: set[str],
    pattern: str,
) -> Iterator[tuple[str, str]]:
    command = _rg_command(root, boundaries, pattern)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError as exc:
        raise _RipgrepFailure from exc
    assert process.stdout is not None
    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise _RipgrepFailure from exc
            if record.get("type") != "match":
                continue
            data = record.get("data", {})
            path_text = data.get("path", {}).get("text")
            if not path_text:
                continue
            document_path = fs_path_to_repo_path(git_root, Path(path_text))
            for submatch in data.get("submatches", ()):
                match_text = submatch.get("match", {}).get("text")
                if match_text is not None:
                    yield document_path, match_text
    finally:
        returncode = process.wait()
    if returncode not in (0, 1):
        raise _RipgrepFailure


def _coarse_classify(document_path: str, raw_candidate: str) -> tuple[str, str | None]:
    """Classify one raw candidate for the document prefilter."""

    destination = _extract_destination(raw_candidate)
    if destination is None:
        return "unresolved", None
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        return "outside-repository", None
    try:
        path = unquote(parsed.path) if parsed.path else document_path
    except Exception:
        return "unresolved", None
    candidate = path if path.startswith("/") else _join_repo_path(_parent_path(document_path), path)
    try:
        return "target", normalize_repo_path(candidate, parameter="link-path")
    except CommandFailure:
        return "outside-repository", None
    except Exception:
        return "unresolved", None


def _extract_destination(raw_candidate: str) -> str | None:
    text = raw_candidate.strip()
    if not text:
        return None
    if text.startswith("<"):
        end = text.find(">")
        if end < 0:
            return None
        return text[1:end]
    escaped = False
    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character.isspace():
            return text[:index]
    return text


def _path_prefix(prefix: str, path: str) -> bool:
    if not prefix or not path.startswith(prefix):
        return False
    return len(path) == len(prefix) or prefix.endswith("/") or path[len(prefix)] == "/"


def _link_with_source_offset(state: StateInline, silent: bool) -> bool:
    start = state.pos
    token_count = len(state.tokens)
    matched = _markdown_link_rule(state, silent)
    if matched and not silent:
        for token in state.tokens[token_count:]:
            if token.type == "link_open":
                token.meta["source-offset"] = start
                token.meta["source-end"] = state.pos
    return matched


_MARKDOWN = MarkdownIt("commonmark")
_MARKDOWN.inline.ruler.at("link", _link_with_source_offset)


@dataclass(frozen=True, slots=True)
class _LocalLink:
    line: int
    link_path: str
    source_end: int | None


def _local_link_paths(content: str) -> tuple[_LocalLink, ...]:
    matches: list[_LocalLink] = []
    line_offsets = [0, *(index + 1 for index, character in enumerate(content) if character == "\n")]
    matched_inline_starts: set[int] = set()
    for token in _MARKDOWN.parse(content):
        if token.type != "inline" or token.map is None:
            continue
        source_start = _inline_source_start(
            content,
            token.content,
            token.map,
            line_offsets,
            matched_starts=matched_inline_starts,
        )
        if source_start is not None:
            matched_inline_starts.add(source_start)
        for child in token.children or ():
            if child.type != "link_open":
                continue
            link_path = child.attrGet("href")
            if link_path is None:
                continue
            offset = child.meta.get("source-offset", 0)
            end = child.meta.get("source-end")
            line = token.map[0] + token.content[:offset].count("\n") + 1
            source_end = source_start + end if source_start is not None and isinstance(end, int) else None
            matches.append(_LocalLink(line=line, link_path=link_path, source_end=source_end))
    return tuple(matches)


def _inline_source_start(
    content: str,
    inline_content: str,
    source_map: list[int],
    line_offsets: list[int],
    *,
    matched_starts: set[int],
) -> int | None:
    if not inline_content:
        return None
    start_line, end_line = source_map
    block_start = line_offsets[start_line]
    block_end = line_offsets[end_line] if end_line < len(line_offsets) else len(content)
    search_start = block_start
    while True:
        source_start = content.find(inline_content, search_start, block_end)
        if source_start < 0:
            return None
        if source_start not in matched_starts:
            return source_start
        search_start = source_start + 1


def _join_repo_path(parent: str, child: str) -> str:
    return f"{parent.rstrip('/')}/{child}" if parent != "/" else f"/{child}"


def _parent_path(path: str) -> str:
    parent = path.rsplit("/", maxsplit=1)[0]
    return parent or "/"


__all__ = [
    "MarkdownLink",
    "parse_inline_annotation",
    "resolve_inline_annotation_boundary",
    "resolve_local_link",
    "scan_cross_boundary_links",
]
