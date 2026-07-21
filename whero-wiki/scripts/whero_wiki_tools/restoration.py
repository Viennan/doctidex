"""Plan and apply restoration of declared external references."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import WheroToolError
from .git import head_commit, normalize_remote_url, preferred_remote, repository_root
from .frontmatter import read_frontmatter
from .model import WIKI_META_FILENAME, validate_wiki_root, view_status_path
from .mounts import WikiMount, discover_declared_references, parse_gitmodules
from .view_service import execute_view
from .view_status import list_disclosed_symlinks, resolve_recorded_source
from .view_types import OperationResult, ViewRequest


@dataclass(frozen=True)
class RestorationAction:
    reference: WikiMount
    state: str
    operation: str
    source: Path | None = None
    checkout: Path | None = None
    message: str = ""


@dataclass(frozen=True)
class RestorationPlan:
    root: Path
    actions: tuple[RestorationAction, ...]


@dataclass(frozen=True)
class ViewRestorationPlan:
    view_root: Path
    source: Path
    request: ViewRequest
    clone_url: str | None = None
    checkout: Path | None = None
    revision: str | None = None


def _matches_type(path: Path, expected: str | None) -> bool:
    return path.is_file() if expected == "file" else path.is_dir()


def _checkout_path(store: Path, reference: WikiMount) -> Path:
    normalized = normalize_remote_url(reference.git_url or "")
    name = re.sub(r"[^A-Za-z0-9._-]+", "--", normalized).strip("-.")
    return store / (name or reference.path.name)


def _run_git(directory: Path | None, *arguments: str) -> None:
    command = ["git"]
    if directory is not None:
        command.extend(["-C", str(directory)])
    command.extend(arguments)
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise WheroToolError(
            f"Git restoration command failed: {' '.join(command)}: "
            f"{result.stderr.strip() or result.stdout.strip() or 'unknown error'}"
        )


def _plan_filesystem(reference: WikiMount) -> RestorationAction:
    assert reference.index is not None and reference.locator_path is not None
    source = (reference.index.parent / reference.locator_path).resolve(strict=False)
    if not source.exists() or not _matches_type(source, reference.expected_type):
        return RestorationAction(
            reference,
            "present-invalid" if source.exists() else "missing-source",
            "error",
            source=source,
            message=(
                f"filesystem locator is unavailable or has the wrong type: {source}"
            ),
        )
    if os.path.lexists(reference.root):
        try:
            valid = reference.root.resolve(strict=True) == source.resolve(strict=True)
        except OSError:
            valid = False
        valid = valid and _matches_type(reference.root, reference.expected_type)
        return RestorationAction(
            reference,
            "present-valid" if valid else "present-invalid",
            "none" if valid else "error",
            source=source,
            message="filesystem reference is valid" if valid else "target does not match locator",
        )
    return RestorationAction(
        reference,
        "missing",
        "link",
        source=source,
        message=f"create relative symbolic link to {source}",
    )


def _validate_git_checkout(reference: WikiMount, checkout: Path) -> tuple[bool, str]:
    if repository_root(checkout) != checkout.resolve(strict=False):
        return False, "target is not a Git repository root"
    remote = preferred_remote(checkout)
    if reference.git_url and (
        remote is None
        or remote.normalized_url != normalize_remote_url(reference.git_url)
    ):
        return False, "Git remote does not match the declared locator"
    if reference.git_commit and head_commit(checkout) != reference.git_commit:
        return False, "Git HEAD does not match the reviewed revision"
    return True, "Git reference is valid"


def _plan_git(reference: WikiMount, store: Path | None) -> RestorationAction:
    if os.path.lexists(reference.root):
        valid, message = _validate_git_checkout(reference, reference.root)
        return RestorationAction(
            reference,
            "present-valid" if valid else "present-invalid",
            "none" if valid else "error",
            checkout=reference.root,
            message=message,
        )
    if store is None:
        return RestorationAction(
            reference,
            "missing",
            "error",
            message="missing Git reference requires --store",
        )
    checkout = _checkout_path(store.resolve(strict=False), reference)
    if checkout.exists():
        valid, message = _validate_git_checkout(reference, checkout)
        return RestorationAction(
            reference,
            "missing" if valid else "present-invalid",
            "link" if valid else "error",
            source=checkout,
            checkout=checkout,
            message=message if not valid else f"link existing checkout {checkout}",
        )
    return RestorationAction(
        reference,
        "missing",
        "clone",
        source=checkout,
        checkout=checkout,
        message=f"clone {reference.git_url} to {checkout} and link it",
    )


def _plan_submodule(root: Path, reference: WikiMount) -> RestorationAction:
    if reference.root.exists():
        return RestorationAction(
            reference,
            "present-valid",
            "none",
            message="Git submodule path is present",
        )
    repository = repository_root(root)
    if repository is None:
        return RestorationAction(
            reference,
            "missing",
            "error",
            message="Git submodule restoration requires a containing repository",
        )
    repository_path = PurePosixPath(*reference.root.relative_to(repository).parts)
    if repository_path not in parse_gitmodules(repository):
        return RestorationAction(
            reference,
            "present-invalid",
            "error",
            message=f"Git submodule is not declared in {repository / '.gitmodules'}",
        )
    return RestorationAction(
        reference,
        "missing",
        "submodule",
        checkout=repository,
        message=f"initialize Git submodule {reference.path}",
    )


def plan_restoration(raw_root: Path, *, store: Path | None = None) -> RestorationPlan:
    root = validate_wiki_root(raw_root)
    references, problems = discover_declared_references(root)
    if problems:
        raise WheroToolError(problems[0])
    actions: list[RestorationAction] = []
    for reference in references:
        if reference.locator_kind == "filesystem":
            action = _plan_filesystem(reference)
        elif reference.locator_kind == "git":
            action = _plan_git(reference, store)
        elif reference.locator_kind == "git-submodule":
            action = _plan_submodule(root, reference)
        else:
            action = RestorationAction(
                reference,
                "present-invalid",
                "error",
                message="reference has no supported locator",
            )
        actions.append(action)
    return RestorationPlan(root, tuple(actions))


def apply_restoration(plan: RestorationPlan) -> tuple[str, ...]:
    errors = [action for action in plan.actions if action.operation == "error"]
    if errors:
        first = errors[0]
        raise WheroToolError(
            f"cannot apply restoration for {first.reference.path}: {first.message}"
        )
    messages: list[str] = []
    for action in plan.actions:
        reference = action.reference
        if action.operation == "none":
            messages.append(f"valid {reference.path}: {action.message}")
            continue
        if action.operation == "submodule":
            assert action.checkout is not None
            repository_path = reference.root.relative_to(action.checkout).as_posix()
            _run_git(
                action.checkout,
                "submodule",
                "update",
                "--init",
                "--",
                repository_path,
            )
            messages.append(f"restored {reference.path} as a Git submodule")
            continue
        assert action.source is not None
        if action.operation == "clone":
            assert reference.git_url is not None
            action.source.parent.mkdir(parents=True, exist_ok=True)
            _run_git(None, "clone", "--", reference.git_url, str(action.source))
            if reference.git_commit:
                _run_git(action.source, "checkout", "--detach", reference.git_commit)
        reference.root.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(reference.root):
            raise WheroToolError(f"restoration target appeared after planning: {reference.root}")
        relative_target = os.path.relpath(action.source, start=reference.root.parent)
        reference.root.symlink_to(
            relative_target,
            target_is_directory=action.source.is_dir(),
        )
        messages.append(f"restored {reference.path} -> {relative_target}")
    return tuple(messages)


def plan_view_restoration(
    raw_view: Path,
    *,
    source: Path | None = None,
    store: Path | None = None,
) -> ViewRestorationPlan:
    view_root = raw_view.expanduser().resolve(strict=True)
    status = view_status_path(view_root)
    if status is None:
        raise WheroToolError(f"directory is not a Whero Wiki View: {view_root}")
    fields = read_frontmatter(status)
    recorded = resolve_recorded_source(str(fields.get("source", "")), view_root)
    selected_source: Path
    clone_url: str | None = None
    checkout: Path | None = None
    revision = str(fields.get("source_commit", "")).strip() or None
    if source is not None:
        selected_source = source.expanduser().resolve(strict=True)
    elif recorded.is_dir():
        selected_source = recorded
    else:
        remote = str(fields.get("source_git_remote_url", "")).strip()
        if not remote or store is None:
            raise WheroToolError(
                "View source is unavailable; pass --source or provide --store for "
                "recorded Git source restoration"
            )
        reference = WikiMount(
            PurePosixPath(view_root.name),
            recorded,
            "view-source",
            git_commit=revision,
            git_url=remote,
            projection="view",
            content="whero-wiki",
            locator_kind="git",
        )
        checkout = _checkout_path(store.expanduser().resolve(strict=False), reference)
        wiki_path = PurePosixPath(str(fields.get("source_git_path", ".")))
        selected_source = (
            checkout
            if wiki_path == PurePosixPath(".")
            else checkout.joinpath(*wiki_path.parts)
        )
        clone_url = remote if not checkout.exists() else None
        if checkout.exists() and not selected_source.is_dir():
            raise WheroToolError(
                f"restored checkout does not contain recorded Wiki path: {selected_source}"
            )
    raw_requested = fields.get("requested_selections")
    if isinstance(raw_requested, list) and all(
        isinstance(item, str) for item in raw_requested
    ):
        requested = tuple(raw_requested)
    else:
        requested = tuple(
            item
            for item in list_disclosed_symlinks(view_root)
            if item != WIKI_META_FILENAME
        )
    if not requested:
        raise WheroToolError(f"View metadata contains no restorable selections: {status}")
    try:
        threshold = float(fields.get("collapse_threshold", 80))
    except (TypeError, ValueError) as exc:
        raise WheroToolError(f"invalid collapse_threshold in {status}") from exc
    request = ViewRequest(
        source=selected_source,
        target=view_root.parent,
        view_name=view_root.name,
        includes=requested,
        include_files=(),
        collapse_threshold=threshold,
        allow_path_relocation=True,
    )
    return ViewRestorationPlan(
        view_root,
        selected_source,
        request,
        clone_url,
        checkout,
        revision,
    )


def apply_view_restoration(plan: ViewRestorationPlan) -> OperationResult:
    if plan.clone_url:
        assert plan.checkout is not None
        plan.checkout.parent.mkdir(parents=True, exist_ok=True)
        _run_git(None, "clone", "--", plan.clone_url, str(plan.checkout))
        if plan.revision:
            _run_git(plan.checkout, "checkout", "--detach", plan.revision)
    if not plan.source.is_dir():
        raise WheroToolError(f"restored View source is unavailable: {plan.source}")
    return execute_view(plan.request)
