# Issue Note: Optimize store lock modes and transaction roles

Status: implemented

## Problem

`FileLock` only supported an exclusive lock: every `acquire` call took `fcntl.LOCK_EX`. RuntimeStore transactions that were named read-only still entered through `RuntimeTransaction.__enter__`, which acquired that same exclusive lock. Read-only RuntimeStore snapshots therefore serialized with writers and with each other even though they only loaded state and built model views.

`StoreCoordinator` added a separate command-level `.command.lock` around one CLI command and exposed that lock through a context-manager interface. Its actual responsibilities were different: retry operations that raised `RepairRequired`, and route cache-backed work so cache access preceded RuntimeStore access. The command lock did not own either responsibility, and every caller wrapped a closure in `with StoreCoordinator(...)` only to reach `run` or `with_repository`.

`RuntimeDiagnosticTransaction` was used by both read and write paths. `validate` and Installation-context detection used it to report pending journals without mutating state, while `repair_core` used the same type to reload state, obtain the repair model view, and publish `import-refs.json`. A read-only diagnostic transaction therefore carried a write surface, and a repair writer could be mistaken for a validation reader.

## Decision

The store layer now separates lock mode from transaction responsibility.

`FileLock` exposes `acquire_shared` and `acquire_exclusive`, both backed by `fcntl.flock`, and one mode-agnostic `release`. A caller must release a shared lock before requesting an exclusive lock; there is no atomic upgrade path.

CacheStore read-only transactions enter with a shared lock and recover interrupted `preparing` records in `__enter__`: they release the shared lock, acquire an exclusive lock, remove the records and their cache-local targets, publish the cleaned record set, reacquire the shared lock, and check again. They repeat at most three times and then raise `StoreFailure`. CacheStore write transactions acquire an exclusive lock and recover `preparing` records directly.

RuntimeStore transactions are separated by both lock mode and mutation capability:

| Transaction | Lock | Role |
|---|---|---|
| `RuntimeReadOnlyTransaction` | shared | Read state and build a normal model view; refuse pending journals with `RepairRequired`. |
| `RuntimeReadDiagnosticTransaction` | shared | Report pending journals for `validate` and Installation-context detection; no reload, repair model view, or write methods. |
| `RuntimeRepairTransaction` | exclusive | Inspect pending journals, reload state, expose the repair model view, and publish repair's narrowed Ref cleanup. |
| `RuntimeWriteTransaction` | exclusive | Keep the journaled business write path. |
| `RuntimeUnlockedReadOnlyTransaction` | none | Read an already-isolated snapshot without a store lock. |

`RuntimeStore` exposes `read_diagnostic_transaction` and `repair_transaction` instead of `diagnostic_transaction`. `validate` and Installation-context detection use the read form; `repair_core` uses the repair form. `replace_refs_for_repair` exists only on `RuntimeRepairTransaction`.

`StoreCoordinator` is a plain coordination object. It exposes `run` and `with_repository`, and has no context-manager interface, no `.command.lock`, and no public `repair` method. Explicit repair is `repair(store, cache)` in `repair.py`; the CLI repair command calls it directly. `repair_core` is the package-internal seam used by coordinator retry paths. It requires a caller-owned `GitCacheWriteTransaction` and acquires the RuntimeStore repair lock itself.

Cache-backed work still acquires cache access before RuntimeStore access. The architecture documents in [stores-transactions.md](../../../architecture/stores-transactions.md) and [overview.md](../../../architecture/overview.md) describe the current behavior.

## Related

This decision follows the coordination boundary recorded in [Add sad/bad-path testing guidance and bound coordination guarantees](../../implemented/architecture/2026-08-24-sad-bad-path-testing-and-coordination-scope.md), the Installation-context read-only shape in [Make Installation-context transactions read-only](../../implemented/simplification/2026-08-27-make-installation-context-transactions-read-only.md), and the Installation storage model in [Shared commit-hash Installation storage](../../implemented/architecture/2026-08-26-shared-commit-hash-installation-storage.md).

## Testing

The full suite passes with 96 tests and 86% coverage. `ruff check` and `git diff --check` pass.

[test_store_concurrency.py](../../../../../src/python/tests/test_store_concurrency.py) exercises cooperating CLI processes for concurrent reads, writer/reader completion without `.command.lock`, and residual-journal repair. [test_store_recovery.py](../../../../../src/python/tests/test_store_recovery.py) covers CacheStore `preparing` cleanup, recovery exhaustion, the read diagnostic surface, and the repair transaction surface.

## Consequences

Side-effect-free RuntimeStore readers can run concurrently instead of serializing behind one exclusive lock. CacheStore readers remain concurrent in the normal case and use a short exclusive recovery pass only when interrupted records are present.

`StoreCoordinator` no longer adds command-wide serialization on top of store locks and journals. The remaining correctness mechanisms are cache-before-RuntimeStore ordering and the RuntimeStore write journal.

Repair and validation no longer share a transaction type, so a validation reader cannot reach repair's reload, repair-model-view, or Ref-publication operations.

The CacheStore read path now changes lock modes around recovery. The three-pass limit bounds recovery when another cooperating process repeatedly introduces `preparing` records; exhaustion becomes a structured store failure.

## Alternatives considered

**Remove the command lock but keep `StoreCoordinator` as a context manager.**
Rejected: an empty enter/exit pair would preserve only syntactic ceremony, and the methods already own cache and RuntimeStore transaction lifetimes. A plain object states the same contract with less surface.

**Keep CacheStore read-only on an exclusive lock.**
Rejected: it leaves cache readers serialized for every read even though interrupted `preparing` records are an edge case. The status model is simple enough for the read entry path to release and reacquire the shared lock around a short recovery pass.

**Make CacheStore read-only purely side-effect-free and move `preparing` recovery only to write transactions.**
Rejected: a read-only command could then observe `preparing` records as available cache entries, or be forced to fail when a write transaction is not otherwise required. In-place recovery preserves the current read-command behavior without requiring a separate maintenance entry point.

**Keep one diagnostic transaction and add a boolean or mode flag.**
Rejected: a mode flag leaves the write methods available on read callers and relies on call-site discipline. Separate types make read and repair capabilities visible in the type system, matching the existing separation between read and write model views.

**Use a normal `RuntimeWriteTransaction` for repair.**
Rejected: that transaction refuses pending journals and journals its own existence before loading state. Repair must first inspect and reconcile residual journals, so it needs a recovery-shaped transaction rather than the normal business write path.
