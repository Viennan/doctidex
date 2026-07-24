---
name: doctidex-git-mount
description: Manage Git-backed doctidex mounts declared by a root index.md. Use to list, add, remove, lazily prepare, or explicitly synchronize complete external doctidex directory trees at /.doctidex/mounts paths.
---

# Doctidex Git Mount

## Prepare the CLI

Install `whero-doctidex` before using the CLI. In this repository run
`.venv/bin/python -m pip install -e impls/libs/python`; otherwise install the distribution in the
active Python environment. Ask the user when installation needs unavailable access.

## Manage Declarations

Always operate from one explicit doctidex root. Use `doctidex-git mount list --json` first.

Add a complete Git source tree with exactly one revision selector:

```bash
doctidex-git mount add --url URL --branch main \
  --mount-path /.doctidex/mounts/design --dry-run --json
doctidex-git mount add --url URL --branch main \
  --mount-path /.doctidex/mounts/design --apply --json
```

Commit and tag selectors use `--commit` and `--tag`. Never invent `src_path`; the URL checkout root
must be the complete doctidex source tree. Adding a declaration is offline and leaves it
`not_prepared`.

Before removal, run the dry-run. Update reported references first. Do not delete unrelated files or
tracked content to force the operation.

## Restore and Synchronize

Use `mount prepare [MOUNT_PATH]` only when content must become readable. It preserves the declared
selector and reuses the effective commit when one exists.

Use synchronization only for an explicit request to update:

```bash
doctidex-git mount sync MOUNT_PATH --dry-run --json
doctidex-git mount sync MOUNT_PATH --apply --json
```

Explain the old and new commits before applying. A failed sync must leave the old effective commit
readable. Never edit files through a host mount path; use the workspace skill for source changes.

When blocked, follow the returned user-level actions. Ask the user for credentials, revision
choice, tracked-content decisions, or destructive Git authorization; do not expose internal clone,
worktree, lock, or projection details.
