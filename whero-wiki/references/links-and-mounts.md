# Links, Preserved Paths, and Mounted Wikis

## Contents

- [Link Forms](#link-forms)
- [Preserved Paths](#preserved-paths)
- [Mounted Wiki Boundaries](#mounted-wiki-boundaries)
- [Mounted Disclosure](#mounted-disclosure)
- [Disclosure Status and Source Identity](#disclosure-status-and-source-identity)
- [Disclosure Errors and Safety](#disclosure-errors-and-safety)
- [Submodule Updates](#submodule-updates)

## Link Forms

Use standard Markdown links. Whero-maintained files may also use a Wiki-rooted
destination:

```markdown
[Terminology](whero-wiki:/concepts/terminology.md)
```

`whero-wiki:/` resolves from the current owning Wiki root, not the filesystem
root. Inside a nested full Wiki or partial disclosure it resolves from that
nested Wiki. It never crosses an ownership boundary.

Prefer ordinary relative links while they remain readable. When a maintained
link needs more than three leading `../` path components, prefer
`whero-wiki:/`; the normalizer reports this as a suggestion rather than
rewriting content. Do not mechanically normalize collected source snapshots.

Use the link tools without adding backlink sections to documents:

```bash
<python> <skill-directory>/scripts/whero_wiki.py links list --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py links inbound \
  --wiki <root> --target <path>
<python> <skill-directory>/scripts/whero_wiki.py links broken --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py links graph \
  --wiki <root> --format json
<python> <skill-directory>/scripts/whero_wiki.py links normalize \
  --wiki <root> --dry-run
```

Link and boundary queries use `--mode auto` by default, detect
`partial-disclosure.md`, and accept the generated symlinked Wiki meta file. Use
`--mode full` or `--mode available` only when the caller must override detection.

The parser ignores fenced and inline code and supports inline, image, and
reference-style Markdown links. Reports distinguish external, resolved,
unavailable, missing, invalid boundary-crossing, and missing-anchor states.
Local URL queries do not become part of the filesystem path. Anchor validation
uses parsed Markdown headings and explicit HTML `id` or anchor `name`
attributes; links and fenced examples do not define anchors. Clear DNS-style
hostnames with any syntactically valid alphabetic top-level domain are external,
while familiar Markdown/document extensions remain local path candidates. In a
partial disclosure, inspect the source-relative view paths rather than resolving
directory symlinks back to source paths. This keeps targets and backlinks stable
and lets a disclosed directory participate in scans without crossing a nested
Wiki or submodule boundary inside it.

## Preserved Paths

A maintained, scope-required `index.md` may declare owner-managed files or
directories relative to its own directory:

```yaml
whero_preserved_paths:
  - vendor
  - exports/raw.md
```

The outer Wiki treats each declared path as an opaque ownership boundary. It may
link to, read, search, and cite the content, but outer validation and link-graph
scans do not recurse into it, and Whero maintenance commands must not write
inside it. The declaration does not add Whero ownership or frontmatter to the
declared content.

- When validating a complete source Wiki with `--mode full`, every declared
  preserved path must exist. Resolving that path, including any symlink, must
  still lead to a file or directory inside the Wiki root.
- When validating a partial disclosure with `--mode available`, a declared
  preserved path may be absent because that boundary was not disclosed. The
  validator reports the path as unavailable without treating the partial view as
  invalid. A disclosed preserved path may be a generated symlink back to the
  source Wiki.

Links may freely cross from outer Wiki documents into preserved descendants.
Linking does not itself disclose the target because the builder does not follow
Markdown links transitively. If a linked descendant is later selected, the
builder promotes that selection to the preserved root and reports the resulting
whole-boundary scope expansion.

Paths must be non-empty relative POSIX paths, may identify a file or directory,
must not overlap, and must not name Whero framework files. Prefer the nearest
useful owning index so the boundary remains understandable under partial
disclosure.

Preserved paths are atomic during disclosure:

- selecting the preserved root discloses it whole;
- selecting any descendant is promoted to the preserved root and discloses it
  whole;
- explicitly selecting an ancestor directory may include it whole;
- adaptive collapse neither crosses the boundary nor counts its internal files;
- scope-required-looking files inside it remain owned by the preserved content
  and are not separately retained by the outer Wiki.

A preserved declaration takes precedence over nested Wiki or submodule
discovery at or below that path. Use a mount instead when inner partial
disclosure, validation, or independent lifecycle handling is required.

## Mounted Wiki Boundaries

Treat nested full Wikis, nested partial disclosures, and Git submodules as mount
boundaries. The outer Wiki discovers and routes to them but does not recursively
own their files, indexes, provenance, or lifecycle. Run validation inside each
nested Wiki separately when its content matters.

A Git submodule containing a valid `whero-wiki-meta.md` is a mounted Whero Wiki.
A submodule without that metadata is an opaque external repository.

List preserved and mounted boundaries with:

```bash
<python> <skill-directory>/scripts/whero_wiki.py mounts --wiki <root>
```

## Mounted Disclosure

Do not disclose a submodule or nested Wiki whole by default.

- Selecting a mounted Whero Wiki root explicitly discloses it whole.
- Selecting a path inside a mounted Whero Wiki delegates to an inner partial
  disclosure at the source-relative mount path. The inner builder applies its own
  scope-required files, collapse threshold, Git identity, and status.
- Outer adaptive collapse excludes mounted contents and cannot cross their
  boundaries.
- Selecting an outer parent that contains a mount is rejected by default. Use
  `--allow-mount-parent` only after deciding to disclose every nested mount in
  that parent whole.
- Selecting a path inside a non-Whero submodule is rejected by default. Select
  the submodule root whole, or use `--allow-plain-submodule-paths` after
  accepting that no inner Whero metadata or framework completion is available.

Nested status files remain authoritative for their inner symlinks. The outer
`partial-disclosure.md` lists delegated mount roots but does not merge their
symlink inventory into its own Git structural-impact calculation.

## Disclosure Status and Source Identity

Every view contains `partial-disclosure.md` at its generated Wiki root with
`whero_maintenance: true`, `whero_scope_required: true`,
`whero_partial_disclosure: true`, a source-relative layout declaration, the view
name, collapse threshold, and reconstructed symlink inventory. The source
`whero-wiki-meta.md` remains a symlink and the Wiki identity file.

- Store `source` relative to the status directory whenever possible.
- For a Git-controlled source containing tracked files, record the current
  commit and Wiki-root path relative to the worktree. A relocated source at the
  same commit is valid; rewrite generated links and status to the supplied path.
- Record a credential-sanitized preferred Git remote only as fetch or checkout
  guidance; remove all URL userinfo, query parameters, and fragments, including
  userinfo in scp-like remotes. Commit ancestry, file blobs, and tree structure
  remain the identity checks.
- Before using `HEAD` as source identity, inspect the final disclosure roots in
  the worktree. Reject tracked-file content edits, selected untracked or ignored
  files, and uncommitted additions, removals, renames, type changes, symlink
  changes, or gitlink changes. Changes outside the disclosed roots do not block
  the operation. A pure executable-bit change is not a content change.
- Require a changed commit to be a strict forward update: the recorded commit
  must be an ancestor of the supplied commit. Reject divergent, rewritten, or
  backward history before structural comparison.
- Compare Git file blobs and tree structure between accepted commits. Ignore
  executable-bit-only changes. Treat regular-file content changes, additions,
  removals, renames, file/directory/symlink type changes, symlink-target changes,
  and submodule pointer changes as source changes.
- Intersect source changes with current disclosure roots by ancestor or
  descendant relationship. Accept changes outside visible roots. Stop before
  mutation when any content or structural change intersects a disclosed root,
  and require the user to review a repair or rebuild before accepting the new
  source identity.
- Remember that the view is read-through: existing symlinks may expose changed
  source bytes before the next builder run. A blocked run preserves the recorded
  commit and generated link/status structure; it does not freeze the old file
  content. Report this explicitly when asking the user to repair or rebuild.
- Without a recorded Git commit, require the resolved source path to remain
  unchanged.
- Treat stale status inventory after interruption as recoverable metadata;
  readable links remain usable and the next successful run reconstructs status.

## Disclosure Errors and Safety

When the builder fails, organize the response under these labels:

- **What happened**: state the failed validation or operation, relevant path or
  roots, and whether links and status were left unchanged.
- **Possible handling**: include when committed or uncommitted source content
  changes intersect disclosed roots, or when an accepted forward Git update
  changes disclosed structure. Inspect the affected paths and the printed Git
  diff when present. Propose a concrete repair or rebuild for user review; do
  not accept the new content baseline implicitly.

For non-forward history, invalid metadata, source identity failures unrelated to
content, preserved boundary violations, unsafe selections, collisions, or
filesystem errors, report only **What happened** and the direct reason. Ask for a
new decision only when resolution changes history, replaces user-owned target
content, accepts changed source content, or expands authority.

Apply these safety invariants:

- Represent selections inside the disclosure model and generated status as
  non-empty, source-relative POSIX paths without `.` or `..` components. This is
  the canonical stored form, not a restriction that callers must satisfy before
  invoking the builder.
- Accept `--include` and `--include-from` entries as source-relative,
  current-working-directory-relative, absolute, or `~`-based filesystem paths.
  Treat list entries as potentially relative to the list file too. Permit `.`
  and `..` in inputs. Resolve and normalize inside the script, then require the
  target to remain within the source Wiki. If multiple base directories produce
  different valid targets, reject the input as ambiguous and ask for an absolute
  path rather than guessing.
- Reject missing or source-escaping items, selection of the source root or
  generated `partial-disclosure.md`, and invalid preserved declarations.
  Promote requested or already disclosed descendant roots when they fall inside
  a newly declared preserved path, then preflight the whole-root collapse before
  mutation.
- Preflight source migration and every link, collapse, delegated disclosure, and
  collision before mutation.
- Collapse a generated container to a directory symlink only after proving it
  contains solely source-matching symlinks and corresponding containers.
- Use relative symlinks and never edit or copy source documents.
- Write status atomically. After a runtime failure, reconcile status only when
  every disclosed link matches the active source; otherwise retain the readable
  view for later recovery.

Treat normal builder output as diagnostics. Surface commit advancement, source
relocation, automatic or requested scope expansion, dry-run action counts,
warnings, and errors rather than routine per-link activity.

## Submodule Updates

The parent repository sees only a gitlink commit, not the inner file changes.
For an inner Whero disclosure, validate the mounted repository independently:

1. Require its new commit to be a forward descendant of the recorded inner
   commit.
2. Compare the mounted repository's own file blobs and Git tree.
3. Stop when content or structural changes intersect its inner disclosed roots.
4. Let the agent propose a reviewed repair or rebuild; do not accept it
   automatically.

For example, if the outer view delegates `vendor/topic/a.md`, a submodule commit
that only edits `vendor/other.md` can be accepted and recorded by the inner
status. A content change, rename, or removal of `topic/a.md` must stop the inner
update and prompt a reviewed disclosure repair. The outer disclosure does not
decide either case from the gitlink alone, so an arbitrary submodule update
cannot invalidate every inner view or hide a meaningful inner change.
