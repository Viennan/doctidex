# Issue Note: Reserve `/.doctidex-git/imports` for managed Installations

Status: implemented

## Problem

`/.doctidex-git/imports/` is the repository-local tree that `import install` and `import restore` populate with Installation worktrees. The work model records each Installation by exact `install-path`, and the earlier protection from [distinguish managed Worktrees from Installation context](2026-08-24-distinguish-managed-worktrees-from-installation-context.md) only matched recorded Installation paths.

[worktree.py](../../../../../src/python/whero/doctidex/worktree.py) protected only paths that exactly matched `view.installation_at(work_path)`. That left unrecorded descendants of `/.doctidex-git/imports/` available to `worktree create`, even though those paths may later be chosen for an Installation.

[imports.py](../../../../../src/python/whero/doctidex/imports.py) had the same gap for `import ref --target-dir`. It rejected only occupied targets, so a Ref could be created under `/.doctidex-git/imports/` or `/.doctidex-git/worktrees/`.

Neither Worktree creation nor Ref creation checked whether the requested path was at or below an existing boundary point. The new object derives its own boundary only after creation, but its target must not already lie outside the current tree's managed scope.

## Decision

`/.doctidex-git/imports` and `/.doctidex-git/worktrees` are now explicit managed directories. Worktree and Ref creation reject paths inside the wrong managed directory and paths below any existing boundary point.

### Managed-directory predicates

[paths.py](../../../../../src/python/whero/doctidex/paths.py) defines `MANAGED_IMPORTS_DIRECTORY`, `MANAGED_WORKTREES_DIRECTORY`, `is_managed_imports_path`, and `is_managed_worktrees_path`. The two public predicates share the private `_is_managed_directory_path` helper.

### Worktree creation

`worktree create` no longer uses `view.installation_at`. It rejects any selected Worktree path inside `/.doctidex-git/imports/` with `worktree.target.unavailable` and `occupant` `managed-imports-directory`, then rejects paths below an existing boundary point with `occupant` `existing-boundary`. The check runs before target availability and Git worktree creation, so a rejected request creates no directory, record, or custom ignore rule.

### Ref creation

`import ref` uses the private `_ref_target_reservation(view, target_dir)` helper before source lookup. The helper returns `managed-imports-directory`, `managed-worktrees-directory`, or `existing-boundary` with the matching boundary, and the command raises `ref.target.unavailable` with `reason` in the details. For `existing-boundary`, the details also include `boundary-path` and `boundary-type`. No parent directory or symlink is created for a rejected target.

### Existing boundary-point detection

Both creation workflows inspect the current work model with `view.first_boundary(path)`. The operation's own derived boundary is not present during this preflight, so the check does not conflict with post-creation boundary derivation.

### Documentation

The architecture [overview.md](../../../architecture/overview.md) states the managed-directory reservations for Installation, Ref, and Worktree concepts. The `worktree` and `import` reference error tables state the new rejection reasons without adding long user-guide explanations.

## Testing

The full suite passes with 78 tests. `ruff check` passes, `git diff --check` passes, and coverage is 85%. Tests cover managed Installation and Worktree directory rejection, existing-boundary rejection for both commands, no physical side effects after rejection, and unchanged valid success paths.

## Alternatives considered

**Keep the exact Installation-path check only.**
Rejected: unrecorded descendants were not protected, and future install paths are unknown at Worktree or Ref creation time.

**Make `import install` reclaim or replace any path under the managed directory.**
Rejected: it would make install semantics depend on cleanup of objects that should never exist there. Preventing creation is clearer and less destructive.

**Apply the guard only to `worktree create`.**
Rejected: `import ref` can create the same class of non-Installation object under `/.doctidex-git/imports/` or `/.doctidex-git/worktrees/`.

**Document the rule without enforcing it.**
Rejected: documentation alone does not stop command-generated objects from colliding with future install-path allocation.

**Use the existing boundary-point lookup instead of a dedicated prefix check.**
Rejected: boundary points represent recorded objects, not the managed container directories, so they cannot reserve unrecorded descendants.

## Consequences

The change closes the reserved-directory and existing-boundary gaps for both Worktree and Ref creation. Valid default and ordinary custom paths remain available, and rejected requests leave no physical or recorded side effects.

The cost is a broader set of preflight rejections. Paths that exactly match a recorded Installation now report `managed-imports-directory` rather than the retired `installation-path` occupant, which is a deliberate diagnostic contract change.

## Related

- [Distinguish managed Worktrees from Installation context](2026-08-24-distinguish-managed-worktrees-from-installation-context.md)
