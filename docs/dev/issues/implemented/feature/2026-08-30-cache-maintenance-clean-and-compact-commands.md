# Issue Note: Add cache clean and compact maintenance commands

Status: implemented

## Problem

The user-level Git cache previously had no maintenance surface. `import` and `worktree` populated cached bare repositories
through `GitCache.load`, and a cache entry survived after every Installation and Worktree that used it was removed.
Unused repositories and unreachable Git objects accumulated with no supported way to reclaim them.

## Decision

The CLI now exposes a top-level `cache` command cluster with two subcommands.

`cache clean` opens a CacheStore write transaction and removes published cache repositories that have no non-bare
linked Worktree. For each published CacheItem, the workflow:

1. resolves the recorded bare repository path;
2. runs `git worktree prune`;
3. reads `git worktree list --porcelain`;
4. treats the repository as unused when it has no non-bare linked worktree;
5. uses the existing `PREPARING` recovery contract to delete the physical repository and publish the surviving record
   set.

`cache compact` runs `git worktree prune` and then `git gc --prune=now` for every published cache repository. It uses
Git's ordinary reachability and garbage-collection behavior. It does not reconnect shallow history, truncate commit
chains, or impose a custom live-Worktree reachability boundary.

Both workflows live in [git_cache.py](../../../../../src/python/whero/doctidex/git_cache.py) and are registered by
[cli/main.py](../../../../../src/python/whero/doctidex/cli/main.py). They operate on the user-level cache selected by
`DOCTIDEX-GIT-HOME` and `config.toml`; they do not select or mutate a repository-local RuntimeStore.

## Testing

`src/python/tests/test_git_cache_maintenance.py` covers:

- exposing and replacing published CacheItem records;
- parsing non-bare linked worktrees and live HEADs;
- `cache clean` removal, live-repository retention, and `PREPARING` recovery;
- the simplified `cache compact` workflow.

The full suite passes with 196 tests. `ruff check src/python/whero/doctidex src/python/tests` and `git diff --check`
pass.

## Alternatives considered

**Add cleanup as flags on `import` or `worktree`.**
Rejected: cache maintenance is cross-cutting and operates on the user-level cache rather than one repository's work
model. A dedicated `cache` cluster keeps that boundary visible.

**Leave cache cleanup manual.**
Rejected: shallow fetches make cache objects and repository entries harder to reason about by hand, and the product
already owns the cache path and status records.

**Clean by scanning filesystem directories without CacheStore.**
Rejected: `status.json` is the publication authority. A filesystem-only scan could delete a `preparing` repository or
miss a recorded path.

## Consequences

Users can now reclaim unused cache repositories and run normal Git garbage collection over the remaining cache without
manually inspecting `status.json` or cache directories.

The trade-off is that `cache clean` is destructive; a malformed Worktree registration can make a live repository look
unused. This is accepted because doctidex-git does not protect cache or Worktree metadata from user or external edits.
`cache compact` relies on ordinary Git reachability rather than trying to optimize a custom live-Worktree object set.
