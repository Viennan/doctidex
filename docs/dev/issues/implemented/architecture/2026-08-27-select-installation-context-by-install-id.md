# Issue Note: Select Installation context by install-id argument

Status: implemented

## Problem

[installation.py](../../../../../src/python/whero/doctidex/installation.py) previously derived
`InstallationContext` from the selected Git root's physical path. `resolve_installation_context` walked
ancestors to a `.doctidex-git` owner, excluded recorded Worktrees, and then asked
`_installation_path_for_root` to find a recorded Installation whose `install-path` was exactly the selected
root.

That path identity is not stable under [Shared commit-hash Installation storage](2026-08-26-shared-commit-hash-installation-storage.md).
Branch and tag Installations are selector-derived symlinks to a shared worktree, while direct-commit
Installations use the shared worktree path. A user or agent running the CLI inside an installed repository
may select the real shared path or a selector path. The real path can match several Installations, and a
selector path can match none after branch or tag re-resolution. Context detection was therefore ambiguous or
missing before the CLI reached the stable `install-id`.

The path-based rule also entangled root selection with context selection. Physical path was being used as an
identity when the work model already has a durable `install-id`, and the matching code could not be made exact
under the shared-storage model.

## Decision

The CLI now separates owner-root selection from Installation selection.

### CLI contract

`--installation-context <INSTALL-ID>` is an optional top-level argument at the same level as `--repos-path`.
It selects an Installation already recorded in the owner `RuntimeState`. `--repos-path` remains the owner Git
root selector.

```text
doctidex-git [--repos-path <OWNER-ROOT>] [--installation-context <INSTALL-ID>] <command> [options]
```

When `--repos-path` is omitted and `--installation-context` is present, the CLI requires exactly one ancestor
`.doctidex-git` owner candidate. Zero candidates fail with `installation.context.owner-required`; multiple
candidates fail with `installation.owner.ambiguous`.

### Installation-context resolution

`resolve_installation_context_by_id` opens the owner `RuntimeState` in a diagnostic read transaction and
constructs `InstallationContext` from the owner root and the recorded `install-path`. An unknown `install-id`
fails with `installation.not-found`.

`installation_path_preflight` is the only path-based check. It keeps the Worktree exclusion, returns ordinary
context when no owner exists, and fails with `installation.context.argument-required` when a non-Worktree path
appears to be inside a managed Installation.

The old `_installation_path_for_root` path-to-`install-id` matching is removed. A branch or tag symlink or a
shared real worktree path no longer participates in Installation identity selection.

### Command routing

When an `InstallationContext` is active, the effective command root is the selected Installation's physical
path:

```text
command_root = repo_path_to_fs(owner_root, context.install_path)
```

`validate`, `boundary-set parse`, `import query`, and `import restore` use the Installation-local model.
`import restore` keeps its specialized owner-side flattening path. Commands that mutate the owner work model,
create Worktrees, initialize a workspace, or repair are forbidden with `installation.context.forbidden`.

The read-only Installation adapter and identity-based `presentation-path` mapping continue from
[Make Installation-context transactions read-only](../simplification/2026-08-27-make-installation-context-transactions-read-only.md).

### Related decisions

Worktree exclusion remains the responsibility of
[Distinguish managed Worktrees from Installation context](../bug-fix/2026-08-24-distinguish-managed-worktrees-from-installation-context.md),
now performed through `installation_path_preflight`.

## Testing

The full suite reports 107 passing tests. Coverage is 86%. `ruff check` and `git diff --check` pass. Tests cover
top-level argument parsing, explicit context for `validate`, `boundary-set parse`, `import query`, and
`import restore`, shared branch/tag/commit paths, unknown install-ids, owner-root discovery from the current
directory, zero and multiple owner candidates, Worktree exclusion, and the path-only guard.

## Consequences

The change removes physical-path ambiguity for branch, tag, and direct-commit Installations that share a worktree.
Installation-context commands now require a stable `install-id`, which matches the existing import and worktree
selector vocabulary.

The cost is an explicit top-level argument and a new path-guard error. Users and agents that invoke read-only
commands directly inside an Installation must pass `--installation-context <INSTALL-ID>`; the guard explains this
before any mutation. `--installation-context` with `--repos-path` omitted also depends on a single owner ancestor,
so zero or multiple owner candidates fail earlier and more clearly than the old path matching.

## Alternatives considered

**Keep path detection and make the ambiguous physical-path match deterministic.**
Rejected: physical path is not the stable identity. A shared worktree can correspond to several Installations,
and a selector symlink can change or disappear. Any rule that disambiguates by path spelling still leaves an
identity-shaped problem represented by a non-identity value.

**Add an `--installation-path` argument instead of an `install-id`.**
Rejected: branch and tag paths are selector-derived and can change during re-resolution. `install-id` is
already the durable, user-visible selector used by the import and worktree commands, so it is the natural
context handle.

**Reject path-detected Installations but do not add a context argument.**
Rejected: that would make Installation-context commands unreachable from an installed path. The user would
need to know the owner root and an indirect command shape, while the model already has an unambiguous id.

**Allow `--repos-path` to accept either an owner root or an Installation id.**
Rejected: it conflates Git-root selection with Installation selection and makes argument errors and root
discovery harder to reason about.

**Drop path detection entirely.**
Rejected: path detection remains valuable as a guard. Without it, a command started inside an Installation
would silently fall through to ordinary repository behavior instead of telling the user to select the
Installation explicitly.
