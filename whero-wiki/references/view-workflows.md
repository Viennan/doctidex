# View Workflows

This guide covers the active View tooling. The normative contract is in
[Whero Wiki Views](../spec/views.md).

## Create Or Expand

Resolve `<skill-directory>` as the directory containing `SKILL.md`:

```bash
<python> <skill-directory>/scripts/whero_wiki.py view \
  --target /path/to/view-parent \
  --view-name task-reference \
  /path/to/source-wiki/topic/document.md \
  --dry-run
```

Use absolute, `~`-based, source-relative, working-directory-relative, or
`--include-from` paths. The CLI infers the nearest source Wiki or View from
absolute or working-directory-relative selections. Pass `--source` as a Wiki
or View root, or any path inside it, when inference is impossible or ambiguous.
The standalone `build_view.py` entry point accepts the same View options.

An absolute path inside a nested Wiki has both an inner lifecycle root and an
outer Wiki that treats it as a Mount. This is genuine ambiguity: use `--source
<outer-wiki>` to materialize the whole Mount, or `--source <nested-wiki>` to
create a View whose direct source is the nested Wiki.

Use this loop:

1. Select the narrowest useful file or directory, including a path inside a
   boundary when that is what the user requested.
2. Run `--dry-run` and review effective-root promotion, collapse, collisions,
   source identity, and source relocation actions.
3. Apply the same command without `--dry-run`.
4. Re-inventory the View and expand again only for a material information gap.

The builder does not follow Markdown links transitively.

## Selection Behavior

- Record caller selections separately from materialized effective roots.
- Add ancestor-path Markdown files marked `whero_view_required: true`.
- Promote a preserved descendant, Mount descendant, or path through a source
  symlink to the required whole boundary without rejecting the selection.
- Keep a View-of-View linked to its immediate parent View. Never resolve its
  links to the ultimate Wiki or retrieve a path unavailable in the parent.
- Exclude atomic boundaries from adaptive-collapse file counts.
- Collapse at the configured percentage, default `80`; pass `0` to disable.
- Never create delegated child View metadata while expanding an outer View.

## Safety And Identity

A View contains generated `whero-wiki-view.md`, a relative link to the source
`whero-wiki-meta.md`, and relative links to immediate-source path entries. The
builder preflights selections, boundaries, source relocation, and collisions
before mutation. It never copies or edits source documents.

For Git-controlled sources, require forward ancestry and reject content or
structural changes intersecting effective roots. Reject selected dirty,
untracked, or ignored content before recording `HEAD`. Changes outside those
roots and executable-bit-only changes may advance the recorded identity. Remote
metadata is sanitized before storage.

On a source-change failure, report what changed, which roots intersected, and
that existing read-through links may already expose new bytes. Require review
of a concrete repair or rebuild; never accept changed source content implicitly.

## Restoration And Interruption

Treat readable symlinks as current availability truth after an interrupted
metadata update. `requested_selections` remains rebuild intent and
`effective_roots` records the last applied plan. A later successful expansion
reconstructs diagnostics and atomically rewrites metadata.

Plan View restoration with:

```bash
<python> <skill-directory>/scripts/whero_wiki.py restore --view <view-root> \
  --source <reviewed-relocated-wiki-or-view>
```

For a missing recorded Git source, provide `--store <directory>` instead.
Review the plan and repeat with `--apply`. Restoration recreates links to the
immediate source entries and does not bypass an unavailable parent View.
Restore a multi-View chain from its first unavailable upstream source toward
the downstream Views. A non-Git source that is gone and has no explicitly
reviewed replacement cannot be restored automatically; recover it externally
before rebuilding the View.
