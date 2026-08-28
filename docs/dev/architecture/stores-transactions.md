# Doctidex Git Stores and Transactions

This document defines the current transactional design for the two durable stores used by `doctidex-git`: the user-level CacheStore and the repository-local RuntimeStore. It is authority for their publication, recovery, and coordination behavior.

## Purpose and scope

The stores are not database transactions. Their goal is recoverable model state under cooperating `doctidex-git` processes, not reversal of every filesystem or Git side effect.

Two stores serve different lifecycles:

| Store | Authority | Durable unit |
|---|---|---|
| CacheStore | Cached bare Git repositories | `status.json` |
| RuntimeStore | One Git root's managed work model | `boundary-set.json`, `imports.json`, `import-refs.json`, `runtime.json` |

## Common primitives

Both stores use:

- advisory shared and exclusive `FileLock`s backed by `fcntl.flock`;
- same-directory temporary files followed by atomic rename;
- `fsync` on files and parent directories;
- SHA-256 digests for observation and recovery.

These primitives provide serialization and durable publication without a general transaction manager.

## CacheStore transactions

CacheStore publishes one `status.json` document containing `CacheItem` records.

### Read-only transaction

A read-only transaction enters with a shared lock, reads `status.json`, and exposes the resulting records. If `preparing` records are present, it releases the shared lock, acquires an exclusive lock, removes the interrupted `preparing` records and their cache directories, publishes the cleaned record set, reacquires the shared lock, and checks again. It repeats that recovery at most three times and fails if `preparing` records remain.

### Write transaction

A write transaction acquires an exclusive lock, performs startup recovery, and supports `replace_records`. A record replacement writes `status.json` atomically and becomes visible immediately. It does not journal the replacement.

### Startup recovery

On entry, every `preparing` CacheItem is treated as an interrupted publication. Its validated cache-local directory is removed and the record is dropped. A later cache miss can create a fresh `preparing` record, clone the bare repository, then publish it.

Bare Git object changes are real external side effects and are not reversed by CacheStore.

## RuntimeStore transactions

RuntimeStore owns four projection files for one Git root. A write transaction journals its existence before it may publish any state change.

### Journal model

A journal is stored under `/.doctidex-git/.transactions/<transaction-id>/journal.json`.

| Journal state | Meaning |
|---|---|
| `prepared` | The transaction exists and may have staged backups. |
| `publishing` | State files are being atomically replaced. |
| `committed` | All state files have been published. |

Each journal entry records:

- `target`: a state file name;
- `old-sha256`: the digest before publication, or null when absent;
- `new-sha256`: the expected digest after publication;
- `stage` and `backup`: transaction-local paths.

### Write transaction lifecycle

1. Acquire the exclusive RuntimeStore lock.
2. Reject startup if any pending journal exists by raising `RepairRequired`.
3. Load the current RuntimeState and snapshot target hashes.
4. Create a transaction directory and write a `prepared` journal immediately.
5. Apply in-memory model changes.
6. On successful exit, commit changed state files using the staged/backup/journal sequence.
7. On failed or unchanged exit, clean the journal without publication.

### Commit protocol

Commit writes staged contents, backs up old files, moves the journal to `publishing`, atomically replaces each changed target, moves the journal to `committed`, then removes the transaction directory. If no state file changed, the journal is removed without publication.

### Recovery

Repair inspects residual journals and compares each target's current digest with `old-sha256` and `new-sha256`. Committed journals must show only `new` digests. Uncommitted journals either restore `old` state or keep `new` state depending on observation. Mixed observations require backup restoration before physical repair.

### Read-only and diagnostic access

- `read_only_transaction` acquires a shared lock and refuses pending journals.
- `read_diagnostic_transaction` acquires a shared lock, reports pending journals, and may avoid loading inconsistent state.
- `repair_transaction` acquires an exclusive lock, reports pending journals, and exposes the repair model view and narrowed Ref publication used by repair.
- `unlocked_read_only_transaction` reads a snapshot without the RuntimeStore lock for already-isolated contexts, such as Installation-local model access.

### Single-file runtime hook publication

The post-checkout hook updates only `runtime.json`. It acquires the RuntimeStore exclusive lock, reads and transforms
that one document, publishes it with the same atomic-write primitive, and runs physical Installation alignment before
releasing the lock. It does not create a journal because the complete four-file model can be inconsistent during a Git
branch switch.

## Coordination

`StoreCoordinator` is a plain coordination object; it does not own a command lock. A normal RuntimeStore transaction that observes a residual journal raises `RepairRequired`; the coordinator runs `repair_core` outside the failed transaction and retries the operation. Explicit repair remains the `repair(store, cache)` entry point in the repair workflow.

Cache-backed work selects a cache transaction first:

- a cache hit starts read-only;
- if RuntimeStore repair becomes necessary, the read-only cache transaction exits before a write transaction performs repair;
- a cache miss starts write and may reuse that write transaction for repair.

Repair is retried up to three times. Exhaustion becomes a structured store failure. `repair_core` requires a caller-owned GitCache write transaction and acquires the RuntimeStore repair lock itself.

Commands needing both domains acquire cache access before RuntimeStore access.

## Constraints

- RuntimeStore journaling covers only the four state projection files.
- CacheStore publication is immediate and not journaled.
- Recovery converges declared state and managed paths; it does not undo Git fetches, bare object additions, or user commits.
- Direct edits by users or unrelated programs are not protected by the coordination protocol.

## Implementation responsibilities

| Responsibility | Implementation |
|---|---|
| CacheStore records and transactions | [store/cache.py](../../../src/python/whero/doctidex/store/cache.py) |
| RuntimeStore journal and transactions | [store/runtime.py](../../../src/python/whero/doctidex/store/runtime.py) |
| File primitives and locks | [store/files.py](../../../src/python/whero/doctidex/store/files.py) |
| Command coordination and repair retry | [coordination.py](../../../src/python/whero/doctidex/coordination.py) |
| Repair workflow | [repair.py](../../../src/python/whero/doctidex/repair.py) |
| Single-file runtime hook publication | [hooks.py](../../../src/python/whero/doctidex/hooks.py), [store/runtime.py](../../../src/python/whero/doctidex/store/runtime.py) |
