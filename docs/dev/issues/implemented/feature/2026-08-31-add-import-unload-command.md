# Issue Note: Add import unload command

Status: implemented

## Problem

`import remove` deletes a selected Installation's record and physical checkout together. Before this change there was
no command that kept a tracked Installation's metadata while detaching it from its `InstallationShare`, so a user
could not free a shared checkout that was no longer needed on disk but still worth keeping for a later
`import restore`. Detaching a tracked Installation by hand also required reproducing the share-ownership rules in
[installation-shares.md](../../../architecture/installation-shares.md), which were easy to get wrong.

## Decision

`import unload` is part of the import cluster:

```text
doctidex-git import unload --install-id <INSTALL-ID>...
```

`--install-id` is repeatable and at least one is required. The command accepts only tracked Installations, and a
tracked Installation that is already `restore-required` is a no-op. Unload is idempotent.

In one `RuntimeStore` write transaction, unload removes physical availability without removing identity. It keeps the
Installation record in the tracked projection, keeps every managed Ref and its target symlink, and does not scan or
reject Markdown links. For each selected Installation, unload removes a branch or tag selector symlink when present,
then removes the selected `install-id` from its active `InstallationShare`. When that leaves no `install-ids`, the
current branch is dropped from `branch-refs`. The share record and its physical worktree are deleted only when no
`install-ids`, `context-references`, or remaining `branch-refs` are left. Branch-snapshot history is not rewritten;
the existing post-checkout merge reconciles stale branch snapshots.

After unload, `import query` reports the Installation as `restore-required`, and `import restore` recreates its
physical checkout from the unchanged metadata. Leaving Refs and links in place does not invalidate the work model:
validation already tolerates a tracked Installation whose physical directory is absent.

The command reports `installation.not-found` for an unknown `install-id`,
`installation.tracking-state.invalid` for an untracked Installation, and
`installation.unload.reconcile.failed` when a selector symlink, share, or physical worktree cannot be removed.

## Verification

Tests cover multi-Installation unload, shared-worktree survival, orphaned-share deletion, idempotence, and the
unknown, untracked, and missing-argument error paths. Integration tests exercise unload with managed Refs and
cross-boundary Markdown links, then run `validate` and `import restore` to prove the missing-physical-directory state
remains valid and can be restored. The full default suite passes, `ruff check` passes, `git diff --check` passes,
and coverage is 88% overall.

## Alternatives considered

**Extend `import remove` with a keep-metadata flag.**
Rejected: `remove` already selects untracked, automatic, and branch-snapshot targets in one command. Folding
metadata-preserving detach into that surface would mix two different ownership contracts and make the command harder
to reason about.

**Let `repair` detach restored tracked Installations.**
Rejected: `repair` aligns the active work model with declared records. Detaching a tracked Installation is a user
selection with destructive physical consequences, not a consistency correction.

**Leave physical cleanup to the user.**
Rejected: the share-ownership rules already decide whether a worktree must survive, and duplicating that decision in
manual filesystem steps would break the single-authority invariant.

## Consequences

Users can free a shared checkout while preserving tracked metadata and the ability to restore it later. The command
reuses the existing Installation share ownership rules instead of adding a second cleanup path.

The trade-off is that managed Refs and links remain in place while their target is temporarily unresolved until the
Installation is restored. This is the same state a fresh clone of tracked metadata reaches, and validation accepts
it. Physical cleanup failures are surfaced through a dedicated structured error rather than leaving a partially
detached work model.

## Related

- [Shared commit-hash Installation
  storage](../../implemented/architecture/2026-08-26-shared-commit-hash-installation-storage.md)
- [Remove branch snapshots from import
  remove](../../implemented/feature/2026-08-29-remove-branch-snapshots-with-import-remove.md)
