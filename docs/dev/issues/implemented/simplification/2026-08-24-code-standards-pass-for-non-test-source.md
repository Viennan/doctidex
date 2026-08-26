# Issue Note: Code standards pass for non-test source

Status: implemented

## Problem

The non-test source under `src/python/whero/doctidex/` is governed by five conventions in [src/AGENTS.md](../../../../../src/AGENTS.md): private methods may only be called from their defining module or class; a private method promoted to public drops its `_` or `__` prefix everywhere; public methods carry a maintained docstring; each module opens with a docstring stating its semantic responsibility; and public definitions precede private ones while related methods are grouped together.

Before this change the source mixed private helpers into the public command surface, imported and called private helpers across modules, left public workflows without docstrings, and placed private definitions before later public ones in several module and class scopes. Tests were kept outside the audit scope.

## Decision

The non-test source now follows all five conventions while preserving observable behavior.

### Private-call boundary

- `RuntimeStore` exposes `clean_journal`, `encode_state`, and `observe_entry` as public operations, with callers in `store/runtime.py`, `initialization.py`, and `repair.py` updated.
- `initialization.ensure_runtime_ignores` is public, so `repair` no longer imports a private bootstrap helper.
- The physical-alignment steps reused by `repair` from `imports` (`ensure_install_commit`, `ensure_install_worktree`) and `worktree` (`ensure_worktree_commit`, `create_git_worktree`, `align_custom_ignores`) are public workflow operations in their owning modules.

### Ordering and grouping

Module and class scopes place public definitions before private definitions. `model.py`, `imports.py`, `installation.py`, `markdown_links.py`, `root_index.py`, `validate.py`, and `worktree.py` group public command functions and domain records before private helpers. `store/model_view.py`, `store/runtime.py`, and `git_cache.py` put public and dunder methods before private bookkeeping methods.

### Documentation contract

Every public method and function has a docstring that states non-obvious contracts rather than restating code, and each module docstring states its semantic responsibility.

## Testing

`ruff check src/python/whero/doctidex` passes with the enabled rule set. The full `pytest` suite passes, and `git diff --check` passes. AST checks confirm no public definition follows a private definition in the same scope and no private symbol is imported across package modules. No tests were modified and no CLI or filesystem behavior changed.

## Alternatives considered

**Enforce the conventions with additional Ruff rules.**
Rejected: it would add a broad lint surface for rules the repository has not enabled and would force mechanical changes beyond the scoped pass. The existing enabled rule set remains `B`, `E`, `F`, `I`, `UP`.

**Include tests in the same audit.**
Rejected: the request excludes tests, and test files follow different documentation and mocking conventions that would expand the scope without addressing production-source boundaries.

**Document an exception for cross-module private calls.**
Rejected: an exception would contradict the convention in [src/AGENTS.md](../../../../../src/AGENTS.md) and preserve the fragile internal boundary this pass is meant to remove.

**Promote every cross-module private helper regardless of need.**
Rejected: it would expose internal steps that have no other caller and widen the public surface. Promotion is reserved for genuine reuse; otherwise the helper stays private and moves to its owning scope.

## Consequences

The internal boundary between command workflows and store operations is explicit, definition order is consistent, and public responsibilities are documented. The cost is a larger, behavior-neutral diff and several newly public workflow names. Coverage is unchanged because the public-interface test suite remains the safety net.
