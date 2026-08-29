# Issue Note: Shallow depth-one source fetches for Installations and Worktrees

Status: implemented

## Problem

The previous source-loading path transferred full repository history when an Installation or Worktree needed only one
fixed commit. `resolve_revision` fetched branch, tag, and explicit commit selectors with full history.
`ensure_commit_available` fetched missing recorded commits with full history, and cache misses created bare repositories
with an unrestricted `git clone --bare`. Because Installation and Worktree both used these helpers, large external
repositories paid unnecessary network and disk cost.

## Decision

Source loading for Installations and Worktrees uses depth-one shallow transfers.

- Cache misses publish shallow bare repositories with `git clone --bare --depth=1`.
- `resolve_revision` centralizes depth-one fetch arguments in `_SHALLOW_FETCH_ARGS` and applies them to branch, tag,
  and explicit commit selectors.
- `ensure_commit_available` fetches missing recorded commits with `--depth=1`.
- `_contains_commit` and `rev-parse` remain the availability guard before a commit is used.

The behavior lives in [repository.py](../../../../../src/python/whero/doctidex/repository.py) and
[git_cache.py](../../../../../src/python/whero/doctidex/git_cache.py). The change applies to both services through their
shared source-loading path; no user command, model record, path, or structured error changes.

## Testing

`src/python/tests/test_shallow_source_loading.py` verifies the behavior through real CLI workflows:

- `import install` for branch, tag, and commit selectors;
- `import restore` after removing a physical Installation;
- `worktree create` from a URL and from an `--install-id`;
- a forward commit made from a shallow-base Worktree.

The full suite passes with 190 tests. `ruff check src/python/whero/doctidex src/python/tests` and `git diff --check`
pass.

## Alternatives considered

**Only add `--depth=1` to selector and commit fetches, keep the cache-miss clone full.**
Rejected: a new cache entry would still download full history once, so the common first-use cost remains.

**Make shallow fetching opt-in per command.**
Rejected: Installation and Worktree both use the same fixed-commit resolution model and should share the same cost
behavior; a per-command switch adds surface without a need.

**Keep full fetches.**
Rejected: it retains unnecessary history transfer for every cache miss, selector resolution, and restore.

## Consequences

The change removes full-history transfer for cache misses, selector resolution, and recorded-commit restore. Large
external repositories require less network and disk before an Installation or Worktree is usable.

The trade-off is that cached bare repositories omit ancestors. Current commands only need the selected commit, its tree,
and blobs, and Worktrees can still commit forward from a shallow base. A future command that needs repository history
must request more depth explicitly.

Local filesystem clones may ignore `--depth` unless a `file://` URL is used, so shallow-boundary tests use `file://`
or a real remote. This is a test-observability detail, not a change in production remote behavior.
