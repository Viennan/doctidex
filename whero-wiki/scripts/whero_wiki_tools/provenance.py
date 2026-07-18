"""Validate curated provenance and map repository changes to concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .diagnostics import Diagnostics
from .frontmatter import read_markdown, scalar_text
from .git import head_commit, repository_root
from .mounts import walk_owned_files
from .paths import parse_relative_path, path_from_root, sha256_file


PROVENANCE_KINDS = {
    "collected-source",
    "repository-path",
    "git-revision",
    "discussion",
    "user-authored",
}
HEX_64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class AffectedConcept:
    concept: str
    changed_path: str
    provenance_kind: str


def concept_provenance(fields: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    sources = fields.get("source_documents")
    if isinstance(sources, list):
        for item in sources:
            if isinstance(item, dict):
                entries.append({"kind": "collected-source", **item})
    provenance = fields.get("provenance")
    if isinstance(provenance, list):
        entries.extend(item for item in provenance if isinstance(item, dict))
    return entries


def validate_provenance(
    root: Path,
    concept: Path,
    fields: dict[str, Any],
    diagnostics: Diagnostics,
    *,
    available: bool,
    strict_stale: bool,
) -> None:
    entries = concept_provenance(fields)
    if not entries:
        diagnostics.error(
            "CURATED_PROVENANCE",
            "provide source_documents or a non-empty provenance list",
            concept,
        )
        return
    for entry in entries:
        kind = scalar_text(entry.get("kind"))
        if kind not in PROVENANCE_KINDS:
            diagnostics.error(
                "CURATED_PROVENANCE_KIND",
                f"unsupported provenance kind: {kind!r}",
                concept,
            )
            continue
        if kind in ("collected-source", "repository-path", "discussion"):
            try:
                relative = parse_relative_path(
                    scalar_text(entry.get("path") or entry.get("reference")),
                    label=f"{kind} provenance path",
                )
            except ValueError as exc:
                diagnostics.error("CURATED_PROVENANCE_PATH", str(exc), concept)
                continue
            target = path_from_root(root, relative)
            if not target.exists():
                reporter = diagnostics.notice if available else diagnostics.error
                if kind == "collected-source":
                    code = "CURATED_SOURCE_UNAVAILABLE" if available else "CURATED_SOURCE_MISSING"
                else:
                    code = "CURATED_PROVENANCE_UNAVAILABLE" if available else "CURATED_PROVENANCE_MISSING"
                reporter(
                    code,
                    f"{kind} provenance is unavailable: {relative}",
                    concept,
                )
                continue
            expected_sha = scalar_text(entry.get("sha256"))
            if kind == "collected-source" and not HEX_64_RE.fullmatch(expected_sha):
                diagnostics.error(
                    "CURATED_SOURCE_DIGEST",
                    f"source has an invalid sha256: {relative}",
                    concept,
                )
                continue
            if expected_sha and target.is_file() and sha256_file(target) != expected_sha.lower():
                reporter = diagnostics.error if strict_stale else diagnostics.warning
                reporter(
                    "CURATED_SOURCE_STALE" if kind == "collected-source" else "CURATED_PROVENANCE_STALE",
                    f"provenance digest changed and requires review: {relative}",
                    concept,
                )
            expected_commit = scalar_text(entry.get("git_commit"))
            if expected_commit:
                current = head_commit(target if target.is_dir() else target.parent)
                if current and current != expected_commit:
                    reporter = diagnostics.error if strict_stale else diagnostics.warning
                    reporter(
                        "CURATED_PROVENANCE_GIT_STALE",
                        f"repository provenance advanced from {expected_commit[:12]} to {current[:12]}",
                        concept,
                    )
        elif kind == "git-revision":
            commit = scalar_text(entry.get("commit"))
            repository = scalar_text(entry.get("repository")) or "."
            if not commit:
                diagnostics.error(
                    "CURATED_PROVENANCE_COMMIT",
                    "git-revision provenance requires commit",
                    concept,
                )
                continue
            try:
                repository_path = path_from_root(
                    root,
                    parse_relative_path(repository, label="provenance repository")
                    if repository != "."
                    else PurePosixPath(),
                )
            except ValueError as exc:
                diagnostics.error("CURATED_PROVENANCE_REPOSITORY", str(exc), concept)
                continue
            if repository_root(repository_path) is None:
                reporter = diagnostics.notice if available else diagnostics.error
                reporter(
                    "CURATED_PROVENANCE_GIT_UNAVAILABLE",
                    f"Git repository is unavailable: {repository}",
                    concept,
                )
        elif kind == "user-authored" and not scalar_text(entry.get("reference")):
            diagnostics.error(
                "CURATED_PROVENANCE_REFERENCE",
                "user-authored provenance requires a stable reference",
                concept,
            )


def affected_concepts(
    wiki_root: Path,
    repository_root_path: Path,
    changed: list[PurePosixPath],
) -> list[AffectedConcept]:
    affected: list[AffectedConcept] = []
    for path in walk_owned_files(wiki_root):
        if path.suffix.lower() != ".md":
            continue
        try:
            document = read_markdown(path)
        except ValueError:
            continue
        if document.fields.get("whero_curated") is not True:
            continue
        for entry in concept_provenance(document.fields):
            kind = scalar_text(entry.get("kind"))
            if kind not in ("repository-path", "collected-source", "discussion"):
                continue
            raw = scalar_text(entry.get("path") or entry.get("reference"))
            try:
                provenance_path = parse_relative_path(raw, label="provenance path")
            except ValueError:
                continue
            absolute = path_from_root(wiki_root, provenance_path).resolve(strict=False)
            try:
                repository_relative = PurePosixPath(*absolute.relative_to(repository_root_path).parts)
            except ValueError:
                continue
            for changed_path in changed:
                shared = min(len(repository_relative.parts), len(changed_path.parts))
                if repository_relative.parts[:shared] == changed_path.parts[:shared]:
                    affected.append(
                        AffectedConcept(
                            path.relative_to(wiki_root).as_posix(),
                            changed_path.as_posix(),
                            kind,
                        )
                    )
    return sorted(set(affected), key=lambda item: (item.concept, item.changed_path))
