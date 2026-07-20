"""Parse, resolve, inspect, and normalize Whero Wiki Markdown links."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_flat_frontmatter
from .model import STATUS_FILENAME
from .mounts import WikiMount, discover_mounts, mount_for_path, walk_owned_files
from .paths import is_within, parse_relative_path, path_from_root, wiki_relative


WHERO_SCHEME = "whero-wiki:/"
MARKDOWN = MarkdownIt("commonmark")
LOCAL_FILE_TLDS = {
    "c",
    "cc",
    "conf",
    "config",
    "cpp",
    "css",
    "csv",
    "gif",
    "go",
    "h",
    "hpp",
    "adoc",
    "html",
    "htm",
    "ini",
    "java",
    "jpeg",
    "jpg",
    "js",
    "json",
    "jsx",
    "md",
    "markdown",
    "pdf",
    "png",
    "properties",
    "py",
    "rst",
    "rs",
    "sh",
    "sql",
    "toml",
    "textile",
    "ts",
    "tsx",
    "txt",
    "xml",
    "yaml",
    "yml",
}


@dataclass(frozen=True)
class LinkReference:
    source: str
    destination: str
    target: str | None
    anchor: str
    kind: str
    status: str
    wiki_root: str
    parent_traversals: int = 0


def _walk_tokens(tokens: Iterable[Token]) -> Iterator[Token]:
    for token in tokens:
        yield token
        if token.children:
            yield from _walk_tokens(token.children)


def markdown_destinations(body: str) -> list[str]:
    destinations: list[str] = []
    for token in _walk_tokens(MARKDOWN.parse(body)):
        if token.type not in ("link_open", "image"):
            continue
        attribute = "href" if token.type == "link_open" else "src"
        destination = token.attrGet(attribute)
        if destination:
            destinations.append(destination)
    return destinations


def markdown_body(text: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            raw = "".join(lines[1:index])
            try:
                fields = yaml.safe_load(raw)
            except yaml.YAMLError:
                return text
            if fields is None or isinstance(fields, dict):
                return "".join(lines[index + 1 :])
            return text
    return text


def _is_external(destination: str) -> bool:
    if destination.startswith("//"):
        return True
    parsed = urlsplit(destination)
    if parsed.scheme and parsed.scheme != "whero-wiki":
        return True
    first = parsed.path.split("/", 1)[0]
    hostname = first.rsplit(":", 1)[0] if first.rsplit(":", 1)[-1].isdigit() else first
    if not re.fullmatch(
        r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
        r"[A-Za-z]{2,63}",
        hostname,
    ):
        return False
    return hostname.rsplit(".", 1)[-1].lower() not in LOCAL_FILE_TLDS


def _is_partial_root(root: Path) -> bool:
    status = root / STATUS_FILENAME
    if not status.is_file():
        return False
    try:
        return frontmatter_is_true(
            read_flat_frontmatter(status),
            "whero_partial_disclosure",
        )
    except WheroToolError:
        return False


def _logical_path(path: Path) -> Path:
    return Path(os.path.abspath(path))


def owning_wiki_root(document: Path, root: Path, mounts: list[WikiMount]) -> Path:
    relative = wiki_relative(_logical_path(document), _logical_path(root))
    mount = mount_for_path(relative, mounts)
    if mount and mount.kind in ("whero-wiki", "partial-wiki"):
        return _logical_path(mount.root)
    return _logical_path(root)


def resolve_markdown_destination(
    document: Path,
    destination: str,
    wiki_root: Path,
    *,
    mounts: list[WikiMount] | None = None,
) -> tuple[Path | None, str, str]:
    if _is_external(destination):
        return None, "", "external"
    parsed = urlsplit(destination)
    path_text = parsed.path
    fragment = unquote(parsed.fragment)
    mounts = mounts or []
    owner = owning_wiki_root(document, wiki_root, mounts)
    preserve_logical_path = _is_partial_root(owner)
    if destination.startswith("whero-wiki:"):
        if not destination.startswith(WHERO_SCHEME):
            return None, fragment, "invalid"
        path_text = parsed.path.lstrip("/")
        target = _logical_path(owner / unquote(path_text))
        if not is_within(target, owner):
            return target, fragment, "cross-boundary"
        return (
            target if preserve_logical_path else target.resolve(strict=False),
            fragment,
            "whero-rooted",
        )
    if not path_text:
        target = _logical_path(document)
        return (
            target if preserve_logical_path else target.resolve(strict=False),
            fragment,
            "fragment",
        )
    decoded = unquote(path_text)
    if decoded.startswith("/"):
        target = owner / decoded.lstrip("/")
        kind = "root-absolute"
    else:
        target = document.parent / decoded
        kind = "relative"
    logical = _logical_path(target)
    if not is_within(logical, owner):
        return logical, fragment, "cross-boundary"
    resolved = logical if preserve_logical_path else logical.resolve(strict=False)
    if not preserve_logical_path and not is_within(resolved, owner):
        return resolved, fragment, "cross-boundary"
    return resolved, fragment, kind


def _slug(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_~]", "", text).lower().strip()
    characters = [character for character in text if character.isalnum() or character in " -_"]
    return re.sub(r"[\s]+", "-", "".join(characters)).strip("-")


def markdown_headings(body: str) -> list[tuple[int, str]]:
    tokens = MARKDOWN.parse(body)
    headings: list[tuple[int, str]] = []
    for index, token in enumerate(tokens[:-1]):
        if token.type != "heading_open" or tokens[index + 1].type != "inline":
            continue
        try:
            level = int(token.tag.removeprefix("h"))
        except ValueError:
            continue
        headings.append((level, tokens[index + 1].content.strip()))
    return headings


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: set[str] = set()

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        for name, value in attrs:
            if value and (name.lower() == "id" or (tag.lower() == "a" and name.lower() == "name")):
                self.anchors.add(value)

    handle_startendtag = handle_starttag


def heading_anchors(path: Path) -> set[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return set()
    text = markdown_body(text)
    tokens = MARKDOWN.parse(text)
    parser = _AnchorParser()
    for token in _walk_tokens(tokens):
        if token.type in ("html_block", "html_inline"):
            parser.feed(token.content)
    anchors = set(parser.anchors)
    counts: dict[str, int] = {}
    for _, heading in markdown_headings(text):
        base = _slug(heading)
        if not base:
            continue
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def _parent_traversals(destination: str) -> int:
    if destination.startswith(("/", "whero-wiki:")):
        return 0
    path_text = unquote(urlsplit(destination).path)
    count = 0
    for part in PurePosixPath(path_text).parts:
        if part == "..":
            count += 1
        else:
            break
    return count


def inspect_document_links(
    root: Path,
    document: Path,
    *,
    available: bool = False,
    mounts: list[WikiMount] | None = None,
) -> list[LinkReference]:
    mounts = mounts if mounts is not None else discover_mounts(root)
    try:
        body = markdown_body(document.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise WheroToolError(f"cannot read Markdown links from {document}: {exc}") from exc
    owner = owning_wiki_root(document, root, mounts)
    references: list[LinkReference] = []
    for destination in markdown_destinations(body):
        target, anchor, kind = resolve_markdown_destination(
            document,
            destination,
            root,
            mounts=mounts,
        )
        if kind == "external":
            status = "external"
        elif kind in ("invalid", "cross-boundary"):
            status = "invalid"
        elif target is None or not target.exists():
            status = "unavailable" if available else "missing"
        else:
            anchor_target = target / "index.md" if target.is_dir() else target
            status = (
                "anchor-missing"
                if anchor and anchor_target.is_file() and anchor not in heading_anchors(anchor_target)
                else "resolved"
            )
        references.append(
            LinkReference(
                wiki_relative(_logical_path(document), _logical_path(root)).as_posix(),
                destination,
                (
                    target.relative_to(root).as_posix()
                    if target is not None and is_within(target, root)
                    else str(target) if target is not None else None
                ),
                anchor,
                kind,
                status,
                str(owner),
                _parent_traversals(destination),
            )
        )
    return references


def markdown_files(root: Path, *, include_mounts: bool = False) -> Iterator[Path]:
    if include_mounts:
        for directory, _, filenames in os.walk(root, followlinks=False):
            current = Path(directory)
            for name in filenames:
                if name.lower().endswith(".md"):
                    yield current / name
        return
    for path in walk_owned_files(root):
        if path.suffix.lower() == ".md":
            yield path


def inspect_wiki_links(
    root: Path,
    *,
    available: bool = False,
    include_mounts: bool = False,
) -> list[LinkReference]:
    mounts = discover_mounts(root)
    references: list[LinkReference] = []
    for document in markdown_files(root, include_mounts=include_mounts):
        references.extend(
            inspect_document_links(
                root,
                document,
                available=available,
                mounts=mounts,
            )
        )
    return references


def inbound_links(
    root: Path,
    target_text: str,
    *,
    available: bool = False,
) -> list[LinkReference]:
    target = path_from_root(root, parse_relative_path(target_text, label="target path"))
    target = _logical_path(target) if _is_partial_root(root) else target.resolve(strict=False)
    target_relative = target.relative_to(_logical_path(root)).as_posix()
    return [
        reference
        for reference in inspect_wiki_links(root, available=available)
        if reference.target == target_relative
    ]


def normalization_suggestions(root: Path) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    for reference in inspect_wiki_links(root):
        if (
            reference.kind != "relative"
            or reference.parent_traversals <= 3
            or reference.status not in ("resolved", "anchor-missing")
            or reference.target is None
        ):
            continue
        owner = Path(reference.wiki_root)
        target = _logical_path(root / reference.target)
        if not is_within(target, owner):
            continue
        owner_relative = target.relative_to(owner).as_posix()
        replacement = f"{WHERO_SCHEME}{owner_relative}"
        if reference.anchor:
            replacement += f"#{reference.anchor}"
        suggestions.append(
            {
                "source": reference.source,
                "destination": reference.destination,
                "replacement": replacement,
                "reason": "relative link traverses more than three parent directories",
            }
        )
    return suggestions


def render_suggestions(suggestions: list[dict[str, str]], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(suggestions, indent=2)
    return "\n".join(
        f"SUGGEST {item['source']}: {item['destination']} -> {item['replacement']}"
        for item in suggestions
    )


def render_link_references(references: list[LinkReference], output_format: str) -> str:
    if output_format == "json":
        return json.dumps([asdict(reference) for reference in references], indent=2)
    lines = []
    for reference in references:
        target = f" -> {reference.target}" if reference.target else ""
        anchor = f"#{reference.anchor}" if reference.anchor else ""
        lines.append(
            f"{reference.status.upper()} {reference.source}: "
            f"{reference.destination}{target}{anchor} [{reference.kind}]"
        )
    return "\n".join(lines)
