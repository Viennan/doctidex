# Issue Note: Remove duplicated Installation workflow branches

Status: implemented

## Problem

The Installation workflows contained two related structure smells:

1. Functions special-cased an existing object and then repeated much of the same logic on the fall-through path.
2. One physical or model-mutating operation was split into two public functions that every caller paired in the same order.

`_ensure_share_for_commit` demonstrated both at once: it branched on an existing `InstallationShare`, duplicated the `prepare_install_path` / `create_worktree` pair, and then repeated the pair for a new share. The branches differed only in where `install_path` came from.

The same early-branch duplication appeared in other Installation workflow functions:

| Function | Duplicated branch logic |
|---|---|
| `_leave_share` | Removed a branch/tag Installation path in both the no-share and remaining-share branches. |
| `_remove_installation_reference` | Removed the branch/tag path and Installation record in both the no-share and remaining-share branches. |
| `worktree.create` | Defined nearly identical `create_from_repository` wrappers and the same outer coordinator/exception handling for install-id and URL source modes. |

`_install_selector_resolved` and `_install_commit_resolved` also had repeated `_ensure_installation_in_share` calls, but their early `if ... return` structure was kept. Flattening them into one finalization path would have added nested `else` branches without removing enough duplication to justify the loss of clarity.

## Decision

### Physical Installation alignment

`imports.py` now exposes one public workflow operation, `ensure_install_worktree`, which owns the complete physical alignment contract. The old public `prepare_install_path` and `create_worktree` functions are gone.

`ensure_install_worktree` creates a missing worktree, reuses a compatible detached clean worktree, removes and recreates an unusable worktree, raises the existing different-`git-url` failure, and maps filesystem/Git failures to the existing `unavailable-path` failure. `repair.py` uses the same operation for tracked Installations and Installation shares.

### Share and selector finalization

`_ensure_share_for_commit` resolves `install_path` once from the existing share or `_install_path`, calls `ensure_install_worktree` once, and only then creates and upserts a new `InstallationShare`.

`_install_selector_resolved` and `_install_commit_resolved` remain early-return workflows. They were not flattened.

This non-flattening decision is superseded by [Add commit selector prefix to Installation share
paths](../architecture/2026-08-31-add-commit-prefix-to-installation-share-paths.md), which later collapses the two
functions into one `_install_resolved` after the commit selector gains a kind segment.

### Share removal

`_leave_share` detaches a replaced selector Installation without deleting its Installation record. `_remove_installation_reference` removes the Installation record and then detaches its share membership. Both functions call `_remove_from_installation_share` for the shared remaining-reference/empty-share cleanup.

### Worktree source modes

`worktree.create` keeps one source-resolution decision for install-id versus URL, but both modes now share one `create_from_repository` and one coordinator/exception path. URL revision resolution remains lazy inside `coordinator.with_repository`.

### Optimization boundary

The refactor prefers early returns and single reusable guards over gratuitous nested `else` branches. No redundant paired workflow operations remain in the affected modules.

## Verification

- `ruff check src/python/whero/doctidex` passes.
- The full `pytest` suite passes: 88 tests.
- Coverage is 86%.
- `git diff --check` passes.

## Alternatives considered

**Keep the two public physical-alignment functions and extract a private helper at each call site.**
Rejected: it would still expose the reuse-or-create decision to callers and leave the pair repeated across modules.

**Inline the reuse-or-create logic into every call site.**
Rejected: it would spread filesystem and Git failure handling across `imports.py` and `repair.py`.

**Introduce a third wrapper while retaining both existing public functions.**
Rejected: it would grow the public surface without removing the split.

**Move physical alignment into the store or model-view layer.**
Rejected: filesystem and Git side effects belong to command workflows, not store or model-view responsibilities.

**Refactor only `_ensure_share_for_commit`.**
Rejected: the other sites repeated the same structural mistake, and a partial cleanup would leave the pattern available as a template.

**Also sweep every early `if` in the CLI and model layers.**
Rejected: most of those statements are guard clauses or input dispatch rather than duplicated workflow logic.

**Flatten `_install_selector_resolved` and `_install_commit_resolved` into one finalization path.**
Rejected: it adds nested `else` blocks, obscures the early reuse path, and increases nesting to remove only a small amount of duplication.

## Consequences

The Installation and Worktree workflows have one physical-alignment entry point, fewer duplicated branches, and clearer lifecycle intent for leave-versus-remove operations.

The cost is a behavior-neutral refactor with a changed internal public surface: `prepare_install_path` and `create_worktree` are replaced by `ensure_install_worktree`. The existing public-interface test suite and full coverage gate confirm the behavior remains stable.
