"""Root ``index.md`` identity parsing and initialization."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

ROOT_INDEX_FRONTMATTER = {
    "type": "index",
    "doctidex": {
        "type": "index",
        "root": True,
    },
}


@dataclass(frozen=True, slots=True)
class RootIndexFrontmatterConflict(RuntimeError):
    """A required root-identity field is present with another value."""

    field: str
    expected: object
    actual: object


@dataclass(frozen=True, slots=True)
class RootIndexFrontmatterInvalid(RuntimeError):
    """Existing frontmatter cannot be safely supplemented."""

    reason: str


@dataclass(frozen=True, slots=True)
class _FrontmatterDocument:
    metadata: dict[str, object]
    body: str


def root_index_frontmatter(content: str) -> object:
    """Return root frontmatter for validation, or ``None`` when it is unusable."""

    try:
        return _parse_frontmatter(content).metadata
    except RootIndexFrontmatterInvalid:
        return None


def root_index_matches(frontmatter: object) -> bool:
    """Return whether parsed frontmatter declares the Architecture root identity."""

    return (
        isinstance(frontmatter, dict)
        and frontmatter.get("type") == ROOT_INDEX_FRONTMATTER["type"]
        and isinstance(frontmatter.get("doctidex"), dict)
        and frontmatter["doctidex"].get("type") == ROOT_INDEX_FRONTMATTER["doctidex"]["type"]
        and frontmatter["doctidex"].get("root") is ROOT_INDEX_FRONTMATTER["doctidex"]["root"]
    )


def prepare_root_index(content: str | None) -> str:
    """Return a root-index document with all required identity fields present.

    Existing body text and unrelated frontmatter data are retained. A present
    required field is never overwritten.
    """

    if content is None:
        return _render(ROOT_INDEX_FRONTMATTER, "")
    if not content.startswith("---"):
        return _render(ROOT_INDEX_FRONTMATTER, content)

    document = _parse_frontmatter(content)
    metadata = dict(document.metadata)
    if "doctidex" not in metadata:
        doctidex_fields: dict[str, object] = {}
    elif isinstance(metadata["doctidex"], dict):
        doctidex_fields = dict(metadata["doctidex"])
    else:
        raise RootIndexFrontmatterConflict("doctidex", "mapping", metadata["doctidex"])

    changed = _supplement(metadata, "type", ROOT_INDEX_FRONTMATTER["type"])
    changed |= _supplement(
        doctidex_fields,
        "type",
        ROOT_INDEX_FRONTMATTER["doctidex"]["type"],
        prefix="doctidex.",
    )
    changed |= _supplement(
        doctidex_fields,
        "root",
        ROOT_INDEX_FRONTMATTER["doctidex"]["root"],
        prefix="doctidex.",
    )
    if not changed:
        return content
    metadata["doctidex"] = doctidex_fields
    return _render(metadata, document.body)


def _supplement(mapping: dict[str, object], key: str, expected: object, *, prefix: str = "") -> bool:
    if key not in mapping:
        mapping[key] = expected
        return True
    if mapping[key] != expected or type(mapping[key]) is not type(expected):
        raise RootIndexFrontmatterConflict(f"{prefix}{key}", expected, mapping[key])
    return False


def _parse_frontmatter(content: str) -> _FrontmatterDocument:
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise RootIndexFrontmatterInvalid("missing-frontmatter")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise RootIndexFrontmatterInvalid("unterminated-frontmatter") from exc
    try:
        metadata = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise RootIndexFrontmatterInvalid("invalid-yaml") from exc
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise RootIndexFrontmatterInvalid("not-a-mapping")
    return _FrontmatterDocument(metadata, "".join(lines[end + 1 :]))


def _render(metadata: dict[str, object], body: str) -> str:
    return f"---\n{yaml.safe_dump(metadata, sort_keys=False)}---\n{body}"


__all__ = [
    "ROOT_INDEX_FRONTMATTER",
    "RootIndexFrontmatterConflict",
    "RootIndexFrontmatterInvalid",
    "prepare_root_index",
    "root_index_frontmatter",
    "root_index_matches",
]
