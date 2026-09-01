# Issue Note: Introduce Presentation-Installation to close recursive Installation-context access

Status: implemented

## Problem

Installation-context mapped a child Installation to an owner-side `presentation-path`, but the owner work model did
not contain an owner-side Installation record for that child. The only owner-side artifacts were the
`InstallationShare` and its `InstallationContextReference`. As a result, a child Installation could not itself be
passed as `--installation-context <INSTALL-ID>` to reach its own sub-Installations. The knowledge-network recursion
stopped one level short.

The ambiguity was worse when the owner and a grandchild referenced the same `(git-url, commit-hash)`: the share could
already exist, but there was no stable owner-side `install-id` for the child to reuse.

The user and Twin Skill wording also said that Installation-context commands cannot mutate the “owner model”. That
phrase was misleading: `import restore` does not mutate the selected Installation's own work model; it only publishes
owner-side share/context-reference state.

## Decision

### Presentation-Installation

A Presentation-Installation is an in-memory, derived commit Installation. It is synthesized when `RuntimeState` loads
from a matching `InstallationShare`, and it is never persisted in `imports.json`, `runtime.json`, or a
`BranchSnapshot`.

The derived record has:

- `tracked` false;
- empty `branch` and `tag`;
- `install-path` equal to the share's commit-derived path;
- `install-id` equal to `install_id_for_path(share.install-path)`;
- no membership in the share's `install-ids`.

The model keeps these invariants:

- every share has exactly one matching commit Installation: either a normal commit Installation or a derived
  Presentation-Installation;
- a Presentation-Installation is never listed in its share's `install-ids`;
- branch and tag Installations are normal Installations and are listed in their share's `install-ids`;
- a context-reference owner may be a normal Installation or a Presentation-Installation;
- derived Presentation-Installations never leak into durable state.

### Creation and promotion

Share creation persists only the `InstallationShare`. The runtime model derives the Presentation-Installation when it
loads.

- `import install --branch` or `--tag` adds only the selector Installation id to `share.install-ids`.
- `import install --commit` persists a normal commit Installation and adds its id to `share.install-ids`, superseding
  the derived twin for that share.
- `import restore` follows the same share/membership path.
- `restore_context_import` persists only the share and context reference; the derived Presentation-Installation appears
  on model load.

### Installation-context recursion

`InstallationRuntimeModelView` maps a local Installation to both:

- `presentation-path`, the owner share's filesystem path;
- `presentation-install-id`, the owner-side commit Installation id.

Installation-context `import query` and `import restore` return `presentation-install-id` when `presentation-path`
exists. That id can be passed as the next `--installation-context <INSTALL-ID>`, closing the recursive loop.

`resolve_installation_context_by_id` accepts derived Presentation-Installation ids in addition to persisted
Installation ids.

### Removal and cleanup

Normal `import remove --install-id` removes the selected Installation and the context references it owns, then
re-evaluates affected shares. It does not run the Presentation-only share scan.

`import remove --presentation-installation-context` is a targeted selector. It selects active `InstallationShare`
records where:

- `install-ids` is empty;
- `branch-refs` is empty or contains only the current branch.

For each selected share, the command removes the share, its managed physical worktree, and the context references
owned by its derived Presentation-Installation from active shares and branch snapshots. `import remove --auto` also
includes this cleanup.

### Post-checkout merge

`_merge_share_membership` no longer appends target-only share records. Current shares are the repository-global set and
already preserve `branch-refs`. The merge:

- preserves current shares and their `branch-refs`;
- replaces `install-ids` and `context-references` only for keys already present in current;
- replaces normal branch-scoped untracked Installations from the target snapshot;
- leaves Worktrees unchanged.

Presentation-Installations are re-derived from the preserved share set after checkout, so no derived record needs to
be carried through the hook.

### Validation and repair

Validation accepts derived Presentation-Installation ids as valid context-reference owners. Repair continues to align
share worktrees and durable share/context-reference records; it does not create or remove persisted
Presentation-Installation records.

### User surface

User documentation and the Twin Skill describe the recursion hint without explaining the full mechanism:

- Installation-context `import query` and `import restore` expose `presentation-install-id`.
- Use `presentation-install-id` as the next `--installation-context <INSTALL-ID>`.
- `import restore` does not mutate the selected Installation's own work model.

## Verification

- Full pytest suite passes.
- `ruff check whero/doctidex tests` passes.
- `scripts/validate-user-doc-links.py` passes.
- `scripts/validate-version-alignment.py` passes.
- Packaged `_skill_data` was rebuilt from the Twin Skill.

## Consequences

Recursive Installation-context access is now closed: a child Installation has a stable owner-side
`presentation-install-id`, and that id can be reused as another Installation context without creating a normal
owner-side Installation.

The trade-off is a load-time derived projection and a targeted removal selector. Existing runtime states remain
compatible because missing Presentation-Installations are derived from shares rather than migrated.

## Alternatives considered

**Treat the context-mapped child as a normal owner-side Installation.**
Rejected: ordinary Installations should be created only by `import install`. Automatic creation would make removal and
branch-snapshot ownership ambiguous.

**Keep only `presentation-path` and derive an install-id on demand.**
Rejected: `--installation-context` selects a recorded Installation by id. A derived id without a recorded
Installation would not be a valid context handle.

**Always add the Presentation-Installation to the share's `install-ids`.**
Rejected: that would make a branch/tag-created share look like it owns an explicit normal commit Installation.

**Introduce a separate child-access record instead of a commit Installation.**
Rejected: that would add a parallel identity type when the desired behavior is exactly “an owner-side commit
Installation that is presentable but not explicitly installed.”

**Keep the current one-level Installation-context behavior and document it as a limitation.**
Rejected: recursive access across a knowledge network is a core product promise, not an optional edge case.

## Related

- [Shared commit-hash Installation storage](../../implemented/architecture/2026-08-26-shared-commit-hash-installation-storage.md)
- [Restore deterministic install-id from git-url and selector](../../implemented/architecture/2026-08-28-restore-deterministic-install-id-from-git-url-and-selector.md)
- [Select Installation context by install-id argument](../../implemented/architecture/2026-08-27-select-installation-context-by-install-id.md)
- [Support Git branch switching with post-checkout runtime snapshots](../../implemented/feature/2026-08-28-support-git-branch-switching-with-post-checkout-runtime-snapshots.md)
- [Remove branch snapshots from import remove](../../implemented/feature/2026-08-29-remove-branch-snapshots-with-import-remove.md)
- [Add import unload command](../../implemented/feature/2026-08-31-add-import-unload-command.md)
- [Index Presentation-Installations for Installation-context mapping](../bug-fix/2026-09-02-index-presentation-installations-for-installation-context.md)
