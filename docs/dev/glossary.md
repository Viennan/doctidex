# Glossary

Quick lookup for development and design terms. Each entry links to its authoritative explanation with a path-plus-fragment reference. Agent-scaffolding terms are intentionally excluded.

| Term | Short meaning | Authority |
|---|---|---|
| BoundaryPoint | A custom or model-derived path where the current repository's link and scan rules stop. | [overview.md](architecture/overview.md#boundary-points) |
| StructuredLinkAnnotation | A `doctidex` HTML-comment YAML block attached to one Markdown link. | [overview.md](architecture/overview.md#link-and-annotation-semantics) |
| Installation | An external Git source at one fixed commit and one read-only install path. | [overview.md](architecture/overview.md#installation) |
| Restore state | Derived Installation availability: `available`, `restore-required`, or `missing`. | [overview.md](architecture/overview.md#installation) |
| Ref | A managed symbolic link from a repository path into an Installation. | [overview.md](architecture/overview.md#ref) |
| Worktree | A managed, untracked editable Git worktree based on a recorded base commit. | [overview.md](architecture/overview.md#worktree) |
| CustomBoundaryPoint | A tracked boundary declared directly by `boundary-set add`. | [overview.md](architecture/overview.md#boundary-points) |
| CacheItem | A cached bare repository identity and publication state. | [overview.md](architecture/overview.md#domain-model) |
| RuntimeState | The merged tracked and runtime work-model view. | [overview.md](architecture/overview.md#domain-model) |
| InstallationContext | Owner root and install path for an Installation selected by `install-id`. | [overview.md](architecture/overview.md#context-detection) |
| InstallationRuntimeStore | A RuntimeStore adapter that coordinates owner and Installation stores without merging state. | [overview.md](architecture/overview.md#model-adaptation) |
| InstallationShare | One runtime-local relation for a Git URL and commit; it owns the shared physical worktree path and referencing Installation identities. | [installation-shares.md](architecture/installation-shares.md#installationshare) |
| InstallationContextReference | Provenance for a sub-Installation restored from InstallationContext. | [installation-shares.md](architecture/installation-shares.md#installationcontext) |
| CacheStore | The user-level `status.json` store for cached bare repositories. | [stores-transactions.md](architecture/stores-transactions.md#cachestore-transactions) |
| RuntimeStore | The repository-local journaled store for the work model. | [stores-transactions.md](architecture/stores-transactions.md#runtimestore-transactions) |
| StoreCoordinator | Command-level coordination for RuntimeStore repair and cache transaction selection. | [stores-transactions.md](architecture/stores-transactions.md#coordination) |
| Cache-aware command | A command that accesses a bare repository through `StoreCoordinator.with_repository`. | [cache-aware-command-pattern.md](cookbook/cache-aware-command-pattern.md#pattern) |
| Issue Note | A decision or proposal record under `docs/dev/issues`. | [Issue Notes](issues/README.md#issue-notes) |
| Lifecycle | The issue status encoded by its top-level folder. | [Layout and naming](issues/README.md#layout-and-naming) |
| Developing | An Issue Note under active design and implementation. | [Layout and naming](issues/README.md#layout-and-naming) |
