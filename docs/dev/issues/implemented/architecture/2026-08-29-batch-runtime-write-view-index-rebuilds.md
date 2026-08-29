# Issue Note: Batch RuntimeWriteModelView index rebuilds

Status: implemented

## Problem

Every `RuntimeWriteModelView` mutation previously reached `RuntimeWriteTransaction._replace_collections`, which
immediately rebuilt every private lookup index through `_set_state` and `_reindex`. Multi-mutation write commands
therefore paid repeated full index rebuilds inside a transaction that already held the exclusive RuntimeStore lock.

## Decision

State publication and index maintenance are separate. Write paths change state as often as needed and rebuild indexes
only when a later query actually consumes them.

### Deferred index maintenance

`RuntimeTransaction` keeps an `_indexes_dirty` flag. `_set_state` records the new state and marks indexes dirty;
`ensure_indexes_current` runs `_reindex` only while the flag is set. Transaction entry calls
`ensure_indexes_current`, so fresh read transactions start with current indexes.

### Decorated index queries

`RuntimeModelView` has a `_requires_current_indexes` decorator. It calls
`self._transaction.ensure_indexes_current()` before every index-consuming query, including the `boundary_points`
getter. Direct state accessors are not decorated.

The decorator preserves read-your-writes semantics while allowing write-only code to compute from `self.state`
without paying for an index rebuild.

### Bulk collection replacement

`RuntimeWriteModelView.replace_installation_shares` publishes a complete active share collection in one write-view
call. Branch snapshot removal and multi-Installation `import remove` now compute final collections once and publish
them once instead of looping over per-record `upsert` or `remove` calls.

### Commit behavior

Commit publishes `RuntimeState` documents and does not require private indexes. A write transaction whose final
mutation is not followed by an index-consuming query commits without a full `_reindex`.

### Write-surface audit

The completed audit found:

- `boundary-set add/remove`, `worktree create/remove`, and `repair` already batch or perform a single write.
- `hook post-checkout` publishes `runtime.json` directly and does not use `RuntimeWriteModelView`.
- `import install`, `restore`, `track`, `ref`, and `unref` are single-record or physical-then-single-write flows.
- `import remove` is batch-aware through `_remove_installations_batch`.

## Verification

The full test suite passes, `ruff check src/python/whero/doctidex src/python/tests` passes, and `git diff --check`
passes. Tests cover deferred reindex counting, decorated query freshness after mutation, bulk share replacement, and
multi-Installation batch writes.

## Consequences

Multi-mutation write commands now avoid repeated full index rebuilds, and write-only transactions can commit without
an unnecessary reindex. The cost is a correctness obligation: every index-consuming query must carry the
`_requires_current_indexes` decorator, and batch flows must avoid write-then-lookup interleaving.

## Alternatives considered

**Only batch the branch snapshot removal workflow.**
Rejected: it removes one symptom but leaves every other multi-mutation write command with the same repeated reindex
cost.

**Maintain every index incrementally on each mutation.**
Rejected: incremental updates touch many derived relations and are more error-prone than a dirty flag plus on-demand
full rebuild. It can be revisited if profiling shows on-demand full rebuild is insufficient.

**Keep immediate reindexing and only optimize `_replace_collections`.**
Rejected: it reduces per-call cost but does not remove the repeated rebuild itself.

**Introduce a general changeset DSL for all writes.**
Rejected: the existing write view already carries current state; a second update language adds contract complexity
without a demonstrated need beyond deferred indexing and bulk replacement.

## Related

- [Remove branch snapshots from import remove](../feature/2026-08-29-remove-branch-snapshots-with-import-remove.md)
- [Restore deterministic install-id from Git URL and
  selector](2026-08-28-restore-deterministic-install-id-from-git-url-and-selector.md)
