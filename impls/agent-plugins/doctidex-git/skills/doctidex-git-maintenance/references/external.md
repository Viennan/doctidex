# Manage External Git Content

All external write commands default to dry-run and accept `--dry-run | --apply`. Review dry-run,
then add `--apply` only with appropriate authority. Installs and restores may access their source;
link is offline. Payloads are ignored by host Git, while the recovery manifest and relative durable
links remain trackable. The CLI never stages or commits them.

## Install a Fixed Snapshot

```text
doctidex-git external install --url URL [--root ROOT]
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
hits the existing key and remains bounded; self-reference still uses an independent snapshot.

## Handle Cycles and Self-Reference

Use explicit `--dependency-of` requests only for dependency edges the task actually requires. A
dependency is always a flat install in the outer owner root, never a nested checkout inside another
snapshot. If an explicit edge returns to an existing root/source/selector identity, the CLI reuses
that install and records the parent relation, so the cycle is bounded. This also supports a source
that is the owner or host repository itself: it remains an independent logical read-only snapshot,
not the current writable working tree.

The CLI does not discover or recursively install dependencies. A dependency-only install cannot
back a durable link; repeat its source and selector without `--dependency-of` to promote it to a
direct install before linking. Keep the returned fixed selector and commit rather than resolving a
moving ref again.

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
doctidex-git external link SOURCE_DIRECTORY TARGET_PATH [--root ROOT]
  [--dry-run | --apply] --json
```

`SOURCE_DIRECTORY` is a cwd-relative or absolute readable directory inside a complete direct
install or its existing link. `TARGET_PATH` is a nonempty normalized POSIX path relative to ROOT;
it cannot start with `/`, contain empty/`.`/`..` segments, overlap another presentation, or be
occupied/ignored. ROOT defaults from cwd but must own the source mapping.

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

## Restore Direct Installs

```text
doctidex-git external restore [--root ROOT] [--install INSTALL_ID]...
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
