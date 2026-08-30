# Cache-Aware Command Implementation Pattern

Use this cookbook when adding or changing a `doctidex-git` command that may read or load a bare Git repository from the user-level cache.

## When this applies

Most commands other than `init`, `validate`, and `repair` may need a Git source during normal execution. Examples are `import install`, `import restore`, `import ref`, `worktree create`, and any future command that resolves an external Git revision.

These commands must follow the same transaction and coordination pattern so RuntimeStore recovery and CacheStore publication remain correct.

## Authority

Read the architecture first:

- [overview.md](../architecture/overview.md)
- [stores-transactions.md](../architecture/stores-transactions.md)

## Pattern

1. Resolve the selected Git root.
2. Resolve Installation context when applicable.
3. Build the correct RuntimeStore variant:
   - ordinary path: `RuntimeStore`
   - Installation path: `InstallationRuntimeStore`
4. Create `StoreCoordinator(store, GitCache.from_environment())`.
5. Define the command operation as a closure that receives only the store and coordinator.
6. Use `coordinator.run` for RuntimeStore-only work.
7. Use `coordinator.with_repository(git_url, operation)` for work that needs a bare repository.
8. Treat the repository path returned by `with_repository` as valid only inside that operation.
9. Return a structured `CommandPayload` from the command workflow; do not write CLI output inside store workflows.

## Code sketch

```python
@_command_result()
def _run_example(
    operation: ParsedInvocation,
    root: Path,
    args: argparse.Namespace,
) -> CommandPayload:
    store = _command_runtime_store(root)

    with StoreCoordinator(store, GitCache.from_environment()) as coordinator:
        def execute() -> CommandPayload:
            def use_repository(repository: Path) -> CommandPayload:
                # Keep all Git work and physical side effects here.
                resolved = resolve_revision(repository, args.url, ...)
                with store.write_transaction() as transaction:
                    view = transaction.write_model_view()
                    # Modify the RuntimeState through the write view.
                    ...
                return success(command=operation.command)

            return coordinator.with_repository(args.url, use_repository)

        return coordinator.run(execute)
```

## Verification

1. Cache hit path:
   - Run the new command twice against the same Git URL.
   - Confirm the second run uses an existing published repository and does not clone again.

2. Cache miss path:
   - Run the command against a new Git URL.
   - Confirm `cache-status.json` receives a published `CacheItem` and the bare repository is usable under
     `data/<domain>/<repository...>`.

3. Interrupted cache publication:
   - Simulate a `preparing` record with an invalid or missing cache directory.
   - Run any cache transaction entry point.
   - Confirm the `preparing` record and cache directory are removed before normal work starts.

4. RuntimeStore recovery:
   - Leave a residual transaction journal or simulate `RepairRequired`.
   - Run the command through `StoreCoordinator`.
   - Confirm repair is attempted and the command retries or reports a structured failure after the retry limit.

5. Physical side effects:
   - Confirm all `git clone`, `git worktree`, and other external Git effects happen inside `with_repository` or another cache transaction.
   - Confirm no bare repository path is retained and used after the transaction closes.

6. Project checks:
   - Run the relevant pytest suite.
   - Run `ruff` and `git diff --check`.

## Anti-patterns

- Do not call `GitCache` transaction methods directly from CLI handlers.
- Do not clone or access a bare repository outside a cache transaction.
- Do not mix RuntimeStore and cache access without `StoreCoordinator`.
- Do not keep a `Path` returned by `with_repository` after the operation returns.
- Do not emit user-facing output inside workflow functions.
