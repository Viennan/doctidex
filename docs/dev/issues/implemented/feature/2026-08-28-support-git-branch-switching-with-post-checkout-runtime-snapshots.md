# Issue Note: Support Git branch switching with post-checkout runtime snapshots

Status: implemented

## Problem

`doctidex-git` treated one Git repository as a single-branch development environment. Its tracked projections switch
with Git, but the untracked `runtime.json` stays in the working tree. That file owns untracked Installations,
Worktrees, and Installation shares, and can therefore describe physical state from the branch that was checked out
when the runtime was last mutated.

After `git checkout`, the new branch could have tracked Installation declarations that did not match the stale
`runtime.json`. Untracked Installations could belong to another branch, share references could no longer line up with
tracked Installations, and physical share worktrees could be retained or removed for the wrong reason.

## Decision

`doctidex-git` now records branch-specific runtime history and installs a Git post-checkout hook that restores it
across branch switches.

### Branch snapshot model

`runtime.json` has a `branch-snapshots` object keyed by the raw branch name. Each value is a runtime document without
`branch-snapshots`; it stores `imports`, `worktrees`, and `installation-shares`. Snapshot `imports` contain only
untracked Installations. `RuntimeState.branch_snapshots` is a `dict[str, BranchSnapshot]`.

`InstallationShare` has a `branch-refs` list. It records branch names that have used the share and is required on
newly written share records.

### Branch identity and workspace gate

The snapshot key is the branch short name. A detached HEAD has no branch key. The post-checkout hook performs work
only when both the old and new branches have a tracked `.doctidex-git/config.toml`; otherwise it exits successfully
without changing state.

### Hook command cluster

The CLI has a `hook` command cluster:

- `hook install` writes supported Git hook scripts under the repository Git hooks directory and is idempotent.
- `hook post-checkout` is the worker invoked by the installed `post-checkout` hook.

The installed script invokes the resolved `doctidex-git` command path, not `PATH`. Successful first-time `init`
installs the hooks automatically.

### Post-checkout behavior

A normal Git invocation saves the old branch's runtime snapshot, then applies the new branch snapshot or an empty
untracked Installation set. A no-argument `hook post-checkout` is an apply-only rerun for the current branch.

The hook updates only `runtime.json`. It acquires the RuntimeStore exclusive lock, atomically publishes that file,
and then aligns physical Installation objects before releasing the lock. It does not create a journaled multi-file
transaction.

For Installation shares, the repository-global share records are retained. The hook replaces `install-ids` and
`context-references` from the target snapshot, preserves `branch-refs` and physical worktree metadata, and keeps
Worktrees unchanged. It never deletes a share worktree merely because the current branch no longer references it.

If reconciliation cannot complete, the hook returns a structured diagnostic and nonzero status. The user corrects the
work model or physical state, then reruns `hook post-checkout`.

### Import and removal

`import install`, `import restore`, and `restore_context_import` add the current branch to `InstallationShare.branch-refs`.
Removal preserves a share and its physical worktree while another branch still references it; the share is deleted only
when membership and `branch-refs` are both empty.

### Validation and repair

Validation rejects duplicate share `branch-refs`, empty branch snapshot keys, and duplicate branch references inside
snapshots. It does not require inactive snapshot Installations to have present physical paths. Repair stays scoped to
the active work model and does not rewrite branch snapshot history.

## Verification

The full test suite passes. Coverage is 87%. `ruff check src/python/whero/doctidex src/python/tests` passes and
`git diff --check` passes. Tests cover branch snapshot round-trips, branch helpers, hook installation, post-checkout
save/apply/rerun, physical reconciliation, branch-aware removal, validation, and legacy-free model parsing.

## Consequences

Branch switches now restore the branch-specific untracked Installation state without duplicating the global
Installation share worktree. The hook adds a new failure point to `git checkout`, but it fails with a structured
diagnostic and can be completed by rerunning the worker.

The trade-off is a new runtime-only `branch-snapshots` object, a `branch-refs` field on Installation shares, and a
single-file RuntimeStore publication path that intentionally bypasses the normal journaled transaction.

## Out of scope

Maintaining `branch-refs` after a branch snapshot is removed, or when a share becomes unreachable from every branch,
is deferred to a future `import remove` option.

## Alternatives considered

**Track `runtime.json` in Git instead of snapshotting it.**
Rejected: runtime state is machine-local and untracked by design. Tracking it would merge host-specific paths and
share state into branch history and create ordinary Git conflicts on checkout.

**Run `doctidex-git repair` automatically after checkout.**
Rejected: repair aligns the whole work model and can touch ignore rules and other concerns. It does not recover the
previous branch's untracked Installation history.

**Store one runtime file per branch under `/.doctidex-git/`.**
Rejected: it creates a parallel state-file layout and bypasses the existing `runtime.json` publication and journaling
path.

**Re-derive untracked Installations from the physical import tree after checkout.**
Rejected: physical objects do not carry the full branch-specific Installation identity, keys, selectors, and share
references.

## Related

- [Add a pre-commit model-structure validation hook](2026-08-29-add-pre-commit-model-structure-validation-hook.md)
- [Shared commit-hash Installation storage](../architecture/2026-08-26-shared-commit-hash-installation-storage.md)
- [Select Installation context by install-id argument](../architecture/2026-08-27-select-installation-context-by-install-id.md)
