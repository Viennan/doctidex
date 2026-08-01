from __future__ import annotations

import io
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from whero.doctidex.errors import DoctidexError

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True, slots=True)
class MarkdownLink:
    label: str
    target: str
    order: int


class DoctidexDocument:
    def __init__(
        self,
        path: Path,
        data: CommentedMap,
        body: str,
        *,
        newline: str = "\n",
    ) -> None:
        self.path = path
        self.data = data
        self.body = body
        self.newline = newline

    @classmethod
    def load(cls, path: Path) -> DoctidexDocument:
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DoctidexError(
                f"{path} is not valid UTF-8.",
                operation="parse_document",
                affected=[str(path)],
                actions=["Convert the document to UTF-8 and retry."],
                code="invalid_utf8",
            ) from exc
        except OSError as exc:
            raise DoctidexError(
                f"Cannot read {path}: {exc.strerror or exc}.",
                operation="parse_document",
                affected=[str(path)],
                actions=["Check that the file exists and is readable."],
                code="document_unreadable",
            ) from exc

        match = _FRONTMATTER.match(raw)
        if not match:
            raise DoctidexError(
                f"{path} does not start with YAML frontmatter.",
                operation="parse_document",
                affected=[str(path)],
                actions=["Add a YAML mapping between opening and closing --- lines."],
                code="frontmatter_missing",
            )

        yaml = _yaml()
        try:
            parsed = yaml.load(match.group(1))
        except Exception as exc:
            raise DoctidexError(
                f"Cannot parse frontmatter in {path}: {exc}.",
                operation="parse_document",
                affected=[str(path)],
                actions=["Correct the YAML frontmatter and retry."],
                code="frontmatter_invalid",
            ) from exc
        if not isinstance(parsed, CommentedMap):
            raise DoctidexError(
                f"Frontmatter in {path} must be a YAML mapping.",
                operation="parse_document",
                affected=[str(path)],
                actions=["Replace the frontmatter value with a YAML mapping."],
                code="frontmatter_not_mapping",
            )
        newline = "\r\n" if "\r\n" in raw[: match.end()] else "\n"
        return cls(path, parsed, raw[match.end() :], newline=newline)

    @property
    def doctidex(self) -> CommentedMap | None:
        value = self.data.get("doctidex")
        return value if isinstance(value, CommentedMap) else None

    @property
    def is_root(self) -> bool:
        return bool(self.doctidex and self.doctidex.get("root") is True)

    def links(self) -> list[MarkdownLink]:
        return markdown_links(self.body)

    def render(self) -> str:
        stream = io.StringIO()
        yaml = _yaml()
        yaml.dump(self.data, stream)
        frontmatter = stream.getvalue().replace("\n", self.newline)
        return f"---{self.newline}{frontmatter}---{self.newline}{self.body}"

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rendered = self.render()
        mode = self.path.stat().st_mode if self.path.exists() else None
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            if mode is not None:
                os.chmod(temp_path, mode)
            os.replace(temp_path, self.path)
        finally:
            temp_path.unlink(missing_ok=True)


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.allow_duplicate_keys = False
    yaml.default_flow_style = False
    return yaml


def markdown_links(content: str) -> list[MarkdownLink]:
    parser = MarkdownIt("commonmark")
    links: list[MarkdownLink] = []
    order = 0
    for token in parser.parse(content):
        if token.type != "inline" or not token.children:
            continue
        children = token.children
        for index, child in enumerate(children):
            if child.type != "link_open":
                continue
            target = child.attrGet("href")
            if target is None:
                continue
            label_parts: list[str] = []
            cursor = index + 1
            while cursor < len(children) and children[cursor].type != "link_close":
                if children[cursor].type in {"text", "code_inline"}:
                    label_parts.append(children[cursor].content)
                cursor += 1
            links.append(MarkdownLink("".join(label_parts), target, order))
            order += 1
    return links
