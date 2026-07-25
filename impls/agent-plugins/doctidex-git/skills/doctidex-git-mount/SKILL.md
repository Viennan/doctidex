---
name: doctidex-git-mount
description: Manage Git-backed doctidex mounts declared by a root index.md. Use to list, add, remove, lazily prepare, or explicitly synchronize complete external doctidex directory trees at /.doctidex/mounts paths.
---

# Doctidex Git Mount

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Mount declaration**: a root-index entry containing Git source URL, exactly one revision
  selector, and a logical mount path.
- **Revision selector**: one of commit, tag, or branch. Commit is fixed; branch/tag can resolve to a
  different commit only when explicitly checked or synchronized.
- **Effective commit**: the exact source snapshot currently selected for reading.
- **`not_prepared`**: declaration is valid but no readable presentation is required yet.
- **`ready`**: the effective commit is readable through the host mount path.
- **Host mount path**: a read-only logical path. Use `$doctidex-git-workspace` to change its source.

All mount commands select the host root from the current working directory; they do not accept a
root option. Run from the exact intended root when nested roots may exist.

## Command Contract

| Command | Required arguments and limits | Network/write behavior |
|---|---|---|
| `doctidex-git mount list --json` | No path argument. Lists only `type: git` declarations in the selected root. | Offline, read-only; does not refresh branch/tag. |
| `doctidex-git mount add --url URL (--commit SHA | --tag TAG | --branch BRANCH) --mount-path MOUNT_PATH [--dry-run | --apply] --json` | Choose exactly one selector option. MOUNT_PATH must be a normalized strict child of `/.doctidex/mounts` and not overlap another mount. URL must identify a repository whose root is the complete doctidex source; no `src_path`. | Offline. Dry-run validates; apply changes root `index.md` and leaves `not_prepared`. |
| `doctidex-git mount remove MOUNT_PATH [--dry-run | --apply] --json` | Use the exact declared path. Parsed Markdown references block removal. | Offline. Apply changes root index and removes the managed readable path/state. |
| `doctidex-git mount prepare [MOUNT_PATH] --json` | Exact path is recommended. Omitting it prepares all Git mounts and returns a batch result unless exactly one exists. No dry-run flag. | May need network/credentials. Makes the current effective commit readable; does not change the declaration. |
| `doctidex-git mount sync [MOUNT_PATH] [--dry-run | --apply] --json` | Exact path is recommended. Omitting it processes all mounts independently. | Dry-run may fetch and returns old/new commit without switching. Apply switches only when different. |

Do not pass a filesystem path where MOUNT_PATH is required. Do not append a source file path to
`mount prepare`, `remove`, or `sync`; pass the declaration root such as
`/.doctidex/mounts/design`.

## Add or Remove

1. List mounts and confirm the selected host root.
2. For add, choose selector semantics deliberately: use commit for an immutable snapshot, branch
   or tag only when explicit future sync is desired.
3. Run the exact dry-run command. Confirm `source`, `declared_revision`, `mount_path`,
   `network: false`, and no overlapping/tracked path finding.
4. Obtain write authorization, run apply, and confirm `mount_state: not_prepared`.
5. Prepare only if the current task must read the source.

For remove, dry-run first. If `mount_still_referenced`, update the reported documents and retry;
do not delete unrelated or tracked content to force removal.

## Prepare or Synchronize

Prepare preserves the declared selector and reuses an existing effective commit when available.
After success, require `mount_state: ready`, `readable: true`, and a non-null `effective_commit`,
then return to native file tools.

Use sync only for an explicit update request:

```bash
doctidex-git mount sync /.doctidex/mounts/design --dry-run --json
doctidex-git mount sync /.doctidex/mounts/design --apply --json
```

In sync output, `changed` is a boolean comparing old/new commits, not a file list. Explain both
commits before apply. If sync fails, report the preserved `result`, effective commit still selected,
affected mount, and returned recovery action.

## Batch and Failures

An omitted path can produce `items`, `completed_count`, and `total_count`. Treat each item
independently: top-level `blocked` does not undo successful items. Check `collection` before assuming
the item list is complete.

Ask the user for credentials, network access, revision/source choice, tracked-content handling, or
destructive Git authorization when requested. Never edit through the host mount path or implicitly
commit, push, reset, or clean.
