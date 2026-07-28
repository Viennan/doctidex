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
- **Link document**: the existing accessible file containing a link. Its location can establish
  the link root without changing the current working directory.
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
doctidex-git resolve INTERNAL_PATH [--from LINK_DOCUMENT] --json
```

`INTERNAL_PATH` is the `/`-prefixed path portion of the link, without an anchor. With no `--from`,
run from the intended exact link root. Use `--from` when the accessible file containing the link is
in a different doctidex tree from the current command context, especially when its filesystem path
begins with the host's `.doctidex/mounts/` path. `LINK_DOCUMENT` may be absolute or relative to the
current directory, must name an existing file, and is used only to select link semantics; resolve
does not verify that the document contains `INTERNAL_PATH`.

For a document in prepared mounted content, `--from` interprets an ordinary `/guide.md` from that
mounted source root. A `/.doctidex/mounts/...` link in the same document resets to the original host
mount namespace. This lets an agent remain in the host repository while resolving source links:

```bash
doctidex-git resolve /guide.md \
  --from .doctidex/mounts/design/index.md --json
```

Read `root` as the selected command/host context, `link_root` and `link_root_kind` as the base used
for this link, and `working_path` as the path for native file tools. `crosses_mount` and `mount`
report the relevant host mount and readable state. Resolve never reads the target file, prepares a
mount, or accesses a remote.

When resolution involves a mount, also read `root_relation` and `maintenance_reuse` if later work
may modify what you read. A confirmed self-reference still returns a read-only path below the
host's `.doctidex/mounts/`, whether `revision` is `same_commit` or `different_commit`; never replace
that reading path with the current writable root. If modification is required, load
`$doctidex-git-workspace`: `same_commit` normally lets compatible changes reuse the host root,
while `different_commit` requires a separate source scope. When `root_relation.source` is
`unknown`, do not guess from matching content or commit text.

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

mounted source root: /work/docs/.doctidex/mounts/design
source internal path: /guides/setup.md
working path:         /work/docs/.doctidex/mounts/design/guides/setup.md
```

Likewise, resolve a simple relative Markdown link from the containing document's directory using
normal filesystem path rules. Use native tools directly when the input is already a filesystem
path. After establishing one root or ready mount mapping, reuse it for sibling and descendant paths
until the selected root or mount state changes; do not call `resolve` for every file.

The accessible source root of a known mount is the host filesystem path corresponding to its exact
`MOUNT_PATH`, such as `/work/docs/.doctidex/mounts/design`. Once that mapping is known, ordinary
normalized `/...` links from documents in that source can be appended there directly. Use
`--from` when the origin or namespace-reset semantics are uncertain, not merely because a path is
mounted.

Prefer `resolve` when any of these applies:

- the path contains nontrivial `.` or `..` normalization;
- traversal has crossed mounted content and `.doctidex/mounts` appears again, invoking the
  non-nesting namespace rule;
- it is unclear whether the path crosses a declared mount;
- mount state, effective commit, readable status, or the exact prepare action is needed;
- a directly inferred must-read path is absent and the absence must be distinguished from a lazy
  mount.

For a local document in the already selected root, an ordinary normalized `/...` path can usually
be inferred without resolve. For a mounted document reached from the host, prefer `--from` over
changing directories merely for one resolution. If a sustained investigation stays within one
unambiguous root, changing to that exact root makes no-`--from` calls and other defaulted commands
more concise. A document inside nested ordinary roots remains `root_ambiguous` until the current
directory selects the exact owning root.

Do not use resolve for relative links, external URLs, anchors, target-existence checks, or reading
file content.

If `link_source_invalid`, correct `LINK_DOCUMENT` to the existing file that supplied the link; if
that file is absent because its mount is lazy, prepare the exact mount before retrying. If
`root_ambiguous`, change to the exact root that owns the document and retry, or ask the user when
ownership is unclear. For `internal_path_not_absolute` or `internal_path_escape`, correct the path
itself; changing `--from` cannot make a relative or escaping internal path valid.

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
document's link root. The mount namespace does not nest: a later `/.doctidex/mounts` link inside
mounted content refers back to the host root where traversal began. Pass the mounted document with
`--from` for this exceptional case; ordinary normalized local paths can be inferred as described
above.

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
