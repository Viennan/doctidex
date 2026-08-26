# Issue Note: Remove duplicated Installation workflow branches

Status: developing

## Problem

The Installation workflows contain two related structure smells that make the same decision appear in several places:

1. A function starts by special-casing an existing object, then repeats much of the same logic on the fall-through path.
2. One physical or model-mutating operation is split into two public functions that every caller must pair in the same order.

`_ensure_share_for_commit` demonstrates both at once. It first branches on an existing `InstallationShare`, duplicates the `prepare_install_path` / `create_worktree` pair, and then repeats the pair on the new-share path. The branches differ only in where `install_path` comes from.

The same early-branch duplication appears in other Installation workflow functions:

| Function | Duplicated branch logic |
|---|---|
| `_install_selector_resolved` | Calls `_ensure_installation_in_share` in the early reuse branch and again on the normal path. |
| `_install_commit_resolved` | Calls `_ensure_installation_in_share` in the early existing-Installation branch and again on the normal path. |
| `_leave_share` | Removes a branch/tag Installation path in both the no-share and remaining-share branches. |
| `_remove_installation_reference` | Removes the branch/tag path and calls `view.remove_installations` in both the no-share and remaining-share branches. |
| `worktree.create` | Defines nearly identical `create_from_repository` wrappers and the same outer coordinator/exception handling for install-id and URL source modes. |

`_install_selector_resolved` and `_install_commit_resolved` are scan results but are not selected for refactoring. Their early `if ... return` pattern is acceptable; flattening them into one finalization path would add nested `else` branches.

The physical alignment split is also duplicated by call site:

| File | Paired call site |
|---|---|
| `imports.py` | `_ensure_share_for_commit`, existing-share and new-share branches |
| `repair.py` | `_align_installation` |
| `repair.py` | `_align_installation_shares` |

The split exposes the "reuse or create" decision to callers even though they all need the same final state: a compatible, clean, detached worktree at the recorded commit.

## Design

### Impact

The user surface and domain model do not change. `import install`, `import restore`, `worktree create`, and `repair` keep their current JSON results, error codes, and filesystem effects.

The change is internal to three command workflows:

- [imports.py](../../../../../src/python/whero/doctidex/imports.py)
- [repair.py](../../../../../src/python/whero/doctidex/repair.py)
- [worktree.py](../../../../../src/python/whero/doctidex/worktree.py)

The `InstallationShare` and `Worktree` records remain governed by [the current architecture](../../../architecture/overview.md).

### Optimization boundary

- Do not increase maximum `if` nesting depth.
- Keep early `if` special-case followed by `return` where it expresses a short reusable path.
- Remove redundant coding by extracting large common blocks into private helpers, not by merging distinct branches.

### Physical Installation alignment

Merge `prepare_install_path` and `create_worktree` into one public workflow operation in `imports.py`, such as `ensure_install_worktree`.

The operation owns the complete path-alignment contract:

- create the worktree when the target is absent;
- reuse a compatible, detached, clean worktree;
- remove and recreate an unusable worktree;
- raise the existing structured failure for a different `git-url`;
- map filesystem and Git failures to the existing `unavailable-path` failure.

`ensure_install_commit` remains a separate operation because commit availability is validated before the cache-backed physical work.

`_ensure_share_for_commit` resolves `install_path` first from the existing share or from `_install_path`, calls `ensure_install_worktree` once, and only then creates and upserts a new `InstallationShare`. `repair` uses the same operation for both tracked Installations and Installation shares.

### Selector and commit finalization

Leave `_install_selector_resolved` and `_install_commit_resolved` as early-return workflows. Do not merge their distinct branches into one finalization path. If a later change finds a large common block inside them, extract that block into a private `imports.py` helper while preserving the early returns.

### Share removal

`_leave_share` and `_remove_installation_reference` should hoist the common branch/tag path removal out of the no-share branch. `_remove_installation_reference` should also remove the Installation record once, regardless of whether a share remains, and only then update or remove the share.

The removal order remains: delete the selector path, delete the Installation record, then update or delete the share record and its physical worktree.

