# Issue Note: Make Installation restore state visible and distinguishable

Status: implemented

## Problem

Installation records previously did not expose whether their physical worktree was present. `import query`
returned `install-id`, `install-path`, commit metadata, keys, and refs without an availability field. In
Installation context, `presentation-path` indicated owner-side mapping, not whether the selected Installation
itself was physically present.

The user documents described `import restore` and the expected missing tracked physical directory after clone,
but the guidance was spread across `import.md` and `validate.md`. A tracked Installation whose physical directory
was absent could produce `work-model.invalid` through `validate` or `installation.context.unavailable` through
Installation-context commands. Both made “not restored yet” look like corrupt or malformed model state.

## Decision

Restore state is a derived Installation availability condition.

### Query visibility

`import query` emits a `restore-state` field for every candidate:

- `available`: the recorded physical Installation path resolves to a usable worktree or selector symlink;
- `restore-required`: the Installation is tracked and its physical path is absent;
- `missing`: the Installation is untracked and its physical path is absent.

In Installation-context query results, a candidate with `presentation-path` is `available`; otherwise restore
state falls back to the ordinary `git-root` plus `install-path` check.

### Context resolution

`resolve_installation_context_by_id` keeps identity-based lookup and enforces availability after resolving the
record:

- tracked and absent: `installation.restore.required`;
- untracked and absent: `installation.context.unavailable` with `reason: installation-missing`;
- available: `InstallationContext`.

`installation.restore.required` details name the `install-id`, `install-path`, tracking state, and the correction
command `import restore --install-id <INSTALL-ID>`.

### Error separation

Expected physical absence is no longer represented as `ModelFormatError`. `InstallationRuntimeStore` keeps
`installation.context.unavailable` for an available Installation whose local declarations are missing or
malformed. Genuine malformed persisted documents continue through the existing `work-model.invalid` or validation
diagnostic paths.

Installation context is meaningful only when the selected Installation itself is a doctidex-git-managed
repository with a local `.doctidex-git` work model.

## Testing

The full suite reports 112 passing tests. Coverage is 87%. `ruff check` and `git diff --check` pass. Tests cover
available, restore-required, and missing query states, context enforcement for tracked and untracked missing
Installations, malformed local workspaces, missing local workspaces, and Installation-context restore-state
before and after `import restore`.

## Consequences

The change makes restore state machine-visible and gives automation a distinct error for the expected “restore
first” step. `import query` now tells users whether a tracked Installation has only metadata or a usable physical
worktree, and `--installation-context` fails clearly for a not-restored tracked Installation before any command
can misreport it as corrupt.

The cost is one new query field and one new error code. Clients that previously inspected
`installation.context.unavailable` or `work-model.invalid` for missing physical Installations must now treat
`restore-state: restore-required` and `installation.restore.required` as the expected recovery state.

## Alternatives considered

**Document the current behavior without changing code or errors.**
Rejected: documentation cannot give automation a distinct error code or make query results machine-visible. The
same symptom would still be misread as malformed state.

**Reuse `installation.context.unavailable` with a `reason: restore-required`.**
Rejected: that code already means several different conditions, including unavailable commands and unreadable local
declarations. Reusing it preserves the ambiguity this issue removes.

**Add only an availability field to `import query`.**
Rejected: query would tell the user the state, but command entry and error paths would still report the state as
`ModelFormatError` or a generic context error.

**Report the missing local workspace as `work-model.invalid`.**
Rejected: that conflates an expected restore step with corrupt model data. A missing physical Installation is
recoverable by `import restore`, not by editing or repairing a state file.

**Check availability only when an Installation is selected by `--installation-context`.**
Rejected: it improves context errors but leaves ordinary `import query` without visibility. Users inspecting
Installations need the same restore state before choosing an action.
