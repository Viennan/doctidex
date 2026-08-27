"""Read-only validation of the doctidex work model and directory tree."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from whero.doctidex.errors import CommandFailure
from whero.doctidex.initialization import RUNTIME_IGNORE_PATHS, WORKSPACE_ARTIFACTS
from whero.doctidex.model import InlineAnnotation, Installation, ModelFormatError, RuntimeState
from whero.doctidex.model_view import (
    MarkdownLink,
    parse_inline_annotation,
    resolve_inline_annotation_boundary,
    scan_markdown_links,
)
from whero.doctidex.paths import normalize_repo_path, repo_path_to_fs
from whero.doctidex.root_index import ROOT_INDEX_FRONTMATTER, root_index_frontmatter, root_index_matches
from whero.doctidex.store.files import StoreFailure
from whero.doctidex.store.model_view import RuntimeModelView
from whero.doctidex.store.runtime import RecoveryRequired, RuntimeStore


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """The command result independent of the public JSON envelope."""

    valid: bool
    scope: str
    diagnostics: tuple[dict[str, object], ...]


def validate(
    store: RuntimeStore,
    *,
    subdir: str | None = None,
    model_structure: bool = False,
) -> ValidationResult:
    """Validate one workspace without changing state.

    ``model_structure`` retains only the root identity and repository-level
    work-model checks.
    """

    scope = _scope(store.git_root, None if model_structure else subdir)
    check = _check_model(store, scope)
    diagnostics = list(check.diagnostics)
    if model_structure:
        if not check.requires_recovery:
            diagnostics.extend(_index_diagnostics(store.git_root))
        diagnostics.sort(key=lambda item: (str(item.get("path", "")), int(item.get("line", 0)), str(item["rule"])))
        return ValidationResult(not diagnostics, scope, tuple(diagnostics))
    if check.model is None:
        diagnostics.sort(key=lambda item: (str(item.get("path", "")), int(item.get("line", 0)), str(item["rule"])))
        return ValidationResult(not diagnostics, scope, tuple(diagnostics))
    diagnostics.extend(_index_diagnostics(store.git_root))
    # Content scanning relies on complete, valid work-model files. Any model
    # diagnostic means those files are not trustworthy, so skip the scan.
    if not check.diagnostics:
        diagnostics.extend(_content_diagnostics(store.git_root, check.model, scope))
    diagnostics.sort(key=lambda item: (str(item.get("path", "")), int(item.get("line", 0)), str(item["rule"])))
    return ValidationResult(not diagnostics, scope, tuple(diagnostics))


@dataclass(frozen=True, slots=True)
class _ModelCheck:
    """The model snapshot and diagnostics shared by validation entry points."""

    model: RuntimeModelView | None
    diagnostics: tuple[dict[str, object], ...]
    requires_recovery: bool = False


def _check_model(store: RuntimeStore, scope: str) -> _ModelCheck:
    diagnostics: list[dict[str, object]] = []
    if not store.workspace_path.is_dir():
        diagnostics.append(
            _model_diagnostic(
                [
                    {
                        "code": "workspace.uninitialized",
                        "path": "/.doctidex-git",
                        "message": "The doctidex-git work model has not been initialized.",
                        "details": {"required-command": "init"},
                    }
                ],
                content_scan="skipped",
            )
        )
        return _ModelCheck(None, tuple(diagnostics))

    try:
        with store.read_diagnostic_transaction() as transaction:
            pending = transaction.pending_journals
            unfinished = tuple(journal for journal in pending if journal.state in {"prepared", "publishing"})
            if unfinished:
                diagnostics.append(
                    _model_diagnostic(
                        [
                            {
                                "code": "transaction.recovery.required",
                                "path": f"/.doctidex-git/.transactions/{journal.transaction_id}/journal.json",
                                "message": (
                                    "A RuntimeStore transaction must be recovered before validation can continue."
                                ),
                                "details": {
                                    "transaction-id": journal.transaction_id,
                                    "journal-path": (
                                        f"/.doctidex-git/.transactions/{journal.transaction_id}/journal.json"
                                    ),
                                    "state": journal.state,
                                },
                            }
                            for journal in unfinished
                        ],
                        content_scan="skipped",
                    )
                )
                return _ModelCheck(None, tuple(diagnostics), requires_recovery=True)
            state = transaction.state
            model = transaction.model_view()
            if scope != "/" and model.first_boundary(scope) is not None:
                raise _scope_failure(store.git_root, scope, "outside-current-tree")
    except (RecoveryRequired, StoreFailure):
        raise
    except ModelFormatError as exc:
        state_file = store.workspace_path / exc.artifact
        if not state_file.is_file():
            violation = {
                "code": "workspace.artifact.missing",
                "path": f"/.doctidex-git/{exc.artifact}",
                "message": "A required doctidex-git workspace artifact is missing.",
                "details": {"required-artifact": exc.artifact},
            }
        else:
            violation = {
                "code": "state-file.malformed",
                "path": f"/.doctidex-git/{exc.artifact}",
                "message": "A doctidex-git state file does not match its documented structure.",
                "details": {
                    "state-file": f"/.doctidex-git/{exc.artifact}",
                    "expected-shape": exc.expected_shape,
                },
            }
        violation = _specific_model_violation(store.workspace_path, violation)
        diagnostics.append(_model_diagnostic([violation], content_scan="skipped"))
        return _ModelCheck(None, tuple(diagnostics))

    violations = [*_model_violations(store.git_root, state), *_gitignore_violations(store.git_root, state)]
    if violations:
        diagnostics.append(_model_diagnostic(violations, content_scan="skipped"))
    return _ModelCheck(model, tuple(diagnostics))


def _specific_model_violation(workspace: Path, fallback: dict[str, object]) -> dict[str, object]:
    """Preserve model meaning for projection mistakes rejected by the parser."""

    artifact = str(fallback.get("details", {}).get("state-file", "")).rsplit("/", 1)[-1]
    path = workspace / artifact
    try:
        document = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return fallback
    if artifact == "imports.json" and isinstance(document, list):
        for index, record in enumerate(document):
            if isinstance(record, dict) and record.get("tracked") is False:
                return {
                    "code": "installation.projection.misplaced",
                    "path": "/.doctidex-git/imports.json",
                    "message": "An untracked installation is stored in the tracked projection.",
                    "details": {
                        "install-id": record.get("install-id"),
                        "actual-state-file": "/.doctidex-git/imports.json",
                        "expected-state-file": "/.doctidex-git/runtime.json",
                        "record-index": index,
                    },
                }
    if artifact == "runtime.json" and isinstance(document, dict):
        runtime_imports = document.get("imports")
        if isinstance(runtime_imports, list):
            for index, record in enumerate(runtime_imports):
                if isinstance(record, dict) and record.get("tracked") is True:
                    return {
                        "code": "installation.projection.misplaced",
                        "path": "/.doctidex-git/runtime.json",
                        "message": "A tracked installation is stored in the runtime projection.",
                        "details": {
                            "install-id": record.get("install-id"),
                            "actual-state-file": "/.doctidex-git/runtime.json",
                            "expected-state-file": "/.doctidex-git/imports.json",
                            "record-index": index,
                        },
                    }
    if artifact == "boundary-set.json" and isinstance(document, list):
        for index, record in enumerate(document):
            if isinstance(record, dict) and record.get("type") != "custom":
                return {
                    "code": "boundary-point.custom.invalid",
                    "path": "/.doctidex-git/boundary-set.json",
                    "message": "The tracked boundary-set contains a non-custom boundary point.",
                    "details": {
                        "boundary-path": record.get("path"),
                        "reason": "non-custom-type",
                        "record-index": index,
                    },
                }
    return fallback


def _scope(git_root: Path, value: str | None) -> str:
    if value is None:
        return "/"
    try:
        scope = normalize_repo_path(value, parameter="--subdir")
    except CommandFailure as exc:
        raise _scope_failure(git_root, value, "outside-repository") from exc
    path = repo_path_to_fs(git_root, scope)
    workspace = "/.doctidex-git"
    if scope == workspace or scope.startswith(f"{workspace}/"):
        raise _scope_failure(git_root, scope, "workspace-internal")
    if not path.is_dir():
        raise _scope_failure(git_root, scope, "not-directory")
    if not os.access(path, os.R_OK):
        raise _scope_failure(git_root, scope, "unreadable")
    return scope


def _scope_failure(git_root: Path, path: str, reason: str) -> CommandFailure:
    return CommandFailure(
        code="validation.scope.unavailable",
        summary="The requested validation scope is not available.",
        subject={"kind": "validation-scope", "path": path},
        details={"repos-path": str(git_root), "operation": "validate", "reason": reason},
    )


def _model_violations(git_root: Path, state: RuntimeState) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    for artifact in WORKSPACE_ARTIFACTS:
        if not (git_root / ".doctidex-git" / artifact).is_file():
            violations.append(
                {
                    "code": "workspace.artifact.missing",
                    "path": f"/.doctidex-git/{artifact}",
                    "message": "A required doctidex-git workspace artifact is missing.",
                    "details": {"required-artifact": artifact},
                }
            )

    def duplicate(items: tuple[object, ...], attribute: str, artifact: str) -> None:
        values: dict[object, list[int]] = {}
        for index, item in enumerate(items):
            values.setdefault(getattr(item, attribute), []).append(index)
        for value, indexes in values.items():
            if len(indexes) > 1:
                violations.append(
                    {
                        "code": "installation.identity.conflict"
                        if attribute in {"install_id", "install_path"}
                        else "state-record.invalid",
                        "path": f"/.doctidex-git/{artifact}",
                        "message": "Multiple work-model records claim the same identity.",
                        "details": {
                            "identity-field": attribute.replace("_", "-"),
                            "identity-value": value,
                            "conflicting-state-files": [f"/.doctidex-git/{artifact}"],
                            "record-indexes": indexes,
                        },
                    }
                )

    duplicate(state.installations, "install_id", "imports.json")
    duplicate(state.installations, "install_path", "imports.json")
    duplicate(state.refs, "target_dir", "import-refs.json")
    duplicate(state.worktrees, "work_path", "runtime.json")
    duplicate(state.custom_boundary_points, "path", "boundary-set.json")

    share_by_commit: dict[tuple[str, str], list[int]] = {}
    for index, item in enumerate(state.installation_shares):
        share_by_commit.setdefault((item.git_url, item.commit_hash), []).append(index)
    for key, indexes in share_by_commit.items():
        if len(indexes) > 1:
            violations.append(
                {
                    "code": "state-record.invalid",
                    "path": "/.doctidex-git/runtime.json",
                    "message": "Multiple installation shares claim the same source and commit.",
                    "details": {
                        "identity-field": "installation-share-commit",
                        "identity-value": {"git-url": key[0], "commit-hash": key[1]},
                        "conflicting-state-files": ["/.doctidex-git/runtime.json"],
                        "record-indexes": indexes,
                    },
                }
            )
    installations = {item.install_id: item for item in state.installations}
    for reference in state.refs:
        installation = installations.get(reference.install_id)
        if installation is None:
            violations.append(
                {
                    "code": "ref.installation.missing",
                    "path": "/.doctidex-git/import-refs.json",
                    "message": "A managed reference has no tracked installation record.",
                    "details": {"install-id": reference.install_id, "target-dir": reference.target_dir},
                }
            )
        elif not installation.tracked:
            violations.append(
                {
                    "code": "ref.installation.untracked",
                    "path": "/.doctidex-git/import-refs.json",
                    "message": "A managed reference points to an untracked installation.",
                    "details": {"install-id": reference.install_id, "target-dir": reference.target_dir},
                }
            )
    managed: dict[str, str] = {}
    for item in state.installations:
        managed[item.install_path] = f"installation:{item.install_id}"
    for reference in state.refs:
        if reference.target_dir in managed:
            violations.append(
                {
                    "code": "managed-path.conflict",
                    "path": reference.target_dir,
                    "message": "A managed path is assigned incompatible work-model responsibilities.",
                    "details": {"managed-path": reference.target_dir, "owners": [managed[reference.target_dir], "ref"]},
                }
            )
        managed[reference.target_dir] = f"ref:{reference.install_id}"
    for worktree in state.worktrees:
        if worktree.work_path in managed:
            violations.append(
                {
                    "code": "managed-path.conflict",
                    "path": worktree.work_path,
                    "message": "A managed path is assigned incompatible work-model responsibilities.",
                    "details": {
                        "managed-path": worktree.work_path,
                        "owners": [managed[worktree.work_path], "worktree"],
                    },
                }
            )
    for item in state.installations:
        target = repo_path_to_fs(git_root, item.install_path)
        if not item.tracked and not target.exists():
            violations.append(
                {
                    "code": "installation.worktree.missing",
                    "path": item.install_path,
                    "message": "An untracked installation directory is missing.",
                    "details": {"install-id": item.install_id, "install-path": item.install_path, "tracked": False},
                }
            )
        elif target.exists() and not _installation_matches(target, item):
            violations.append(
                {
                    "code": "installation.worktree.inconsistent",
                    "path": item.install_path,
                    "message": "An installation directory does not represent its recorded Git source and revision.",
                    "details": {
                        "install-id": item.install_id,
                        "install-path": item.install_path,
                        "expected-git-url": item.git_url,
                        "expected-commit-hash": item.commit_hash,
                    },
                }
            )
        elif target.exists() and _git_worktree_dirty(target):
            violations.append(
                {
                    "code": "installation.worktree.dirty",
                    "path": item.install_path,
                    "message": "An installation directory contains uncommitted changes.",
                    "details": {"install-id": item.install_id, "install-path": item.install_path},
                }
            )
    installations_by_id = {item.install_id: item for item in state.installations}
    for share in state.installation_shares:
        share_path = repo_path_to_fs(git_root, share.install_path)
        if not share_path.exists() or not _is_git_worktree(share_path):
            violations.append(
                {
                    "code": "installation.share.worktree.invalid",
                    "path": share.install_path,
                    "message": "An installation share does not have a valid physical worktree.",
                    "details": {
                        "git-url": share.git_url,
                        "commit-hash": share.commit_hash,
                        "install-path": share.install_path,
                    },
                }
            )
        for install_id in share.install_ids:
            installation = installations_by_id.get(install_id)
            if installation is None:
                violations.append(
                    {
                        "code": "installation.share.reference.missing",
                        "path": share.install_path,
                        "message": "An installation share references an unknown Installation.",
                        "details": {
                            "git-url": share.git_url,
                            "commit-hash": share.commit_hash,
                            "install-id": install_id,
                        },
                    }
                )
                continue
            target = repo_path_to_fs(git_root, installation.install_path)
            if installation.branch or installation.tag:
                if not target.is_symlink() or target.resolve(strict=False) != share_path.resolve(strict=False):
                    violations.append(
                        {
                            "code": "installation.share.selector.invalid",
                            "path": installation.install_path,
                            "message": "A selector Installation does not link to its share worktree.",
                            "details": {
                                "install-id": installation.install_id,
                                "install-path": installation.install_path,
                                "share-install-path": share.install_path,
                            },
                        }
                    )
            elif installation.install_path != share.install_path:
                violations.append(
                    {
                        "code": "installation.share.commit-path.invalid",
                        "path": installation.install_path,
                        "message": "A commit Installation does not use its share's physical path.",
                        "details": {
                            "install-id": installation.install_id,
                            "install-path": installation.install_path,
                            "share-install-path": share.install_path,
                        },
                    }
                )
    for reference in state.refs:
        installation = installations.get(reference.install_id)
        if installation is None:
            continue
        source = repo_path_to_fs(git_root, installation.install_path) / reference.src_sub_dir.lstrip("/")
        target = repo_path_to_fs(git_root, reference.target_dir)
        if not source.exists() and repo_path_to_fs(git_root, installation.install_path).exists():
            violations.append(
                {
                    "code": "ref.source.unavailable",
                    "path": reference.target_dir,
                    "message": "A managed reference source is missing from its installation.",
                    "details": {
                        "install-id": installation.install_id,
                        "install-path": installation.install_path,
                        "src-sub-dir": reference.src_sub_dir,
                        "target-dir": reference.target_dir,
                    },
                }
            )
        if not target.is_symlink() or target.resolve(strict=False) != source.resolve(strict=False):
            violations.append(
                {
                    "code": "ref.target.inconsistent",
                    "path": reference.target_dir,
                    "message": "A managed reference does not point to its recorded installation source.",
                    "details": {
                        "install-id": installation.install_id,
                        "target-dir": reference.target_dir,
                        "expected-source": reference.src_sub_dir,
                        "actual-target": os.readlink(target) if target.is_symlink() else None,
                    },
                }
            )
    for worktree in state.worktrees:
        target = repo_path_to_fs(git_root, worktree.work_path)
        if not target.exists() or not _worktree_matches(target, worktree.url):
            violations.append(
                {
                    "code": "worktree.physical-state.invalid",
                    "path": worktree.work_path,
                    "message": "A recorded worktree is missing or no longer represents its Git source.",
                    "details": {"work-path": worktree.work_path, "reason": "missing-or-wrong-git-source"},
                }
            )
    return violations


def _installation_matches(target: Path, installation: Installation) -> bool:
    if not _is_git_worktree(target):
        return False
    try:
        head = _git_output(target, "rev-parse", "HEAD")
        remote = _git_output(target, "remote", "get-url", "origin")
    except OSError:
        return False
    return head == installation.commit_hash and remote == installation.git_url


def _is_git_worktree(target: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _worktree_matches(target: Path, git_url: str) -> bool:
    if not _is_git_worktree(target):
        return False
    try:
        return _git_output(target, "remote", "get-url", "origin") == git_url
    except (OSError, subprocess.CalledProcessError):
        return False


def _git_worktree_dirty(target: Path) -> bool:
    """Return whether a Git worktree has tracked or untracked uncommitted changes."""

    try:
        result = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(result.stdout.strip())


def _git_output(target: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(target), *arguments], check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _index_diagnostics(git_root: Path) -> list[dict[str, object]]:
    path = git_root / "index.md"
    if not path.is_file():
        return [
            _diagnostic(
                "index.conforms",
                "/index.md",
                "The doctidex root index.md is missing.",
                {"expected": "file with doctidex root frontmatter", "actual": None},
            )
        ]
    try:
        content = path.read_text()
    except OSError:
        return [
            _diagnostic(
                "index.conforms",
                "/index.md",
                "The doctidex root index.md cannot be read.",
                {"expected": "readable file", "actual": "unreadable"},
            )
        ]
    frontmatter = root_index_frontmatter(content)
    if not root_index_matches(frontmatter):
        return [
            _diagnostic(
                "index.conforms",
                "/index.md",
                "The root index.md does not declare a doctidex root.",
                {"expected": ROOT_INDEX_FRONTMATTER, "actual": frontmatter},
            )
        ]
    return []


def _gitignore_violations(git_root: Path, state: RuntimeState) -> list[dict[str, object]]:
    required = [
        *RUNTIME_IGNORE_PATHS,
        *(item.work_path for item in state.worktrees if not item.work_path.startswith("/.doctidex-git/worktrees/")),
    ]
    violations: list[dict[str, object]] = []
    for path in required:
        candidate = path.lstrip("/") or "."
        if not path.endswith("/") and path not in {"/.doctidex-git/.lock", "/.doctidex-git/runtime.json"}:
            candidate = f"{candidate}/"
        try:
            result = subprocess.run(
                ["git", "-C", str(git_root), "check-ignore", "--quiet", "--no-index", "--", candidate],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            result = None
        if result is None or result.returncode != 0:
            violations.append(
                {
                    "code": "workspace.runtime-protection.invalid"
                    if path.startswith("/.doctidex-git")
                    else "worktree.path-protection.invalid",
                    "path": path,
                    "message": "A doctidex-git managed path is not protected by Git ignore.",
                    "details": {"artifact-path": path, "required-protection": "git-ignore", "work-path": path},
                }
            )
    return violations


def _content_diagnostics(git_root: Path, model: RuntimeModelView, scope: str) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for link in scan_markdown_links(git_root, model, scope=scope):
        if _is_external(link.link_path):
            continue
        if link.target_path is None:
            diagnostics.append(
                _link_diagnostic(
                    "link.path.conforms", link, "The local link cannot be normalized.", {"reason": "outside-repository"}
                )
            )
            continue
        target = repo_path_to_fs(git_root, link.target_path)
        missing_install = bool(
            link.installation and not repo_path_to_fs(git_root, link.installation.install_path).exists()
        )
        if not target.exists() and not missing_install:
            diagnostics.append(
                _link_diagnostic(
                    "link.target.exists",
                    link,
                    "The local link target does not exist.",
                    {"target-path": link.target_path},
                )
            )
        if link.boundary_point is not None:
            annotation = _annotation_for_link(git_root / link.path.lstrip("/"), link.source_end)
            expected = link.boundary_point.path
            annotated_boundary = (
                resolve_inline_annotation_boundary(link.path, link.link_path, annotation)
                if annotation is not None
                else None
            )
            if annotated_boundary != expected:
                details: dict[str, object] = {
                    "link-path": link.link_path,
                    "expected-cross-boundary-point": expected,
                    "reason": "missing-or-mismatched",
                }
                if annotation is not None:
                    details["actual-cross-boundary-point"] = annotation.cross_boundary_point
                diagnostics.append(
                    _link_diagnostic(
                        "link.annotation.required",
                        link,
                        "A cross-boundary link requires a matching doctidex annotation.",
                        details,
                    )
                )
            if link.boundary_point.type == "import" and link.installation is not None and not link.installation.tracked:
                diagnostics.append(
                    _link_diagnostic(
                        "import.link.tracked",
                        link,
                        "A link crossing an import must use a tracked installation.",
                        {
                            "install-id": link.installation.install_id,
                            "install-path": link.installation.install_path,
                            "tracked": False,
                        },
                    )
                )
    for worktree in model.worktrees:
        if not _within(scope, worktree.work_path):
            continue
        target = repo_path_to_fs(git_root, worktree.work_path)
        if target.exists() and _is_git_worktree(target) and _git_worktree_dirty(target):
            diagnostics.append(
                _diagnostic(
                    "worktree.clean",
                    worktree.work_path,
                    "A managed worktree contains uncommitted changes.",
                    {"work-path": worktree.work_path},
                )
            )
    return diagnostics


def _within(scope: str, path: str) -> bool:
    return scope == "/" or path == scope or path.startswith(f"{scope.rstrip('/')}/")


def _is_external(value: str) -> bool:
    parsed = urlsplit(value)
    return bool(parsed.scheme or parsed.netloc)


def _annotation_for_link(path: Path, source_end: int | None) -> InlineAnnotation | None:
    if source_end is None:
        return None
    try:
        content = path.read_text()
    except OSError:
        return None
    return parse_inline_annotation(content, source_end)


def _model_diagnostic(violations: list[dict[str, object]], *, content_scan: str) -> dict[str, object]:
    return _diagnostic(
        "work-model.valid",
        "/.doctidex-git",
        "The doctidex-git work model has validation violations.",
        {"violations": violations, "content-scan": content_scan},
    )


def _link_diagnostic(rule: str, link: MarkdownLink, message: str, details: dict[str, object]) -> dict[str, object]:
    return _diagnostic(rule, link.path, message, {"link-path": link.link_path, **details}, line=link.line)


def _diagnostic(
    rule: str, path: str, message: str, details: dict[str, object], *, line: int | None = None
) -> dict[str, object]:
    result: dict[str, object] = {"rule": rule, "path": path, "message": message, "details": details}
    if line is not None:
        result["line"] = line
    return result


__all__ = ["ValidationResult", "validate"]
