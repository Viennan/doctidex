# Manage External Git Content

All external write commands default to dry-run and accept `--dry-run | --apply`. Review dry-run,
then add `--apply` only with appropriate authority. Installs and restores may access their source;
link is offline. Payloads are ignored by host Git, while the recovery manifest and relative durable
links remain trackable. The CLI never stages or commits them.

## Install a Fixed Snapshot

```text
DOCTIDEX_GIT external install --url URL [--root ROOT]
  [--commit COMMIT | --tag TAG | --branch BRANCH]
  [--dependency-of INSTALL_ID]
  [--dry-run | --apply] --json
```

`URL` is a complete Git repository locator. Prefer the installed Git credential helper or another
non-command-line credential mechanism; avoid embedding secrets in URL because shell history and
process inspection are outside the CLI's sanitization boundary. If a supplied URL does contain
credentials, treat them as invocation-only and never repeat them in logs or prose. `ROOT` is the
exact owner root or defaults from cwd. Selector options are mutually exclusive: commit must be the
full repository object ID; tag/branch must be one valid ref name. Omission discovers the remote
default branch once, records its name as provenance, and fixes a commit selector. Repeating an
existing root/source/selector key reuses its recorded commit and path; it never follows a moved ref.

Without `--dependency-of`, create or promote a direct install and include it in portable recovery.
With it, the ID must be a complete install in the same owner root; create/reuse a flat dependency
install and a parent edge without adding independent recovery. Direct never downgrades. Repeating
the same source/selector without the parent promotes dependency to direct. A cycle or self-reference
hits the existing key and remains bounded; self-reference still uses an independent snapshot. A
dependency-only install's readable `install_path` is not a substitute for a direct source. To
establish document links to an external repository through a durable presentation, first repeat the
same source and selector without `--dependency-of` to promote it to direct. Keep the returned fixed
selector and commit rather than resolving a moving ref again.

## Handle Cycles and Self-Reference

Use explicit `--dependency-of` requests only for dependency edges the task actually requires. A
dependency is always a flat install in the outer owner root, never a nested checkout inside another
snapshot. If an explicit edge returns to an existing root/source/selector identity, the CLI reuses
that install and records the parent relation, so the cycle is bounded. This also supports a source
that is the owner or host repository itself: it remains an independent logical read-only snapshot,
not the current writable working tree.

The CLI does not discover or recursively install dependencies.

Read `applied`, `install_id`, `install_role`, bounded `dependency_of`, `manifest_included`,
`install_path`, `working_path`, sanitized `source_url`, `source_relation`, `revision_selector`,
`default_branch`, `resolved_commit`, `host_repository`, `payload_tracking`, `git_exclusion_file` and
state, `recovery_manifest` and state, `responsible_index`, `frontmatter_changes`, and
`planned_changes`. `network` reports actual access. Different selector kinds/values never share an
install path merely because their commits match.

Stop on invalid/inaccessible source, missing revision, invalid parent, tracked payload, ignore or
manifest conflict, damaged install, or partial success. Preserve every reported path. Resolve
credentials/network/revision/tracking/parent/target decisions before retrying.

## Create a Durable Relative Link

```text
DOCTIDEX_GIT external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] --json
```

`SOURCE_DIRECTORY` is a cwd-relative or absolute readable directory inside a complete direct
install or its existing link. `TARGET_PATH` is a nonempty normalized POSIX path relative to ROOT;
it cannot start with `/`, contain empty/`.`/`..` segments, overlap another presentation, or be
occupied/ignored. ROOT defaults from cwd but must own the source mapping. Prefer a presentation
near the content that actually uses it, and write document links to this root-relative path rather
than to `/.doctidex/git/installs/...`.

Apply creates a relative symlink to the stable install or its repository subdirectory, updates the
responsible index boundary/unsafe entries, and records portable mapping. It does not copy content,
replace a path, use an absolute symlink, or access the network. A dependency-only source must first
be promoted to direct. The same target/mapping is idempotent.

Read `applied`, install ID/path, source/target/presentation/working paths,
`repository_relative_path`, source/selector/default/commit facts, `safe_state`,
`symlink_tracking`, `responsible_index`, `frontmatter_changes`, recovery manifest state, and
`planned_changes`. On occupancy/overlap, ignored target, unsupported symlink, unmanaged source, or
nonrecoverable dependency, keep the existing content and follow the finding; there is no replace or
copy fallback.

## Rebind a Nearby Presentation

```text
DOCTIDEX_GIT external rebind SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] --json
```

Use this after installing and reading a new fixed selector/commit when an existing nearby
presentation should retain the same path. `SOURCE_DIRECTORY` follows the durable-link rule above;
`TARGET_PATH` must already be one complete direct managed presentation in ROOT. The command does
not fetch, choose a revision, edit an install, or decide whether the old and new repository layout
is semantically compatible. Review the new content and selector first.

