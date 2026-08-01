from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from whero.doctidex.errors import DoctidexError
from whero.doctidex.protocol.root import RootContext
from whero.doctidex.results import envelope, finding, paginate_lists, query_identity

from .external import ExternalService
from .runner import git
from .source import (
    ResolvedSource,
    RevisionSelector,
    add_detached_worktree,
    canonical_source,
    ensure_source_cache,
    resolve_local_revision,
    resolve_source,
    sanitize_url,
)
from .storage import RootStorage, source_cache, source_id, source_mutation


@dataclass(frozen=True, slots=True)
class WorktreeSource:
    kind: str
    gitdir: Path
    identity: str
    source_url: str | None
    repository_relative_path: str
    network: bool = False
    resolved: ResolvedSource | None = None


class WorktreeService:
    def __init__(self, context: RootContext) -> None:
        self.context = context
        self.root = context.root
        self.storage = RootStorage(self.root)

    def open(self, value: str, selector: RevisionSelector) -> dict[str, Any]:
        source = self._classify(value, selector)
        network = source.network
        with source_mutation(source.identity, operation="worktree_open"):
            if source.resolved is not None:
                _, cache_network = ensure_source_cache(source.resolved)
                network = network or cache_network
            base_commit = resolve_local_revision(source.gitdir, selector, operation="worktree_open")
            identifier = "w-" + uuid.uuid4().hex[:20]
            internal = f"/.doctidex/git/worktrees/{identifier}"
            path = self.storage.worktree_directory / identifier
            runtime = self.storage.read_runtime()
            candidate_count = sum(
                1
                for item in runtime["worktrees"].values()
                if item.get("source_identity") == source.identity and item.get("base_commit") == base_commit
            )
            record = {
                "worktree_id": identifier,
                "source_kind": source.kind,
                "source_identity": source.identity,
                "source_url": source.source_url,
                "gitdir": str(source.gitdir),
                "revision_selector": selector.as_dict(),
                "base_commit": base_commit,
                "root_internal_path": internal,
                "worktree_path": str(path),
                "repository_relative_path": source.repository_relative_path,
            }
            with self.storage.mutation():
                changed, _ = self.storage.ensure_host_layout()
                add_detached_worktree(source.gitdir, path, base_commit, operation="worktree_open")
                self.storage.update_runtime(lambda data: data["worktrees"].__setitem__(identifier, record))
                changed.extend([path, self.storage.runtime_path])

        item = _worktree_item(record)
        status = "warning" if candidate_count else "ok"
        notices = []
        if candidate_count:
            notices.append(
                finding(
                    "worktree",
                    "warning",
                    "worktree_reuse_candidate",
                    "Another managed worktree has the same source and base commit.",
                    path=str(path),
                    actions=["Keep the new isolation only when the task requires a separate writable result."],
                )
            )
        return envelope(
            "worktree_open",
            status=status,
            result="A detached writable worktree was created.",
            root=str(self.root),
            changed=[str(item) for item in dict.fromkeys(changed)],
            network=network,
            findings=notices,
            worktree=item,
            reuse_candidate_count=candidate_count,
        )

    def list(
        self,
        *,
        source_filter: str | None,
        worktree_filter: Path | None,
        limit: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        runtime = self.storage.read_runtime()
        records = list(runtime["worktrees"].values())
        filter_identity = None
        if source_filter is not None:
            filter_identity = _source_filter_identity(source_filter, self.root)
            records = [item for item in records if item.get("source_identity") == filter_identity]
        if worktree_filter is not None:
            exact = str(worktree_filter.absolute())
            records = [item for item in records if item.get("worktree_path") == exact]
        items = [_worktree_item(item) for item in records]
        items.sort(key=lambda item: item["worktree_path"])
        state = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
        identity = query_identity(
            "worktree_list",
            root=str(self.root),
            source=filter_identity,
            worktree=str(worktree_filter.absolute()) if worktree_filter else None,
            limit=limit,
        )
        try:
            pages, collection = paginate_lists(
                {"items": items}, limit=limit, identity=identity, state=state, cursor=cursor
            )
        except ValueError as exc:
            raise DoctidexError(
                "The worktree list cursor no longer matches the managed state.",
                operation="worktree_list",
                affected=[str(self.root)],
                actions=["Restart worktree list from the first page."],
                code="cursor_invalid",
                domain="worktree",
            ) from exc
        unavailable = any(item["state"] == "unavailable" for item in items)
        return envelope(
            "worktree_list",
            status="warning" if unavailable else "ok",
            result="Managed worktrees listed.",
            root=str(self.root),
            collection=collection,
            items=pages["items"],
        )

    def close(self, path: Path) -> dict[str, Any]:
        exact = path.absolute()
        runtime = self.storage.read_runtime()
        pair = next(
            (
                (identifier, item)
                for identifier, item in runtime["worktrees"].items()
                if item.get("worktree_path") == str(exact)
            ),
            None,
        )
        if pair is None:
            raise DoctidexError(
                "The exact path is not a managed doctidex-git worktree.",
                operation="worktree_close",
                affected=[str(exact)],
                actions=["Pass the exact worktree_path returned by worktree list."],
                code="worktree_unmanaged",
                domain="worktree",
                path=str(exact),
            )
        identifier, record = pair
        item = _worktree_item(record)
        if item["state"] == "unavailable":
            raise DoctidexError(
                "The managed worktree is unavailable and was preserved.",
                operation="worktree_close",
                affected=[str(exact)],
                actions=["Inspect the Git worktree metadata and restore the path before closing."],
                code="worktree_unavailable",
                domain="worktree",
                path=str(exact),
                fields={"worktree": item},
            )
        if item["state"] == "changed":
            raise DoctidexError(
                "The managed worktree has Git changes and was preserved.",
                operation="worktree_close",
                affected=[str(exact)],
                actions=["Use native Git to deliver, restore, or explicitly retain the changes."],
                requires_user="git_action",
                code="worktree_changed",
                domain="worktree",
                path=str(exact),
                fields={"worktree": item},
            )
        with source_mutation(record["source_identity"], operation="worktree_close"):
            with self.storage.mutation():
                git(
                    ["--git-dir", record["gitdir"], "worktree", "remove", str(exact)],
                    operation="worktree_close",
                )
                self.storage.update_runtime(lambda data: data["worktrees"].pop(identifier, None))
        return envelope(
            "worktree_close",
            result="The clean managed worktree was closed.",
            root=str(self.root),
            changed=[str(exact)],
            worktree=item,
        )

    def _classify(self, value: str, selector: RevisionSelector) -> WorktreeSource:
        path = Path(value).expanduser()
        if path.exists():
            path = path.absolute()
            try:
                parsed = ExternalService(self.context).link_parse(path)
            except DoctidexError:
                parsed = None
            if parsed and parsed.get("managed") and parsed.get("target_state") == "available":
                working = Path(parsed["working_path"])
                gitdir = _common_gitdir(working)
                if gitdir is None:
                    raise _source_error(value)
                return WorktreeSource(
                    "managed_path",
                    gitdir,
                    str(gitdir),
                    parsed.get("source_url"),
                    parsed.get("repository_relative_path") or ".",
                )
            if path.is_file():
                gitdir = _gitfile_target(path)
                if gitdir is None:
                    raise _source_error(value)
                return WorktreeSource("gitfile", gitdir, str(gitdir), _remote_url(gitdir), ".")
            bare = git(["-C", str(path), "rev-parse", "--is-bare-repository"], operation="worktree_open", check=False)
            if bare.returncode == 0 and bare.stdout.strip() == "true":
                gitdir = path.resolve(strict=False)
                return WorktreeSource("bare_gitdir", gitdir, str(gitdir), _remote_url(gitdir), ".")
            top = git(["-C", str(path), "rev-parse", "--show-toplevel"], operation="worktree_open", check=False)
            if top.returncode == 0:
                repository = Path(top.stdout.strip()).absolute()
                gitdir = _common_gitdir(path)
                assert gitdir is not None
                suffix = path.relative_to(repository).as_posix() if path != repository else "."
                return WorktreeSource("working_tree", gitdir, str(gitdir), _remote_url(gitdir), suffix)
            raise _source_error(value)

        resolved = resolve_source(value, selector, cwd=Path.cwd())
        cache = source_cache(resolved.canonical)
        return WorktreeSource(
            "url",
            cache,
            resolved.canonical,
            resolved.public_url,
            ".",
            resolved.network,
            resolved,
        )


class CacheService:
    def clean(self, url: str, *, apply: bool) -> dict[str, Any]:
        if not _absolute_or_remote(url):
            raise DoctidexError(
                "Cache cleanup requires an absolute local repository path or remote URL.",
                operation="cache_clean",
                affected=[sanitize_url(url)],
                actions=["Pass the same absolute locator used to identify the source cache."],
                code="source_invalid",
                domain="cache",
            )
        canonical = canonical_source(url)
        cache = source_cache(canonical)
        public = sanitize_url(url)
        if not cache.is_dir():
            raise DoctidexError(
                "No shared bare source cache exists for this URL.",
                operation="cache_clean",
                affected=[public],
                actions=["Check the URL; no cleanup is needed if the cache was already removed."],
                code="cache_source_not_found",
                domain="cache",
            )
        with source_mutation(canonical, operation="cache_clean", conflict_code="cache_cleanup_conflict"):
            first = _classify_linked_worktrees(cache)
            if first["valid"]:
                return _cache_result(public, canonical, first, state="preserved", applied=False)
            if apply:
                second = _classify_linked_worktrees(cache)
                if second != first:
                    raise DoctidexError(
                        "The linked worktree registrations changed during cleanup.",
                        operation="cache_clean",
                        affected=[public],
                        actions=["Rerun cache clean dry-run after concurrent worktree activity finishes."],
                        code="cache_cleanup_conflict",
                        domain="cache",
                    )
                shutil.rmtree(cache)
                return _cache_result(public, canonical, first, state="removed", applied=True)
            return _cache_result(public, canonical, first, state="planned", applied=False)


def _worktree_item(record: dict[str, Any]) -> dict[str, Any]:
    path = Path(record["worktree_path"])
    if not path.is_dir():
        state = "unavailable"
    else:
        status = git(["-C", str(path), "status", "--porcelain"], operation="worktree_list", check=False)
        state = "unavailable" if status.returncode != 0 else ("changed" if status.stdout.strip() else "clean")
    suffix = record["repository_relative_path"]
    working = path if suffix == "." else path.joinpath(*suffix.split("/"))
    return {
        "source_kind": record["source_kind"],
        "owner_root": str(path.parents[3]) if len(path.parents) >= 4 else None,
        "source_url": record.get("source_url"),
        "revision_selector": record["revision_selector"],
        "base_commit": record["base_commit"],
        "root_internal_path": record["root_internal_path"],
        "worktree_path": str(path),
        "repository_relative_path": suffix,
        "working_path": str(working),
        "state": state,
        "findings": []
        if state != "unavailable"
        else [
            finding(
                "worktree",
                "warning",
                "worktree_unavailable",
                "The managed worktree path or Git metadata is unavailable.",
                path=str(path),
                actions=["Inspect the path and Git worktree metadata."],
            )
        ],
    }


def _common_gitdir(path: Path) -> Path | None:
    result = git(
        ["-C", str(path), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation="worktree_open",
        check=False,
    )
    return Path(result.stdout.strip()).resolve(strict=False) if result.returncode == 0 else None


def _gitfile_target(path: Path) -> Path | None:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content.startswith("gitdir: "):
        return None
    target = Path(content[len("gitdir: ") :])
    if not target.is_absolute():
        target = path.parent / target
    target = target.resolve(strict=False)
    result = git(
        ["--git-dir", str(target), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        operation="worktree_open",
        check=False,
    )
    return Path(result.stdout.strip()).resolve(strict=False) if result.returncode == 0 else None


def _remote_url(gitdir: Path) -> str | None:
    result = git(["--git-dir", str(gitdir), "remote", "get-url", "origin"], operation="worktree_open", check=False)
    return sanitize_url(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else None


def _source_filter_identity(value: str, root: Path) -> str:
    path = Path(value).expanduser()
    if path.exists():
        gitdir = _common_gitdir(path.absolute()) if path.is_dir() else _gitfile_target(path.absolute())
        if gitdir is not None:
            return str(gitdir)
    return canonical_source(value, cwd=root)


def _source_error(value: str) -> DoctidexError:
    return DoctidexError(
        "The worktree source is not a managed path, Git repository, gitfile, or URL.",
        operation="worktree_open",
        affected=[value],
        actions=["Pass a supported source locator."],
        code="source_invalid",
        domain="worktree",
    )


def _absolute_or_remote(value: str) -> bool:
    parsed = urlsplit(value)
    if parsed.scheme:
        return True
    if ":" in value.split("/", 1)[0]:
        return True
    return Path(value).expanduser().is_absolute()


def _classify_linked_worktrees(cache: Path) -> dict[str, int]:
    check = git(["--git-dir", str(cache), "rev-parse", "--is-bare-repository"], operation="cache_clean", check=False)
    if check.returncode != 0 or check.stdout.strip() != "true":
        raise _cache_damaged()
    result = git(["--git-dir", str(cache), "worktree", "list", "--porcelain"], operation="cache_clean", check=False)
    if result.returncode != 0:
        raise _cache_damaged()
    blocks = [block for block in result.stdout.strip().split("\n\n") if block.strip()]
    valid = 0
    prunable = 0
    linked = 0
    for block in blocks:
        lines = block.splitlines()
        if not lines or not lines[0].startswith("worktree "):
            raise _cache_damaged()
        fields = {line.split(" ", 1)[0] for line in lines[1:]}
        if "bare" in fields:
            continue
        linked += 1
        if "prunable" in fields:
            prunable += 1
        else:
            valid += 1
    return {"linked": linked, "valid": valid, "prunable": prunable}


def _cache_damaged() -> DoctidexError:
    return DoctidexError(
        "The bare source or linked worktree metadata cannot be classified safely.",
        operation="cache_clean",
        actions=["Preserve the cache and use native Git to inspect or repair its worktree metadata."],
        code="cache_source_damaged",
        domain="cache",
    )


def _cache_result(
    public_url: str,
    canonical: str,
    counts: dict[str, int],
    *,
    state: str,
    applied: bool,
) -> dict[str, Any]:
    preserved = state == "preserved"
    notices = (
        [
            finding(
                "cache",
                "warning",
                "cache_worktree_active",
                "At least one valid linked worktree still uses this source cache.",
                actions=["Close or otherwise finish every valid linked worktree before retrying cleanup."],
            )
        ]
        if preserved
        else []
    )
    return envelope(
        "cache_clean",
        status="warning" if preserved else "ok",
        result={
            "planned": "The source cache is eligible for cleanup.",
            "removed": "The eligible source cache was removed.",
            "preserved": "The source cache was preserved.",
        }[state],
        findings=notices,
        applied=applied,
        source_url=public_url,
        cache_source_id=source_id(canonical),
        linked_worktree_count=counts["linked"],
        valid_worktree_count=counts["valid"],
        prunable_worktree_count=counts["prunable"],
        state=state,
    )
