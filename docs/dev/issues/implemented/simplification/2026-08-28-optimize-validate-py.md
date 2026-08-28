# Issue Note: Optimize validate.py

Status: implemented

## Problem

`validate.py` carried several responsibilities in one module: workspace discovery, scope validation, store recovery
handling, model projection validation, physical Installation/share/Ref/Worktree checks, ignore-rule checks, Markdown
link diagnostics, and public result assembly. The behavior was correct, but the structure made the module harder to
review and change. The largest burden was `_model_violations`, a long function that mixed identity checks,
relationship consistency, and physical-state checks.

## Decision

The validation internals are refactored without changing the public contract.

`validate(store, *, subdir, model_structure)` remains the public entry point. The emitted rules, ordering, details,
and exit statuses are unchanged.

### Result assembly

`validate()` now has one finalization path. `_finalize(diagnostics, scope)` owns diagnostic sorting and
`ValidationResult` construction. The unused `_ModelCheck.requires_recovery` field is removed; recovery state is
represented by a diagnostic.

### Model violation decomposition

`_model_violations` is a small orchestrator. It builds `installations_by_id` once and delegates to bounded private
functions:

- `_missing_artifact_violations`
- `_duplicate_record_violations`
- `_share_record_violations`
- `_ref_installation_violations`
- `_managed_path_violations`
- `_installation_physical_violations`
- `_share_physical_violations`
- `_ref_physical_violations`
- `_worktree_physical_violations`

### Projection mistake handling

`_specific_model_violation` delegates to `_imports_projection_violation`, `_runtime_projection_violation`, and
`_boundary_set_projection_violation`. Each helper handles only the projection mistake that a successful model parse
cannot recover.

### Git inspection helpers

Git subprocess inspection now goes through `_run_git`. `_is_git_worktree`, `_git_output`, and `_git_worktree_dirty`
reuse that helper while preserving their prior error behavior.

## Verification

The full test suite passes. Overall coverage is 87%. `ruff check src/python/whero/doctidex src/python/tests` passes,
and `git diff --check` passes. Validation tests continue to cover model structure, projection mistakes, physical
Installations, shares, Refs, Worktrees, and ignore-rule diagnostics.

## Consequences

The module is easier to extend because each validation domain has a named private function and shared lookups are
constructed once. Result sorting and construction are no longer duplicated.

The trade-off is a small increase in total line count from the extracted function boundaries. There is no observable
behavior change, and no new public API or user-facing diagnostic surface was introduced.

## Alternatives considered

**Leave the file as is.**
Rejected: the module was already large enough that new validation rules were harder to place and review.

**Split validation into separate modules by check domain.**
Rejected: the checks share the same model view, diagnostic shape, and command entry point. A single module with clear
private helpers keeps that shared context visible.

**Replace dictionaries with typed diagnostic objects.**
Rejected: the machine-readable dictionary shape is the stable user contract. Typed objects would add conversion and
churn without simplifying the check logic.

**Reuse import/repair physical-check functions.**
Rejected: validation is read-only and reports diagnostics, while import and repair mutate or recover state. Mixing
those responsibilities would change failure semantics.
