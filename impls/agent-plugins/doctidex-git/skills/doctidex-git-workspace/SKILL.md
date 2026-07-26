---
name: doctidex-git-workspace
description: Open isolated writable roots for mounted Git sources and coordinate tasks spanning multiple doctidex roots. Use when a host mount must be changed, the host repository is itself mounted, or one task requires separate source and host results.
---

# Doctidex Git Workspace

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Independent root**: a host or source root with its own base commit, write boundary, diff,
  validation, and Git delivery actions.
- **Base commit**: the commit from which a maintenance result started; it can be null before a mount
  is prepared.
- **Read-only path**: the host mount path used for reading the current effective commit.
- **Maintenance root**: the filesystem path returned by `maintenance open`; this is where source
  edits belong.
- **Target branch**: an informational branch name when the mount selector is a branch. It does not
  mean the maintenance root has switched to that branch.
- **Handoff**: a read-only summary of changes, validation, semantic candidates, and remaining Git
  decisions for one maintenance root.

`maintenance scope` and `maintenance open` select their host root from the current working
directory. Run them from the exact host root; a `PATH` passed to `scope` classifies work but does
not select a different host. After `open`, pass the returned exact `MAINTENANCE_ROOT` to
`status`, `handoff`, and `close`; those explicit calls work from another current directory. When
the path is omitted, these commands again select the host from the current directory.

## Command Contract

| Command | Parameter behavior | Result or limit |
|---|---|---|
| `doctidex-git maintenance scope [PATH ...] --json` | PATH values are filesystem targets in the current host. Omit them to scope the host root. | Deduplicates the host and each mount into `items`; does not open writable roots. |
| `doctidex-git maintenance open MOUNT_PATH --json` | Pass the exact declared mount path, not a file below it. Mount must already have an effective commit. | Returns one `maintenance_root`, `writable_root`, base commit, boundaries, and next actions. |
| `doctidex-git maintenance status [MAINTENANCE_ROOT] --json` | Omit the path to list all open contexts for the current host; pass an exact returned path to select its owning host and filter one. | No match within a selected host returns an empty list, not an error. `changes` are Git status entries, not a diff. |
| `doctidex-git maintenance handoff [MAINTENANCE_ROOT] --json` | Pass the exact returned path from any cwd. Omit only from its host when exactly one context is open. | Returns one root's changes and three validation domains; does not commit or push. |
| `doctidex-git maintenance close [MAINTENANCE_ROOT] --json` | Use the same exact-selection rule as handoff. No dry-run flag. | Removes only a Git-clean context; any change blocks close and preserves the root. |

If open reports `maintenance_source_not_prepared`, load `$doctidex-git-mount`, prepare that exact
mount, and retry. Open itself does not fetch or synchronize.

## Multi-Root Workflow

1. Run scope for all task paths. Treat every item as an independent result.
2. Decide task order from real content dependencies; the CLI does not choose the order.
3. Keep `host_root` work in its returned `write_path`.
4. For each `mounted_source`, ensure `base_commit` is non-null and open its exact `mount_path`.
5. Work only under each returned `maintenance_root`, starting from that source's own `index.md`.
   Never modify the host `read_only_path`.
   For substantial, multi-step work on that one source, `cd` to its maintenance root so native
   tools and commands with optional paths naturally use the intended root. Keep passing the exact
   root in multi-root orchestration when that makes scope clearer.
6. Load `$doctidex-git-maintain` and `$doctidex-git-validate` as needed for each root.
7. Run handoff with the exact maintenance path and inspect the native Git diff.
8. Report each root's base commit, changes, validation, target branch hint, and required
   commit/push/merge/selector action separately.
9. Close only after Git status is clean or the user has explicitly disposed of the result.

## Failures and Partial Results

A multi-root task is not atomic. Preserve and report successful roots when another root fails.
`maintenance_has_changes` is a preservation result, not a cleanup error: keep the path open and ask
the user how to deliver or dispose of changes. Obtain explicit authorization before commit, push,
merge, selector update, reset, or deletion.
