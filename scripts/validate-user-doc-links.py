"""Validate that ``docs/user`` links remain reachable in a packaged skill tree."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark")


def _leaf_tokens(tokens: list[object]) -> Iterator[object]:
    for token in tokens:
        children = getattr(token, "children", None)
        if children:
            yield from _leaf_tokens(children)
        else:
            yield token


def _link_targets(content: str) -> Iterator[tuple[int, str]]:
    for token in _MARKDOWN.parse(content):
        if token.type != "inline" or token.map is None:
            continue
        line = token.map[0] + 1
        for leaf in _leaf_tokens(token.children or []):
            target: str | None = None
            if leaf.type == "link_open":
                target = leaf.attrGet("href")
            elif leaf.type == "image":
                target = leaf.attrGet("src")
            if target is not None:
                yield line, target


def _heading_anchor(content: str) -> str:
    text = content
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_~]+", "", text)
    text = text.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _heading_anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    tokens = _MARKDOWN.parse(path.read_text())
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        inline = tokens[index + 1] if index + 1 < len(tokens) else None
        if inline is not None and inline.type == "inline" and inline.content:
            anchors.add(_heading_anchor(inline.content))
    return anchors


def _validate(
    docs_root: Path,
    references_root: Path,
    source: Path,
    href: str,
) -> tuple[str, str]:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
        return "non-relative", f"link target must be a relative docs/user path: {href}"

    target = source if not parsed.path else (source.parent / unquote(parsed.path)).resolve(strict=False)
    if not target.is_relative_to(docs_root):
        return "out-of-scope", f"link target leaves docs/user: {href}"
    if not target.is_file():
        return "missing-source", f"link target does not exist in docs/user: {href}"

    packaged = references_root / target.relative_to(docs_root)
    if not packaged.is_file():
        return "dangling", f"link target is missing from the packaged references tree: {href}"
    if parsed.fragment and _heading_anchor(parsed.fragment) not in _heading_anchors(packaged):
        return "missing-fragment", f"link fragment does not exist: {href}"
    return "ok", ""


def run(docs_root: Path, references_root: Path) -> int:
    """Validate every Markdown link under ``docs_root`` against ``references_root``."""

    docs_root = docs_root.resolve()
    references_root = references_root.resolve()
    violations: list[dict[str, object]] = []
    for document in sorted(docs_root.rglob("*.md")):
        relative = document.relative_to(docs_root)
        for line, href in _link_targets(document.read_text()):
            kind, message = _validate(docs_root, references_root, document, href)
            if kind == "ok":
                continue
            violations.append(
                {
                    "source": str(relative),
                    "line": line,
                    "target": href,
                    "kind": kind,
                    "message": message,
                }
            )

    for violation in violations:
        print(json.dumps(violation, ensure_ascii=False))
    return 1 if violations else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate docs/user Markdown links against a packaged references tree."
    )
    parser.add_argument("--docs-root", type=Path, required=True, help="Source docs/user directory.")
    parser.add_argument("--references-root", type=Path, required=True, help="Packaged references directory.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    return run(args.docs_root, args.references_root)


if __name__ == "__main__":
    raise SystemExit(main())
