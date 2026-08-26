# Index Decision Pattern

Use this cookbook when adding or removing an in-memory index over `RuntimeState`.

## When this applies

RuntimeStore transactions maintain private indexes consumed by `RuntimeModelView`. A new workflow often appears to need a new index keyed by a single field. Before adding one, check whether an existing index plus a recorded object already provides the same lookup.

## Authority

- [RuntimeStore transactions](../architecture/stores-transactions.md#runtimestore-transactions)
- [Installation share store](../architecture/installation-shares.md)

## Pattern

1. Identify the lookup input and required result.
2. Enumerate the indexes already maintained by `RuntimeTransaction`.
3. Ask whether one existing index returns an object that contains the remaining lookup key.
4. If two existing indexes can be composed into one dictionary lookup each, prefer the composition over a new index.
5. Add a new index only when the composed path is not O(1), or when the same composed path is repeated in many hot workflows.
6. When maintaining indexes, evaluate the full O(1) query space formed by every index and their combinations, not just the one current call site.

## Case study

This issue first proposed `_installation_shares_by_backing`, keyed by `backing-install-id`. The caller already had an `install-id`:

- `_installations_by_id` returns the `Installation`;
- the `Installation` contains `git-url` and `commit-hash`;
- `_installation_shares_by_commit` returns the `InstallationShare` for that pair.

The backing index was redundant. It was removed, leaving only `_installation_shares_by_commit`.

## Verification

1. Find every intended caller of the lookup.
2. Confirm each caller can reach the result through at most one existing-index lookup plus one field read.
3. Confirm the new index would not serve a different query class omitted by those callers.
4. Run the relevant pytest suite and `ruff`.

## Anti-patterns

- Do not add an index for one local call site without checking the existing query space.
- Do not key an index by a field that is already recoverable from a returned object.
- Do not leave an index in place after its only caller is removed.
