# Issue Note: Remove branch snapshots from import remove

Status: implemented

## Problem

`runtime.json` retained `branch-snapshots` entries after their local Git branches were deleted. `import remove` could
remove selected Installations, but it did not remove branch snapshots or maintain the `InstallationShare.branch-refs`
records those snapshots left behind. Stale branch snapshots therefore kept Installation shares, and sometimes their
physical worktrees, alive after the branch that justified them was gone.

## Decision

`import remove` owns branch-snapshot deletion and reuses the existing Installation share ownership rules.

### Command surface

The `import remove` selection group is:

```text
import remove (--install-id <ID> | --untracked | --auto | --branch <BRANCH>...)
```

`--branch` is repeatable, is mutually exclusive with the other selectors, and names branch snapshots by branch short
name. Selecting the current branch fails with `import.branch-snapshot.remove.current-branch` before mutation. An
unknown branch name is a no-op.

`--auto` keeps its Installation-selection contract and additionally removes snapshots whose keys are absent from the
local Git branch set. The current branch name is explicitly excluded, including on an unborn HEAD. On a detached HEAD
the full local branch set remains the source of truth.

### Branch snapshot removal

Explicit and automatic cleanup run in one RuntimeStore write transaction. For every selected branch, the command:

1. removes the `branch-snapshots` entry;
2. removes the branch name from `branch-refs` in active `installation-shares`;
3. applies the same removal to `installation-shares` stored in every remaining branch snapshot.

`context-references` are not branch history and are never removed by snapshot deletion.

### Orphaned share cleanup

A share key is orphaned when every record for that `(git-url, commit-hash)`, active and remaining snapshots alike,
has empty `install-ids`, `context-references`, and `branch-refs`. The command removes those share records and deletes
each orphan's managed physical worktree with the same path semantics used when the last Installation leaves a share.
Shares that still have an `install-id`, `context-reference`, or another branch's `branch-refs` are retained.

### Runtime write-path guard

`RuntimeWriteTransaction._replace_collections` derives its next state with `dataclasses.replace(self.state, ...)`
instead of constructing a fresh `RuntimeState`. `branch_snapshots` is an explicit optional parameter only when a
mutation changes it.

A field-generic regression test enumerates `dataclasses.fields(RuntimeState)`, seeds distinct sentinel values for
every field, runs each `RuntimeWriteModelView` mutation, and asserts every field not intentionally changed by that
mutation survives. This covers current and future fields without a manual test edit.

### Errors

| Code | Meaning |
|---|---|
| `import.branch-snapshot.remove.current-branch` | `--branch` named the currently checked-out branch. |
| `import.branch-snapshot.reconcile.failed` | A share or physical worktree could not be cleaned during snapshot removal. |

Existing `installation.remove.blocked` applies only to Installation selection and is unchanged.

## Verification

The full test suite passes, `ruff check` passes, and `git diff --check` passes. Tests cover branch enumeration,
write-view snapshot mutation, explicit multi-branch removal, current-branch rejection, stale `--auto` cleanup,
active and retained `branch-refs` reconciliation, orphaned physical worktree removal, CLI dispatch, and durable
`runtime.json` effects.

## Consequences

Users can now remove stale branch history and the shares it kept alive through the existing `import remove` command.
The change avoids a second cleanup entry point and keeps Installation share ownership in the import workflow.

The trade-off is that `--auto` now depends on Git's local branch set, and orphaned physical worktree deletion is
destructive. The reachability check considers active and remaining snapshot share records before deleting a worktree,
and the current branch is always excluded from automatic cleanup.

The write-path guard makes partial RuntimeState updates preserve unlisted fields by construction, preventing both
`branch_snapshots` loss and the same class of future-field loss.

## Alternatives considered

**Add a separate `import snapshot remove` command.**
Rejected: branch snapshots are runtime history owned by the import work model, and their cleanup needs the same
selection and share-reconciliation logic as `import remove`. A second command would duplicate those rules and split
the cleanup entry point.

**Let `repair` delete stale branch snapshots and orphaned shares.**
Rejected: `repair` deliberately stays scoped to the active work model and does not rewrite branch snapshot history.
Snapshot cleanup is an explicit user selection, not a consistency correction.

**Leave `--auto` as Installation-only and require `--branch` for snapshot cleanup.**
Rejected: automatic cleanup is the natural fit for branches that no longer exist locally, and the prior deferred work
calls for cleanup without the user first naming every deleted branch.

**Delete shares as soon as a branch reference disappears, without checking remaining snapshots.**
Rejected: a share can still be needed by another branch snapshot or by the active work model. Deleting it early would
break a later checkout or restore and is incompatible with the existing share-ownership rule.

## Related

- [Support Git branch switching with post-checkout runtime
  snapshots](2026-08-28-support-git-branch-switching-with-post-checkout-runtime-snapshots.md)
- [Shared commit-hash Installation storage](../architecture/2026-08-26-shared-commit-hash-installation-storage.md)