Run dry-run and read `previous_install_id`, `previous_install_path`,
`previous_repository_relative_path`, the new install/source/commit facts, `safe_state`,
`frontmatter_changes`, and `planned_changes`. With `--apply`, `state: rebound` replaces the mapping
at the same target path; existing Markdown links can remain unchanged only when the referenced
repository-relative structure is compatible. `state: unchanged` is a completed no-op. The command
does not write Markdown prose, link annotations, or Git delivery state. Make any necessary semantic
edits natively, then validate and inspect the diff.

Stop on blocked mapping, payload, tracking, or configuration evidence. Do not remove the old
symlink manually to force a rebind: it preserves the live presentation until it can publish the
replacement. The old install remains managed independently; only remove it later under the separate
install-removal authority after its references are gone.

## Unlink One Presentation

```text
DOCTIDEX_GIT external unlink TARGET_PATH [--root ROOT]
  [--dry-run | --apply] --json
```

Use this only with explicit authority to remove that presentation. It accepts the exact managed
target path, not an install ID, and does not remove any payload, cache, other presentation, Markdown
text, or Git state. Dry-run reports the mapped install/path, `frontmatter_changes`, and planned
paths. Apply returns `state: unlinked` after removing only the relative symlink and its portable and
runtime mapping records.

Before either mode completes, the command examines safe Markdown navigation and safe filesystem
symlinks that still point at the presentation. A `presentation_referenced` blocked result lists
locatable `affected` evidence. Do not delete or rewrite those blockers automatically: report them
and wait for the appropriate content-edit authority, then rerun dry-run. Legacy mappings can retain
an index declaration whose ownership cannot be proven; this is expected preservation, not a reason
to edit frontmatter by hand.

## Restore Direct Installs

```text
DOCTIDEX_GIT external restore [--root ROOT] [--install INSTALL_ID]...
  [--limit N] [--cursor TOKEN]
  [--dry-run | --apply] --json
```

ROOT defaults from cwd. Omit `--install` to process all direct manifest entries; repeated filters are
sorted and deduplicated. Unknown IDs produce item-level blocked records rather than an empty match.
Dry-run verifies that each missing exact commit can be reconstructed without persistent writes;
apply restores the same stable path and fixed commit. Neither mode discovers a default branch or
re-resolves branch/tag provenance. Existing durable symlinks and the manifest are not rewritten.

Read `applied`, `recovery_manifest`, `recovery_manifest_identity`, normalized `install_filter`, and
the bounded `items` collection. Each item includes install ID/path, source URL, selector,
default branch, resolved commit, `planned|restored|unchanged|blocked`, and item findings. Item
failure yields a completed warning while other items continue. A cursor is bound to root, manifest
identity, filters, limit, and mode; restart on `cursor_invalid`.

Missing/invalid recovery information blocks the whole operation. Occupied/damaged install paths or
unknown IDs block only their items. Restore only the reported direct install; never create nested
state under installed content or repair links by changing their targets.

## Remove a Managed Install

```text
DOCTIDEX_GIT external remove INSTALL_ID [--root ROOT]
  [--dry-run | --apply] --json
```

Use this only after the user has explicitly authorized deletion. `INSTALL_ID` is one exact current
managed install in the selected owner root; the command has no source URL, path, batch, cursor, or
pagination alternative. ROOT is the owner root or defaults from cwd. Omission of both mode flags is
an offline dry-run. The command never contacts a source, stages/commits, changes Markdown,
presentations, frontmatter, ignore rules, or shared cache.

When the ID is not already known, run `DOCTIDEX_GIT external link-parse PATH [--root ROOT] --json`
first. Only its non-null current `install_id` may be passed to remove. Do not use
`dependency_parent_install_id`: it describes a parent edge, not the install at PATH. An unmanaged
or `dependency_not_installed` result has no current removable target; report that fact and stop.

Read `status`, `findings`, `affected`, `applied`, `install_id`, `install_role`, `install_path`,
`manifest_included`, `state`, `changed`, and `planned_changes`. A reference-free dry-run returns
`state: planned`; apply returns `state: removed` and removes only that payload and its per-install
records. A blocked `install_referenced` result preserves every path and lists the document,
symlink, mapping, or dependency-parent evidence. Do not delete or rewrite blockers automatically:
report them, then wait for user direction or a separately authorized edit.

Unknown IDs and damaged managed state are also blocked and preserve the owner root. For an interrupted
remove whose payload is already absent, repeat the same exact ID after checking its new result; do
not choose a replacement ID or run cache cleanup. Stop and report persistent Git/state failures.