### Worktree source modes

`worktree.create` keeps the install-id versus URL source decision but reduces the branch to source resolution. Both modes should produce one `source_url`, one selector description, one resolved base commit or commit resolver, and one shared `create_from_repository` wrapper.

The shared wrapper keeps the current lazy URL revision resolution: install-id mode already has a base commit, while URL mode resolves it inside `coordinator.with_repository`. The existing `cache.repository.unavailable` translation stays on the shared coordinator call path.

## Implementation plan

### Phase 1: Collapse physical Installation alignment

Add `ensure_install_worktree` in `imports.py`, replace `prepare_install_path` and `create_worktree` at their call sites, and update `repair.py`.

Validation:

- existing `test_import.py`, `test_repair.py`, and `test_installation_shares.py` pass;
- `ruff check src/python/whero/doctidex` passes.

### Phase 2: Remove duplicated Installation workflow branches

Refactor `_ensure_share_for_commit`, `_leave_share`, and `_remove_installation_reference` to remove duplicated code without increasing `if` nesting. Keep `_install_selector_resolved` and `_install_commit_resolved` unchanged.

Validation:

- existing public-interface import, removal, restore, branch/tag replacement, and share tests pass, including the test that preserves a managed Ref when a branch Installation is replaced;
- no function in the refactored files gains a deeper `if` nesting path than before;
- `git diff --check` passes.

### Phase 3: Consolidate `worktree.create` source modes

Refactor `worktree.create` to share one `create_from_repository` and one coordinator/exception path after source resolution.

Validation:

- existing `test_worktree.py` cases for URL, install-id, custom path, default path, and tree-name creation pass.

### Phase 4: Final quality pass

Re-read the refactored functions for remaining early-branch duplication or paired workflow operations. Confirm that early-return branches remain early returns and that no refactor introduced deeper `if` nesting. Update docstrings for any changed public function, remove obsolete private helpers, and run the full test suite, `ruff check`, `git diff --check`, and coverage.

## Progress

- Design completed.
- Four-phase implementation plan completed.
- Implementation has not started.

## Alternatives considered

**Keep the two public functions and extract a private helper at each call site.**
Rejected: it would still expose a decision that belongs inside the workflow and would leave the same pair repeated in multiple modules.

**Inline the reuse-or-create logic into every call site.**
Rejected: it would spread filesystem and Git failure handling across `imports.py` and `repair.py`, making the physical-alignment contract harder to change consistently.

**Introduce a third wrapper while retaining both existing public functions.**
Rejected: it would grow the public surface without removing the split; the old pair would remain available and invite the same misuse.

**Move physical alignment into the store or model-view layer.**
Rejected: filesystem and Git side effects belong to command workflows, not to store or model-view responsibilities.

**Refactor only `_ensure_share_for_commit` and leave the other early-branch sites.**
Rejected: the other sites repeat the same structural mistake, and a partial cleanup would leave the pattern available as a template for future code.

**Also sweep every early `if` in the CLI and model layers.**
Rejected: most of those `if` statements are guard clauses or input dispatch, not duplicated workflow logic. The change should stay scoped to Installation and adjacent Worktree command workflows.

**Flatten `_install_selector_resolved` and `_install_commit_resolved` into one finalization path.**
Rejected: it adds nested `else` blocks, obscures the early reuse path, and increases nesting to remove only a small amount of duplication.

## Risks

The refactor is behavior-neutral by design, but failure mapping and cleanup on failed worktree creation must be preserved exactly. The removed public functions are imported by `repair`, so every call site and any direct tests must be updated in the same change.

`worktree.create` uses lazy commit resolution, so its source-mode consolidation must not resolve a URL revision earlier than the existing coordinator flow does, and must preserve the existing `cache.repository.unavailable` translation.

The change should stay scoped to Installation and adjacent Worktree command workflows. It should not absorb the editable Worktree service's `create_git_worktree` failure semantics, and should not sweep unrelated CLI dispatch, validation, or model parse guard clauses.
