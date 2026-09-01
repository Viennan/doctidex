# Issue Note: Index Presentation-Installations for Installation-context mapping

Status: implemented

## Problem

`InstallationRuntimeModelView._mapped_installation` resolved the selected Installation context with
`owner_view.installation_at(context.install_path)`. That lookup covered only persisted `RuntimeState.installations`.
When the selected context was a derived Presentation-Installation, the owner lookup returned `None`, and the mapped
child Installation lost both `presentation-path` and `presentation-install-id`. Recursive Installation-context access
therefore stopped at the first Presentation-Installation owner.

The same derived records were also absent from boundary derivation, so boundary-aware scans did not treat a
Presentation-Installation's `install-path` as an import boundary.

## Decision

### Read-side Installation universe

`RuntimeState.installations` is the persisted Installation collection.
`RuntimeState.presentation_installations` is the derived, in-memory collection.

`RuntimeTransaction._reindex` builds `_installations_by_id` and `_installations_by_path` from both collections, with
persisted Installations winning on collision. `RuntimeModelView.installation` and `installation_at` resolve both
record kinds. `RuntimeModelView.installations` still returns only `state.installations`.

`RuntimeModelView.persisted_installation` exposes a persisted-only lookup for mutation workflows.

### Persisted-only mutation lookup

Write-facing Installation resolution uses `persisted_installation`. `imports._find_installation`,
`imports._select_installations`, `imports.restore_context_import`, `imports._install_resolved`, Worktree's
Installation read path, and repair's Ref alignment all reject or exclude derived Presentation-Installations instead of
treating them as mutable persisted records. `RuntimeWriteModelView.upsert_installation` also uses the persisted-only
lookup, so installing a normal commit Installation with the same id as an existing Presentation-Installation adds the
normal record rather than mistaking the derived twin for it.

### Installation-context mapping

`resolve_installation_context_by_id` uses `model_view.installation` without a separate Presentation-Installation
fallback. `_mapped_installation` needs no special case: an owner-side `installation_at` lookup now returns the derived
owner record, and the existing context-reference/share-path logic produces the owner-side presentation fields.

### Derived boundaries

Each Presentation-Installation contributes an `import` boundary point for its `install-path`. The boundary is derived
by `RuntimeState.boundary_points` and is not written to `boundary-set.json`, `imports.json`, or `runtime.json`.
Boundary-aware scans and `boundary-set parse` therefore recognize Presentation-Installation paths without persisting
derived Installation records.

### Hook command resolution

`hooks._command_path` prefers the repository-local `.venv/bin/doctidex-git` entry point before falling back to a
`doctidex-git` found on `PATH`. This keeps hook-install behavior deterministic in repository-local test and development
environments.

## Verification

- The complete pytest suite passes without exclusions.
- `ruff check src/python/whero/doctidex src/python/tests` passes.
- `scripts/validate-user-doc-links.py --docs-root docs/user --references-root skills/doctidex-git/references` passes.
- `scripts/validate-version-alignment.py` passes.
- `git diff --check` passes.

## Consequences

Recursive Installation-context access now works when an intermediate owner is a Presentation-Installation. Read-side
queries can see derived records, while write workflows remain limited to persisted Installations. Derived records stay
out of durable state and share membership, and their install paths participate in boundary-derived scope without being
materialized as durable boundary declarations.

The hook command-resolution change removes a test-environment dependency on a pipx `doctidex-git` executable being
earlier in `PATH` than the repository-local entry point.

## Alternatives considered

**Patch `_mapped_installation` to search `state.presentation_installations` directly.**
Rejected: that fixes one caller while leaving `installation` and `installation_at` inconsistent. The same special-case
would reappear in future read paths.

**Materialize the Presentation-Installation as a normal owner-side Installation.**
Rejected: ordinary Installations should be created only by `import install` or `import restore`; automatic persistence
would make removal and branch-snapshot ownership ambiguous.

**Keep the current behavior and document the one-level recursion limitation.**
Rejected: recursive Installation-context access is an existing product promise, and the context resolver already accepts
Presentation-Installation ids.

## Related

- [Introduce Presentation-Installation to close recursive Installation-context access](../architecture/2026-09-01-introduce-presentation-installation-for-recursive-installation-context.md)
