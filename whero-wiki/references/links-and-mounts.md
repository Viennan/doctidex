# Links and Mounted Wikis

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

The parser ignores fenced and inline code and supports inline, image, and
reference-style Markdown links. Reports distinguish external, resolved,
unavailable, missing, invalid boundary-crossing, and missing-anchor states.
In a partial disclosure, inspect the preserved view paths rather than resolving
directory symlinks back to source paths. This keeps targets and backlinks stable
and lets a disclosed directory participate in scans without crossing a nested
Wiki or submodule boundary inside it.

## Mounted Wiki Boundaries

Treat nested full Wikis, nested partial disclosures, and Git submodules as mount
boundaries. The outer Wiki discovers and routes to them but does not recursively
own their files, indexes, provenance, or lifecycle. Run validation inside each
nested Wiki separately when its content matters.

A Git submodule containing a valid `whero-wiki-meta.md` is a mounted Whero Wiki.
A submodule without that metadata is an opaque external repository.

List boundaries with:

```bash
<python> <skill-directory>/scripts/whero_wiki.py mounts --wiki <root>
```

## Mounted Disclosure

Do not disclose a submodule or nested Wiki whole by default.

- Selecting a mounted Whero Wiki root explicitly discloses it whole.
- Selecting a path inside a mounted Whero Wiki delegates to an inner partial
  disclosure at the preserved mount path. The inner builder applies its own
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

## Submodule Updates

The parent repository sees only a gitlink commit, not the inner file changes.
For an inner Whero disclosure, validate the mounted repository independently:

1. Require its new commit to be a forward descendant of the recorded inner
   commit.
2. Compare the mounted repository's own Git tree.
3. Stop only when structural changes intersect its inner disclosed roots.
4. Let the agent propose a reviewed restructure; do not repair automatically.

For example, if the outer view delegates `vendor/topic/a.md`, a submodule commit
that only edits `vendor/other.md` or changes the selected file's content can be
accepted and recorded by the inner status. A rename or removal of `topic/a.md`
must stop the inner update and report the affected root. The outer disclosure
does not decide either case from the gitlink alone, so an arbitrary submodule
update cannot invalidate every inner view or hide a meaningful inner change.
