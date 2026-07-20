"""Validate curated provenance and map repository changes to concepts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .diagnostics import Diagnostics
from .errors import WheroToolError
from .frontmatter import frontmatter_is_true, read_frontmatter, read_markdown, scalar_text
from .git import head_commit, repository_root, resolve_commit
from .mounts import walk_owned_files
from .paths import parse_relative_path, path_from_root, resolve_within, sha256_file


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


def _provenance_target(
    root: Path,
    concept: Path,
    raw: str,
    kind: str,
    diagnostics: Diagnostics,
    *,
    available: bool,
) -> tuple[PurePosixPath, Path] | None:
    try:
        relative = parse_relative_path(raw, label=f"{kind} provenance path")
        target = (
            path_from_root(root, relative)
            if available
            else resolve_within(root, relative, must_exist=False)
        )
    except WheroToolError as exc:
        diagnostics.error("CURATED_PROVENANCE_PATH", str(exc), concept)
        return None
    return relative, target


def _report_unavailable_provenance(
    diagnostics: Diagnostics,
    concept: Path,
    kind: str,
    relative: PurePosixPath,
    *,
    available: bool,
) -> None:
    reporter = diagnostics.notice if available else diagnostics.error
    if kind == "collected-source":
        code = "CURATED_SOURCE_UNAVAILABLE" if available else "CURATED_SOURCE_MISSING"
    else:
        code = (
            "CURATED_PROVENANCE_UNAVAILABLE"
            if available
            else "CURATED_PROVENANCE_MISSING"
        )
    reporter(code, f"{kind} provenance is unavailable: {relative}", concept)


def _validate_record_reference(
    target: Path,
    relative: PurePosixPath,
    kind: str,
    concept: Path,
    diagnostics: Diagnostics,
) -> bool:
    if not target.is_file():
        diagnostics.error(
            "CURATED_PROVENANCE_REFERENCE",
            f"{kind} provenance must reference a maintained file: {relative}",
            concept,
        )
        return False
    try:
        fields = read_frontmatter(target)
    except WheroToolError as exc:
        diagnostics.error("CURATED_PROVENANCE_REFERENCE", str(exc), concept)
        return False
    if not frontmatter_is_true(fields, "whero_maintenance"):
        diagnostics.error(
            "CURATED_PROVENANCE_REFERENCE_MAINTENANCE",
            f"{kind} provenance reference must set whero_maintenance: true: {relative}",
            concept,
        )
        return False
    return True


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
        if kind in (
            "collected-source",
            "repository-path",
            "discussion",
            "user-authored",
        ):
            field = "reference" if kind in ("discussion", "user-authored") else "path"
            resolved = _provenance_target(
                root,
                concept,
                scalar_text(entry.get(field)),
                kind,
                diagnostics,
                available=available,
            )
            if resolved is None:
                continue
            relative, target = resolved
            if not target.exists():
                _report_unavailable_provenance(
                    diagnostics,
                    concept,
                    kind,
                    relative,
                    available=available,
                )
                continue
            if kind == "collected-source" and not target.is_file():
                diagnostics.error(
                    "CURATED_SOURCE_PATH",
                    f"collected-source provenance must name a regular file: {relative}",
                    concept,
                )
                continue
            if kind in ("discussion", "user-authored") and not _validate_record_reference(
                target,
                relative,
                kind,
                concept,
                diagnostics,
            ):
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
                repository_path = repository_root(target if target.is_dir() else target.parent)
                if repository_path is None:
                    reporter = diagnostics.notice if available else diagnostics.error
                    reporter(
                        "CURATED_PROVENANCE_GIT_UNAVAILABLE"
                        if available
                        else "CURATED_PROVENANCE_GIT_REPOSITORY",
                        f"git_commit requires provenance inside a Git repository: {relative}",
                        concept,
                    )
                    continue
                recorded = resolve_commit(repository_path, expected_commit)
                if recorded is None:
                    reporter = diagnostics.notice if available else diagnostics.error
                    reporter(
                        "CURATED_PROVENANCE_COMMIT_UNAVAILABLE"
                        if available
                        else "CURATED_PROVENANCE_COMMIT",
                        f"recorded Git commit does not exist: {expected_commit}",
                        concept,
                    )
                    continue
                current = head_commit(repository_path)
                if current and current != recorded:
                    reporter = diagnostics.error if strict_stale else diagnostics.warning
                    reporter(
                        "CURATED_PROVENANCE_GIT_STALE",
                        f"repository provenance advanced from {recorded[:12]} to {current[:12]}",
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
                repository_path = (
                    root
                    if repository == "."
                    else (
                        path_from_root(
                            root,
                            parse_relative_path(
                                repository,
                                label="provenance repository",
                            ),
                        )
                        if available
                        else resolve_within(
                            root,
                            parse_relative_path(
                                repository,
                                label="provenance repository",
                            ),
                            must_exist=False,
                        )
                    )
                )
            except WheroToolError as exc:
                diagnostics.error("CURATED_PROVENANCE_REPOSITORY", str(exc), concept)
                continue
            if not repository_path.exists():
                reporter = diagnostics.notice if available else diagnostics.error
                reporter(
                    "CURATED_PROVENANCE_GIT_UNAVAILABLE",
                    f"Git repository is unavailable: {repository}",
                    concept,
                )
                continue
            if not repository_path.is_dir():
                diagnostics.error(
                    "CURATED_PROVENANCE_REPOSITORY",
                    f"provenance repository is not a directory: {repository}",
                    concept,
                )
                continue
            git_root = repository_root(repository_path)
            if git_root is None:
                reporter = diagnostics.notice if available else diagnostics.error
                reporter(
                    "CURATED_PROVENANCE_GIT_UNAVAILABLE",
                    f"Git repository is unavailable: {repository}",
                    concept,
                )
                continue
            if resolve_commit(git_root, commit) is None:
                reporter = diagnostics.notice if available else diagnostics.error
                reporter(
                    "CURATED_PROVENANCE_COMMIT_UNAVAILABLE"
                    if available
                    else "CURATED_PROVENANCE_COMMIT",
                    f"Git commit is unavailable: {commit}",
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
        if not frontmatter_is_true(document.fields, "whero_curated"):
            continue
        for entry in concept_provenance(document.fields):
            kind = scalar_text(entry.get("kind"))
            if kind not in (
                "repository-path",
                "collected-source",
                "discussion",
                "user-authored",
            ):
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
