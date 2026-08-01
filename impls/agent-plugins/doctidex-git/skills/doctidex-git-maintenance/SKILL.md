---
name: doctidex-git-maintenance
description: Validate and maintain doctidex content with optional installed doctidex-git external presentations and isolated worktrees. Use when checking full or directory-scoped protocol structure, installing/linking/restoring external Git content, expanding a dependency discovered in an installed repository, or opening/listing/closing a managed writable worktree; do not require managed workflows when native tools suffice and do not perform Git delivery without user authority.
---

# Maintain doctidex Content

If `$doctidex-git-overview` has not already been read for this task, read it once and return here.

First choose the working method. For maintenance of the current host working tree at its current
commit, use that path and native Git directly unless isolation is useful. A separate managed
worktree remains optional. External install/link/restore is also optional; a user or agent may use
native Git, manual worktrees, submodules, symlinks, or another method instead.

Read exactly one command reference before invoking its workflow:

- Read [validation.md](references/validation.md) for full or directory-scoped protocol validation.
- Read [external.md](references/external.md) before install, durable link, restore, dependency
  expansion, or promotion from dependency to direct.
- Read [worktrees.md](references/worktrees.md) before opening, listing, or closing an isolated
  writable worktree.

When entering from `$doctidex-git-read` with a complete `link-parse` result, do not reopen Read or
Overview. Use the exact source, commit, owner root, and parent install fields already returned. When
starting here and an inaccessible symlink must first be interpreted, load Read once, collect the
facts, then return here without causing Read to reload Maintenance.

## Preserve Layer Boundaries

Use validation for observable doctidex protocol structure only. Do not turn a managed-state issue,
Git tracking fact, content trust concern, or semantic writing judgment into a protocol failure.
Validation is deterministic; the agent still judges semantic candidates and authors index/log
prose.

Treat installs as logical read-only snapshots at fixed commits. Never edit an install in place. A
dependency discovered from installed content is created flat in the outer owner root, using
`--dependency-of`; never recurse under the installed repository. Self-reference also gets an
independent snapshot. Different selectors have different install paths even if they resolve to the
same commit.

For edits, work only in an authorized writable working tree. Inspect native Git status/diff before
and after changes. The CLI never chooses a delivery branch or runs add/commit/push/merge/reset.
Preserve unrelated changes and ask the user when `requires_user` identifies a permission, tracking,
revision, target, parent, recovery, or delivery decision.

## Finish the Task

After editing, run validation at the coverage appropriate to the claim. Read every protocol finding
and semantic candidate; a scoped pass is not a full-root pass. Use native Git to inspect and deliver
changes only within granted authority. Close a managed worktree only after it is objectively clean;
changed or unavailable worktrees are deliberately preserved.
