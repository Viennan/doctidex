# Issue Note: Consolidate fragmented unit-test files by owning feature

Status: implemented

## Problem

`src/python/tests/` has drifted back toward small, feature-split modules. It currently contains 38
`test_*.py` modules. Several features are covered by many short files that all test the same owning
mechanism, which makes the feature's coverage harder to scan and duplicates private helpers and fixtures.

The clearest case is Presentation-Installation: seven `test_presentation_installation_*.py` modules split
one feature across 839 lines and 24 test functions, and `test_runtime_model_view_installation_lookup.py`
adds three closely related lookup tests. Similar fragmentation exists for branch-snapshot removal, store
transaction coordination, runtime write views, shared Installation storage, skills, Git hooks, and config
behavior. Across the candidate groups below, 23 modules and 106 test functions are split into sub-behavior
files; several files define near-identical `_share`, `_write_state`, or `_presentation_id` helpers.

This is a testing-infrastructure issue rather than a product-behavior change. The prior restructure decision
in [Restructure tests around user-facing behavior](../../implemented/testing/2026-08-24-restructure-tests-around-user-facing-behavior.md)
established command-cluster organization; this proposal preserves that principle and removes later drift.

## Decision

The `src/python/tests/` suite is now consolidated by owning feature. Each target file owns one feature or
command cluster:

- `test_presentation_installation.py`
- `test_branch_snapshot.py`
- `test_store_coordination.py`
- `test_runtime_write_view.py`
- `test_installation_shares.py`
- `test_skills.py`
- `test_hooks.py`
- `test_config.py`

The old sub-behavior modules for those features are deleted. `test_git_cache_maintenance.py` remains separate
because it is already a single cache-maintenance module.

The merge preserves existing test functions, assertions, fixture dependencies, parametrizations, markers,
and test names. Duplicated private helpers are collapsed only within their owning target; no feature-local
helpers moved into `conftest.py`. No production files or product behavior changed.

## Testing

The implementation passes the same gates as the baseline:

- full default pytest suite: `258 passed, 7 deselected`
- Ruff: `All checks passed!`
- `git diff --check`: clean

The suite now contains 23 `test_*.py` modules under `src/python/tests/`.

## Consequences

The consolidation makes feature coverage easier to find and removes duplicate test helpers. The trade-off is
larger, feature-level test files; the ownership rule keeps each target a single owning feature and rejects
`and`-style target names so the files do not become grab bags. Cache maintenance remains intentionally
separate from config.

## Related

- [Restructure tests around user-facing behavior](../../implemented/testing/2026-08-24-restructure-tests-around-user-facing-behavior.md)
- [Introduce Presentation-Installation to close recursive Installation-context access](../../implemented/architecture/2026-09-01-introduce-presentation-installation-for-recursive-installation-context.md)
- [Remove branch snapshots from import remove](../../implemented/feature/2026-08-29-remove-branch-snapshots-with-import-remove.md)
- [Optimize store lock modes and transaction roles](../../implemented/architecture/2026-08-27-optimize-store-lock-modes-and-transaction-roles.md)
- [Batch RuntimeWriteModelView index rebuilds](../../implemented/architecture/2026-08-29-batch-runtime-write-view-index-rebuilds.md)
- [Shared commit-hash Installation storage](../../implemented/architecture/2026-08-26-shared-commit-hash-installation-storage.md)
- [Standardize doctidex-git config access](../../implemented/architecture/2026-08-30-standardize-doctidex-git-config-access.md)

## Alternatives considered

**Merge every test module into one large file.**
Rejected: it would erase the command-cluster and feature organization the suite already has, making the file
difficult to navigate and review.

**Only merge exact `test_presentation_installation_*` prefix files.**
Rejected: it addresses the most visible symptom but leaves the same fragmentation in branch-snapshot, store
coordination, runtime write view, shared-storage, skills, hooks, and config coverage.

**Keep the small files and move duplicated helpers into `conftest.py`.**
Rejected: it reduces some duplication without fixing file fragmentation, and it would expand the shared
fixture surface for helpers that are only relevant to one feature.

**Leave the test files unchanged.**
Rejected: the current layout makes feature coverage and ownership needlessly hard to discover and continues
to invite duplicate helpers as new sub-behavior tests are added.
