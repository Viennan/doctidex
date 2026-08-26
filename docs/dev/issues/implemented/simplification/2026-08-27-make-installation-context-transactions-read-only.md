# Issue Note: Make Installation-context transactions read-only

Status: implemented

## Problem

[installation.py](../../../../../src/python/whero/doctidex/installation.py) previously exposed a writable Installation transaction for `import restore`, but the restore path never used it. `imports.restore_context_import` already opened the owner write transaction directly and read the Installation-local model with an unlocked read-only snapshot.

`InstallationRuntimeModelView._mapped_installation` also resolved the owner-side record with `installation_for_commit`, even though `imports.restore_context_import` creates or reuses the owner-side record under the same `install-id` as the local record. Commit-based lookup was order-dependent, could match an unrelated owner Installation when several selectors resolved to the same commit, and could return no match before restore even though the local record should remain queryable.

## Decision

This refines the InstallationContext mapping introduced in [Shared commit-hash Installation storage](../architecture/2026-08-26-shared-commit-hash-installation-storage.md).

`InstallationRuntimeStore` is a read-only Installation-context adapter. It exposes `read_only_transaction` and `restore_import`; `write_transaction` and `InstallationWriteTransaction` are removed. `restore_import` remains the only mutating operation and delegates to `imports.restore_context_import`.

`InstallationRuntimeModelView._mapped_installation` resolves the owner-side Installation by `install-id`. When no owner-side record exists, it returns the local Installation with `presentation_path=None`, so the local record remains queryable before restore. When the owner-side record exists, it supplies the owner-side `presentation-path`.

`import query` in Installation context therefore omits `presentation-path` until the local Installation has been restored. The user reference documents state that a missing `presentation-path` means the Installation has not been restored, and that the user must run `import restore --install-id <INSTALL-ID>` in the same Installation context.

The owner-side mutation and `InstallationContextReference` bookkeeping remain in [installation-shares.md](../../../architecture/installation-shares.md#installationcontext). The read-only adapter shape is reflected in [overview.md](../../../architecture/overview.md#installation-context-behavior).

## Testing

The full suite passes with 88 tests. Coverage is 86%. `ruff check` and `git diff --check` pass. The Installation-context regression test covers the read-only transaction surface and the pre-restore and post-restore query mapping.

## Alternatives considered

**Route `import restore` through `InstallationRuntimeStore.write_transaction`.**

Rejected: the restore path must coordinate an owner write transaction with an Installation-local read snapshot, and its owner mutation must be scoped to the specialized `restore_context_import` workflow. A generic write transaction would still expose only a read-only Installation model view and would not own the required provenance logic.

**Make `InstallationWriteTransaction.write_model_view()` return the owner `RuntimeWriteModelView`.**

Rejected: that would allow generic owner mutation through the Installation adapter, broadening the Installation-context surface beyond `import restore` and hiding the context-reference rules in [installation-shares.md](../../../architecture/installation-shares.md#installationcontext).

**Remove the Installation transaction classes entirely and open the owner and local stores in each command.**

Rejected: the coordinated `InstallationRuntimeModelView` is still needed by `boundary-set parse` and `import query` to map Installation-local records to owner `presentation-path` values.

**Keep resolving the owner-side Installation by `installation_for_commit`.**

Rejected: `imports.restore_context_import` already preserves the local `install-id` in the owner model, so `installation_for_commit` is an indirect and order-dependent lookup. It can match an unrelated branch or tag Installation that resolves to the same commit, or return no match before restore even though the local record should remain visible.

## Consequences

The Installation-context adapter no longer presents a generic write surface. `import restore` remains the only owner-mutating operation, so the public API matches the command admission table.

The mapping change makes Installation-context query results deterministic by identity rather than by commit. Before restore, users see a local Installation without `presentation-path` and must run restore to make it accessible in the owner tree; this behavior is documented in [common.md](../../../../../docs/user/reference/common.md#installation-context) and [import.md](../../../../../docs/user/reference/import.md#installation-context).
