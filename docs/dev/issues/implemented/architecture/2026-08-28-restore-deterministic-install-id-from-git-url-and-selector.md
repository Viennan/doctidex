# Issue Note: Restore deterministic install-id from git-url and selector

Status: implemented

## Problem

`doctidex-git` was originally designed to derive one `install-id` from one Git URL plus one revision selector.
During a scaffolding change, the implementation began generating `install-id` with `uuid.uuid4().hex`. That broke the
source/selector identity contract, prevented inverse lookup from the selector-derived `install-path`, and allowed
single-value runtime indexes to silently hide duplicate identities.

Installation-context restore had the same drift: it created or reused an owner-side `Installation` for an
Installation-local sub-Installation, even though the intended model is mapping through
`InstallationShare.context-references` only.

## Decision

### Installation identity

An `install-id` is the first 16 hexadecimal characters of the SHA-256 digest of a selector-kind-aware
`install-path`:

```text
branch: /.doctidex-git/imports/<domain>/<repository...>/branch/<escaped-value-segments>
tag:    /.doctidex-git/imports/<domain>/<repository...>/tag/<escaped-value-segments>
commit: /.doctidex-git/imports/<domain>/<repository...>/<commit-hash>
install-id = first-16-hex-chars(sha256(selector-path))
```

Branch and tag names keep their identity when the selector re-resolves to a new commit. A direct commit uses the
commit hash. The 16-hex digest is short and readable for LLM consumers. If a derived id collides with an Installation
at a different path, installation fails with `installation.id.collision`.

`_selector_install_path` and `_install_id` live in `imports.py` as private helpers. No shared identity module exists.

### Install and restore

`import install` computes the selector path and id once. Branch/tag re-resolution updates `commit-hash` in place and
keeps `install-id`, `install-path`, and Refs stable. Direct-commit reinstall reuses the Installation at the share path.
`replace_installation` is removed because no command changes an `install-id` anymore.

`import restore` restores the recorded commit without re-resolving the branch or tag and keeps the existing
`install-id`.

### Runtime indexes and ModelView

The transaction maintains unique identity maps and relation projections:

```text
unique identity maps:
  Installation by install-id
  Installation by install-path
  InstallationShare by (git-url, commit-hash)
  Ref by target-dir
  Worktree by work-path
  CustomBoundaryPoint by path

relation projections:
  Ref by install-id
  InstallationContextReference by (owner-install-id, install-id)

derived projection:
  BoundaryPoint list and exact-path lookup
```

`_installations_by_source` and `_installations_by_commit` are removed. `installation_for_selector` and
`installation_for_commit` are removed from `RuntimeModelView`; selector-to-id derivation belongs only to the import
workflow. `InstallationRuntimeModelView` forwards only the Installation-context surface used by commands and link
scanning.

### Installation-context mapping

`restore_context_import` ensures the owner `InstallationShare` for the sub-Installation's `(git-url, commit-hash)` and
records one `InstallationContextReference`. It does not create an owner-side Installation and does not add the
sub-Installation id to `share.install-ids`.

The context reference is keyed by `(owner-install-id, install-id)` because the same local id can be restored through
different InstallationContexts and resolve to different commits. `InstallationRuntimeModelView._mapped_installation`
uses that index and sets `presentation-path` to the owner share path when the share is available.

### Validation and architecture

Validation distinguishes `install-ids` from `context-references`. A share `install-id` must resolve to an owner
Installation; a context-reference sub-install id does not. Missing context-reference owners are reported as
`installation.context-reference.owner.missing`.

The Installation share architecture and Installation-context behavior in `installation-shares.md` and `overview.md`
describe the new selector-kind paths and context-reference-only mapping. `stores-transactions.md` documents the
`InstallationRuntimeStore` and `InstallationReadOnlyTransaction` behavior.

## Testing

The full test suite passes. Coverage is 87%. `ruff check src/python/whero/doctidex src/python/tests` and
`git diff --check` pass. Tests cover deterministic branch/tag/commit ids, same-named branch/tag separation,
branch/tag re-resolution, Installation-context restore without an owner-side record, and context-reference validation.

## Related

- [Shared commit-hash Installation storage](2026-08-26-shared-commit-hash-installation-storage.md)
- [Select Installation context by install-id argument](2026-08-27-select-installation-context-by-install-id.md)
- [Support Git branch switching with post-checkout runtime snapshots](../feature/2026-08-28-support-git-branch-switching-with-post-checkout-runtime-snapshots.md)
- [Installation share store](../../../architecture/installation-shares.md)
- [Doctidex Git Stores and Transactions](../../../architecture/stores-transactions.md)

## Alternatives considered

**Keep UUID install-ids and add a separate deterministic source/selector lookup table.**
Rejected: it preserves two identity systems and leaves the recorded `install-id` disconnected from the stable lookup.

**Derive `install-id` from `git-url + resolved-commit` instead of `git-url + selector`.**
Rejected: it collapses branch and tag identity and changes the id when a moving selector re-resolves.

**Keep the owner-side substitute Installation and add context references on top.**
Rejected: it preserves the misleading owner Installation and duplicates the relationship already represented by
`context-references`.

**Leave index construction unchanged and add validation-only duplicate checks.**
Rejected: load-time lookups would still silently discard or overwrite records before validation could explain the
conflict.

## Consequences

The change restores a stable, deterministic Installation identity and makes selector-derived paths invertible.
Branch/tag re-resolution no longer changes `install-id` or rewires Refs, and Installation-context restore no longer
introduces a substitute owner Installation.

The cost is a selector-kind-aware path layout and a new context-reference relation index. Existing persisted random
`install-id` values are not migrated by this decision.
