# Issue Note: Distinguish managed Worktrees from Installation context

Status: implemented

## Problem

[installation.py](../../../../../src/python/whero/doctidex/installation.py) detected Installation context by walking ancestor paths named `.doctidex-git`. A managed Worktree created under the default `/.doctidex-git/worktrees/` tree is itself a Git worktree, so `resolve_git_root` selected that Worktree as the command root and the ancestor scan then found the owner's `.doctidex-git`. The command was misclassified as running inside an Installation, and the Installation-context admission rules either rejected Worktree commands or ran read-only commands against a nonexistent local work model.

That contradicted the Worktree semantics in [overview.md](../../../architecture/overview.md#worktree): a Worktree is an editable, untracked development space based on a recorded base commit. It may receive modifications, branches, and commits while the base commit remains in history. A Worktree is not the read-only fixed-revision surface an Installation is.

Installation read-only behavior was also under-specified in validation. `validate` confirmed only that `HEAD` and `origin` matched the recorded Installation; it did not report uncommitted changes, so a dirty Installation could pass validation even though Installation is read-only. Repair discarded dirty changes when it recreated a non-clean Installation, but that behavior was not an explicit contract.

The user and architecture documents described an Installation as a fixed-revision object and a Worktree as an editable worktree, but they did not state the operational boundary: Installation directories are read-only, while a Worktree is free to branch, modify, and commit from its base commit. `worktree create --work-path` also could accept a recorded Installation path when that physical path was absent, which would turn an Installation path into a Worktree.

## Decision

Managed Worktrees and Installations are now separate path roles.

### Worktree context

`installation_path_preflight` keeps the ancestor scan and multiple-owner ambiguity check. For one owner, it opens a read-only diagnostic transaction over the owner RuntimeState. If the selected Git root matches a recorded `Worktree.work_path`, it returns ordinary context. The Worktree record, not the default `/.doctidex-git/worktrees/` spelling, is the authority for the exclusion. The earlier `resolve_installation_context` path-to-`install-id` behavior is superseded by [Select Installation context by install-id argument](../architecture/2026-08-27-select-installation-context-by-install-id.md).

If the owner work model cannot be read, the command fails before mutation with a structured `work-model.invalid` error that includes the owner path. A pending RuntimeStore transaction fails with a structured store error before the command mutates.

After the exclusion, command dispatch follows the ordinary repository-root path. `init` is available in the Worktree; other work-model commands behave as they do in any uninitialized Git repository until that Worktree is initialized.

### Installation read-only state

`validate` keeps the current `HEAD` and `origin` checks and adds a dirty-state check for each existing physical Installation using `git status --porcelain --untracked-files=all`. A non-empty result produces an `installation.worktree.dirty` violation inside `work-model.valid` with the `install-id` and `install-path`. A dirty Installation does not pass validation.

`repair` at the owner root aligns an existing physical Installation to its recorded commit. It discards tracked modifications and untracked files under the Installation path and leaves `HEAD` and the working tree at the recorded commit. `repair` does not discard dirty Worktree changes, and `worktree remove` still requires `--force` for a dirty Worktree. `repair` remains forbidden inside Installation context.

### Installation path protection

`worktree create --work-path` now rejects paths inside `/.doctidex-git/imports/` and paths below an existing BoundaryPoint, including when the physical path is absent. The earlier exact-recorded-`install-path` rule is partially superseded by [Reserve `/.doctidex-git/imports` for managed Installations](2026-08-25-reserve-doctidex-git-imports-directory.md). `worktree create --install-id <INSTALL-ID>` remains valid and creates an independent Worktree directory under `/.doctidex-git/worktrees/`.

### Documentation

The [user overview](../../../../user/overview.md) and reference pages state that Installation directories are read-only and that Worktrees may branch, modify, and commit from their base commit. The Installation and Worktree concepts in [overview.md](../../../architecture/overview.md) state the same constraint as architecture authority.

## Testing

The full suite passes with 76 tests. `ruff check` passes, `git diff --check` passes, and coverage is 85%. Relative documentation links resolve. Tests cover default and custom Worktree context, invalid and pending owner models, Installation-path rejection, dirty Installation validation, and dirty Installation repair.

## Alternatives considered

**Exclude only the default `/.doctidex-git/worktrees/` prefix.**
Rejected: path spelling is not the semantic boundary. A custom Worktree path could sit under `.doctidex-git`, and a recorded Worktree should be recognized as a Worktree wherever it lives. The owner work model already records `work-path`, so consulting it is the durable rule.

**Keep Worktree paths in Installation context and add Worktree-specific exceptions.**
Rejected: it would preserve the wrong context and widen the Installation-context admission table with Worktree rules. A Worktree is an editable development space, not a read-only Installation, so its commands should be admitted through the ordinary repository path.

**Leave dirty Installation detection to repair only.**
Rejected: validation is the read-only check that should expose the violation before repair discards changes. Repair then provides the mutating correction.

**Preserve untracked files during Installation repair.**
Rejected: the Installation read-only contract requires the working tree to match the recorded commit; leaving untracked files would still make it dirty. All dirty changes, tracked and untracked, are discarded.

**Leave the Installation read-only and Worktree editable rules implicit.**
Rejected: command admission alone does not communicate to users that Installation directories must not be edited. The user guide and architecture concepts must state the boundary so misuse is discoverable before an edit or `repair`.

**Allow `worktree create --work-path` to reuse an Installation path for convenience.**
Rejected: it would give one path two incompatible roles, allow a read-only Installation to become editable, and erase the distinction this issue restores.

## Consequences

The change makes Worktree paths behave like ordinary repository paths and makes Installation read-only behavior explicit and validated. Users can no longer mistake a default Worktree for an Installation context or reuse an Installation path as a Worktree.

The cost is that context detection now reads the owner work model during preflight. A corrupt or pending owner model can fail a Worktree command earlier than before, and repair now explicitly discards uncommitted Installation changes. Both effects are scoped and non-mutating for the failure case; the discard is the documented repair contract for the read-only Installation.
