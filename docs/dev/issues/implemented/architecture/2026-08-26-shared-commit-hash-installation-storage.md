# Issue Note: Shared commit-hash Installation storage

Status: implemented

## Problem

Every `import install` and `import restore` previously created one detached Git worktree at the Installation's `install-path`. The path was derived from the Git URL and the requested revision selector, so a branch, a tag, and an explicit commit that all resolved to the same `(git-url, commit-hash)` still received separate worktrees under `/.doctidex-git/imports/`.

That duplicated read-only checkouts and model records without adding information. The duplication was already unnecessary for recursive Installation use: `InstallationRuntimeModelView` preserves the local record and, once restored, maps `presentation-path` to the owner-side Installation with the same `install-id`.

The change is limited to Installation storage. The `worktree` command family keeps its current storage organization and editable Worktree semantics.

## Decision

Installation sharing uses an `InstallationShare` stored in `runtime.json`. The share owns the physical detached Git worktree for one `(git-url, commit-hash)`.

### Storage model

Each share records:

- `git-url` and `commit-hash` for the shared revision;
- `install-path` for the single real worktree path;
- `install-ids` for every Installation that resolves to that commit;
- `context-references` for sub-Installations restored from InstallationContext.

The share path is organized like the former commit-hash Installation path:

`/.doctidex-git/imports/<domain>/<repository>/<commit-hash>`

There is no hidden backing Installation and no physical-owner transfer among Installations.

### Physical paths

A direct commit Installation's `install-path` equals `share.install-path`. Branch and tag Installations keep their selector-derived `install-path` and are symlinks to `share.install-path`.

### Install and restore

`import install` and `import restore` share one sequence:

1. resolve the selector to `(git-url, commit-hash)`;
2. find or create the share;
3. create the real worktree when the share is new;
4. add the Installation `install-id`;
5. make the Installation path a real worktree for a direct commit or a symlink for a branch or tag.

Branch and tag re-resolution moves the Installation between shares.

### Removal

Removing an Installation removes its `install-id` and physical path. The share and its real worktree survive while any reference remains. When the last reference disappears, the share and worktree are deleted together.

### InstallationContext

`import restore` with `--installation-context <INSTALL-ID>` resolves the parent Installation by its recorded `install-id`, records or reuses the owner-side Installation under the local `install-id`, and stores an `InstallationContextReference` naming the parent Installation. The explicit selector contract is defined by [Select Installation context by install-id argument](2026-08-27-select-installation-context-by-install-id.md).

The read-only adapter and identity-based `presentation-path` mapping are defined by [Make Installation-context transactions read-only](../simplification/2026-08-27-make-installation-context-transactions-read-only.md).

### Validation and repair

Validation checks the share worktree, every share reference, direct commit paths, and branch/tag symlinks. Repair aligns the share worktree first, then restores selector symlinks and removes unregistered Installation symlinks.

The architecture document is [installation-shares.md](../../../architecture/installation-shares.md). The user-visible symlink behavior is documented in [import.md](../../../../user/reference/import.md).

## Testing

The full suite passes with 87 tests. Coverage is 85%. `ruff check` passes and `git diff --check` passes. Tests cover share round-tripping, shared physical paths, branch and tag symlinks, direct commit reuse, removal semantics, InstallationContext provenance, validation, and repair.

## Alternatives considered

**Let the first `install-id` own the physical worktree and transfer ownership on removal.**
Rejected: it made `install-ids` order semantically meaningful and required owner-transfer handling. Keeping `install-path` on the share gives the worktree one stable owner.

**Use a hidden backing Installation and derive a direct self-reference.**
Rejected: it introduced a synthetic Installation that had to be filtered from query and selection, plus a persisted or derived `direct` flag. The share-owned path avoids both.

**Use the resolved commit-hash path directly as the branch or tag `install-path`.**
Rejected: it eliminated symlinks but leaked long commit hashes into primary user-facing paths, harming LLM readability and stability.

**Keep one detached Git worktree per revision selector.**
Rejected: that was the previous behavior and the source of redundant checkouts.

**Store branch and tag selectors as aliases on one Installation record.**
Rejected: branch, tag, and commit selectors are distinct Installation identities with their own `install-id`, keys, and selection semantics.

**Reuse the Worktree service storage for shared commit checkouts.**
Rejected: Worktrees are editable and untracked, while Installations are read-only.

**Persist the sharing relation in tracked declarations.**
Rejected: which Installations resolve to the same commit is a machine-local runtime fact, not a reproducible declaration.

## Consequences

The change removes redundant worktrees for Installations that resolve to the same commit while preserving stable branch and tag paths. The share is the single authority for physical worktree ownership, and Installation identities remain separate from physical storage.

The cost is a new runtime-only share relation and additional validation/repair rules. Branch and tag `install-path` values are now symlinks, so physical checks and repair must distinguish symlink paths from the share's real worktree.

## Related

- [Support Git branch switching with post-checkout runtime snapshots](../feature/2026-08-28-support-git-branch-switching-with-post-checkout-runtime-snapshots.md)
