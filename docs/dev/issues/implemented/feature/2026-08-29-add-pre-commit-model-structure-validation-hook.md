# Issue Note: Add a pre-commit model-structure validation hook

Status: implemented

## Problem

`hook install` previously wrote only a `post-checkout` hook. Nothing gated `git commit` on
`validate --only-model-structure`, so a commit could enter history while the `.doctidex-git` work model was invalid or
uninitialized. The user discovered that state later through a manual validation.

## Decision

`hook install` now writes both a `post-checkout` hook and a `pre-commit` hook. The `pre-commit` hook delegates
commit-time work to a `hook pre-commit` worker.

### Installed hooks

`hook install` writes:

- `post-checkout`, which keeps untracked runtime state branch-consistent;
- `pre-commit`, which invokes `hook pre-commit` before commits.

Both scripts use the resolved `doctidex-git` command path and the existing atomic-write and executable-bit handling.
Successful first-time `init` installs both because it already calls `hook install`.

### Pre-commit worker

The installed `pre-commit` script is:

```sh
#!/bin/sh
exec /resolved/path/to/doctidex-git hook pre-commit "$@"
```

`hook pre-commit` returns success when `.doctidex-git` is absent. When the workspace exists, it runs
`validate --only-model-structure`. A valid model passes; an invalid model fails with
`hook.pre-commit.validation.failed` and carries the validation diagnostics in the failure details, which aborts the
commit.

### Workspace gate

The worker tests the `.doctidex-git` directory, not the tracked `config.toml`. A repository without that directory
is outside doctidex management and commits proceed. A partial or inconsistent workspace is validated rather than
silently skipped.

## Verification

The full test suite passes. Coverage is 87%. `ruff check src/python/whero/doctidex src/python/tests` passes and
`git diff --check` passes. Tests cover hook installation, idempotency, executable bits, worker pass/fail behavior,
the uninitialized-repository skip, and the real `git commit` gate.

## Consequences

Commits now fail when the work-model structure is invalid. That is the intended gate, but it adds a new failure point
to `git commit`. The hook uses only `validate --only-model-structure`, so the gate remains scoped to work-model state and
does not make commits depend on Markdown link scanning or managed physical-object checks.

## Related

- [Write Git hook scripts in a tool-compatible way](../simplification/2026-08-29-write-git-hook-scripts-in-a-tool-compatible-way.md)
- [Support Git branch switching with post-checkout runtime snapshots](2026-08-28-support-git-branch-switching-with-post-checkout-runtime-snapshots.md)

## Alternatives considered

**Invoke `validate --only-model-structure` directly from the `pre-commit` shell script.**
Rejected: it hardcodes the current validation step into the shell surface and makes the hook equivalent to the
`validate` command. A `hook pre-commit` worker keeps the commit-time seam in Python, where future pre-commit work can
be added without changing the installed script.

**Run full `validate` instead of `validate --only-model-structure`.**
Rejected: full validation also scans Markdown content and managed physical objects, which makes the commit gate
slower and ties commits to link and content concerns outside work-model structure.

**Introduce a separate pre-commit framework or external hook manager.**
Rejected: `hook install` already owns supported Git hooks for the repository, so a second installation path would
split that source of truth.

**Leave validation manual only.**
Rejected: it does not prevent invalid work-model state from entering commit history.
