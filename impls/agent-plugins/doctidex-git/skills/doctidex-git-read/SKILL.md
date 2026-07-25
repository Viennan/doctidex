---
name: doctidex-git-read
description: Navigate and investigate doctidex directory trees in Git repositories while retaining unrestricted use of native file, search, and shell tools. Use for locating knowledge, resolving doctidex links, understanding index or log scope, or restoring a required lazy Git mount whose path is absent.
---

# Doctidex Git Read

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Responsible index**: the nearest `index.md` responsible for an included local path; use it as a
  recommended local map.
- **Applicable log**: the nearest optional `log.md` for change background.
- **Link root**: the doctidex root used by a `/`-prefixed link; it is not the filesystem root.
- **Working path**: the filesystem location used by native tools; it can often be inferred directly
  and is also returned by `resolve`.
- **Normalized internal path**: a `/`-prefixed doctidex path with no unresolved `.` or `..`
  segments.
- **Lazy mount**: a declared external source whose state is `not_prepared` until required.
- **Ready mount**: a mount whose current effective commit is readable at its logical path.

Excluded and protected files may still be read for repository context. Atomic entries are indexed
as a whole but their files remain directly readable. These terms constrain maintenance, not native
reading.

## Command Contract

### Select a root

```bash
doctidex-git context PATH --json
```

Use a filesystem PATH. `root: null` means no doctidex root contains it; continue ordinary file
exploration unless the task asks to initialize one.

### Inspect a filesystem path

```bash
doctidex-git inspect PATH --json
```

PATH may be a file or directory inside the selected root. Read `path_context` for host scope,
attributes, responsible index, applicable log, and mount membership. `links` are machine-parsed
links from the responsible index; `semantic_candidates` require judgment. Inspect does not prepare
mounts or access a remote.

### Resolve a doctidex path

```bash
doctidex-git resolve INTERNAL_PATH --json
```

Run from the intended host root. `INTERNAL_PATH` must begin with `/`; pass
`/.doctidex/mounts/...` for external trees. Read `internal_path`, `working_path`, `crosses_mount`,
and `mount`. Resolve never reads the target file or prepares a mount.

Treat `resolve` as a disambiguation and mount-state helper, not a required step before file access.
When the link root and normalized internal path are already known, derive the working path by
appending the internal path without its leading `/` to the filesystem link root:

```text
link root:     /work/docs
internal path: /guides/setup.md
working path:  /work/docs/guides/setup.md

host root:     /work/docs
internal path: /.doctidex/mounts/design/api.md
working path:  /work/docs/.doctidex/mounts/design/api.md
```

Likewise, resolve a simple relative Markdown link from the containing document's directory using
normal filesystem path rules. Use native tools directly when the input is already a filesystem
path. After establishing one root or ready mount mapping, reuse it for sibling and descendant paths
until the selected root or mount state changes; do not call `resolve` for every file.

Prefer `resolve` when any of these applies:

- the path contains nontrivial `.` or `..` normalization;
- traversal has crossed mounted content and `.doctidex/mounts` appears again, invoking the
  non-nesting namespace rule;
- it is unclear whether the path crosses a declared mount;
- mount state, effective commit, readable status, or the exact prepare action is needed;
- a directly inferred must-read path is absent and the absence must be distinguished from a lazy
  mount.

Establish the intended root before calling `resolve`. Do not use it for relative links, external
URLs, anchors, target-existence checks, or reading file content.

### Check declared mounts

```bash
doctidex-git mount list --json
```

This command has no root argument; run it from the selected host root. It is offline and does not
check whether a branch or tag is current remotely.

## Read Freely

Use native file readers, directory tools, search, shell, and Git commands. Start with a responsible
index when it helps narrow the task; read an applicable log when change history matters; expand to
global search whenever indexes are insufficient. No CLI call is required before ordinary access.

Resolve relative links from the containing document directory. Resolve `/`-prefixed paths from the
document's link root. The mount namespace does not nest: a later `.doctidex/mounts` inside mounted
content refers back to the host root where traversal began. This exceptional case is a recommended
use of `resolve`; ordinary normalized local paths can be inferred as described above.

## Restore a Required Mount

When a native tool cannot find a path the task must read:

1. Reuse already known mount state. If it is unknown, resolve the internal path once or list mounts.
2. If mount `state` is `not_prepared`, load `$doctidex-git-mount` and prepare that exact
   `MOUNT_PATH`; do not prepare every mount by default.
3. Retry the original native tool using the returned or directly inferred working path.
4. If mount state is `ready` and the file is still absent, investigate it as a real source-path or
   revision issue.
5. If preparation needs network, credentials, source URL, or revision choice, ask the user using
   the returned action.

Ordinary reading and prepare do not synchronize a branch or tag. Only explicit mount sync can
change the effective commit.

## Result

Report the selected root, paths actually read, responsible index/log used, effective commit for
mounted evidence, and unresolved user action. Do not describe a `semantic_candidate` as a missing
index entry until the existing prose has been read.
