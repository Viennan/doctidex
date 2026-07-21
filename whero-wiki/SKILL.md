---
name: whero-wiki
description: "Create, organize, maintain, query, cite, curate, review, preserve, validate, and selectively expose Whero Wiki knowledge. Use when establishing or adapting a Whero Wiki; navigating complete or partial material; importing or refreshing source snapshots; maintaining indexes, logs, curated concepts, project knowledge, provenance, links, preserved ownership boundaries, nested Wikis, or submodules; or creating and incrementally expanding a structure-preserving Whero Wiki View. Do not impose the model on unrelated material unless the user asks to adopt it."
---

# Whero Wiki

Operate a source-preserving, agent-readable Markdown knowledge base identified
by `whero-wiki-meta.md`. Resolve every bundled resource relative to this
`SKILL.md`; never assume a fixed installation directory.

## Start

1. Locate the supplied Wiki root or search for `whero-wiki-meta.md`. Accept a
   root only when its frontmatter has `whero_wiki: true`,
   `whero_maintenance: true`, and `whero_view_required: true`.
2. Classify the material before acting: full Wiki or View; collected source,
   maintained knowledge, or framework metadata; owned path, preserved boundary,
   nested Wiki, View, or submodule.
3. Choose one primary operation:
   - **Query**: read, search, compare, cite, or answer without writing.
   - **Maintain**: initialize structure, curate, refresh authorized sources,
     repair links, or update indexes and logs.
   - **View**: create or expand a selective read-through projection.
   - **Review**: compare maintained claims with source authority without editing.
4. Query before writing in a mixed task. Write only inside the user's authorized
   boundary and never maintain content beyond a preserved or mounted ownership
   boundary.

Host repository instructions override defaults for language, tooling, tests,
and change scope. Source preservation and ownership boundaries remain defining
contracts.

## Runtime Contract

Use the v0.0.2 runtime. Wiki identity documents and View metadata set
`format_version: "0.0.2"`. Framework documents and Views use
`whero_view_required`, `whero-wiki-view.md`, `whero_view`, and validation mode
`view`.

Use `View` in user-facing prose. Write internal links in maintained documents
as standard relative Markdown destinations.

## Mental Model

- `whero_maintenance: true` identifies Whero-owned content. Missing means the
  file is not maintained by Whero.
- `whero_view_required: true` identifies framework context carried along
  selected ancestor paths; it also requires `whero_maintenance: true`.
- Collected sources preserve upstream bytes. Put summaries, corrections, and
  interpretation in maintained documents.
- Maintained knowledge includes synthesized and normalized content. Curated
  concepts additionally set `whero_curated: true` and retain provenance.
- Framework files identify, route, or operate the Wiki. Standard examples are
  `whero-wiki-meta.md`, maintained `index.md`, and maintained `log.md`.
- A preserved path is an opaque maintenance boundary declared by a maintained
  index. It remains readable but must not be modified by outer Wiki maintenance.
- A mounted Wiki, View, or submodule owns an independent subtree. Run its own
  lifecycle inside that boundary.

Apply these invariants:

- Never translate, normalize, reformat, annotate, or silently correct collected
  prose.
- Repair only a Markdown destination or add the exact marker
  `<!-- whero:unresolved-local-link -->` when an authorized link-localization
  workflow permits it.
- Do not add Whero frontmatter merely because a document is inside a Wiki.
- Keep maintained instructions and framework files in the host-required
  language. Preserve collected-source language and terminology.
- Treat unavailable View content as a coverage limitation, not malformed source.

## Query

1. Read `whero-wiki-meta.md`, then inspect `whero-wiki-view.md` when present.
2. Read the shallowest useful `index.md`; follow the narrowest relevant route.
   Prefer a relevant curated concept for orientation, then verify exact claims
   against collected sources.
3. Inventory with `rg --files`; add `-L` when View directory symlinks must be
   followed. Search filenames and headings before large bodies.
4. Stop at preserved and mounted boundaries unless the query explicitly needs
   their content. Enter a nested Wiki as a separate owning root.
5. Expand a View only when unavailable material is likely to provide a required
   definition, schema, prerequisite, or authoritative evidence. Do not compute
   the transitive closure of links.
6. State snapshot, version, conflict, and View-coverage limitations. Phrase a
   negative result as "not found in the available View" unless the full Wiki was
   searched.

## Maintain

Use the bundled CLI for deterministic scaffolding and validation:

```bash
<python> <skill-directory>/scripts/whero_wiki.py --help
```

For a new Wiki, create `whero-wiki-meta.md` first. Organize coherent top-level
collections, preserve useful source structure, and create indexes or logs only
when they improve routing or provenance. Mark synthesized knowledge as
maintained; mark only framework context as View-required.

Write `index.md` as a dense routing guide, not a file list. Explain the local
content, ownership boundaries, source family, important relationships, and
snapshot limits. Maintain one reachable index chain and update it with material
source or classification changes.

Write `log.md` only when history helps provenance or handoff. Use ISO date
headings newest first and concise labeled entries for imports, refreshes, moves,
removals, index changes, or link repair.

For curated concepts, read [Agent-Curated Knowledge](references/curated-knowledge.md)
before creating or refreshing content. For independent review, use the
[Curated Review Agent Prompt](references/curated-review-agent-prompt.md).

For code repositories, select the operating mode in
[Project Knowledge Modes](references/project-knowledge.md). Keep third-party
analysis non-invasive. Set `whero_project_wiki: true` only when the project
itself is maintained as a Wiki during development.

## Links And External Boundaries

Read [Link Workflows](references/links.md) before graph queries or repair work.
Write maintained internal links as relative Markdown links.

Read [External-Reference Workflows](references/external-references.md) before
declaring preserved paths, entering mounted content, inspecting submodules, or
handling a missing external source. The runtime supports exact
`whero_preserved_paths`, direct-child `whero_preserved_patterns`, detected
nested Wiki/submodule boundaries, declarative references, and planned
restoration.

Use:

```bash
<python> <skill-directory>/scripts/whero_wiki.py links broken --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py mounts --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py restore --wiki <root>
```

Review restoration output before applying it. Use `--store <directory>` for a
missing Git source and repeat with `--apply`. For a View whose immediate source
moved or is missing, use `restore --view <view-root>`, plus `--source
<wiki-or-view-root>` for an explicitly reviewed path relocation or `--store`
for its recorded Git source. Restore a multi-View chain from the unavailable
upstream source toward downstream Views. A lost non-Git source with no reviewed
replacement cannot be restored by the tool.

## Create Or Expand A View

Read [View Workflows](references/view-workflows.md) before creating, expanding,
relocating, repairing, or reviewing a View.

Use the current builder rather than manually creating links:

```bash
<python> <skill-directory>/scripts/whero_wiki.py view \
  --target /path/to/view-parent \
  --view-name task-reference \
  /path/to/source/wiki-root/source/topic/document.md \
  --dry-run
```

Review the dry-run, then apply the same command without `--dry-run`. Select the
narrowest useful path. The CLI infers the source Wiki or View from path
ancestors when unambiguous; use `--source` only to resolve ambiguity or when
selections are source-relative. A path inside a nested Wiki has both inner and
outer lifecycle roots: pass the outer root when the requested result should expose its Mount
whole, or the inner root to create a View of that Wiki itself. Let the builder
add View-required framework files, promote
preserved, Mount, and source-symlink descendants to their required whole roots,
and apply configured collapse. Re-inventory after every expansion.

A View may use another View as its immediate source. Select only paths currently
available there; the builder preserves the parent-source link chain and never
bypasses it to retrieve unavailable ultimate-source content.

## Complete Work

1. Keep source additions, affected navigation, maintained knowledge, and useful
   log entries aligned.
2. Validate the relevant Wiki profile and inspect link diagnostics.
3. Run the host repository's isolated tests when Python behavior changes.
4. Inspect the diff to confirm collected content and ownership boundaries were
   preserved.

## Protocol

Load only the document needed for protocol work:

- [Terminology](spec/terminology.md) and [Chinese](spec/CN/terminology.md)
- [Wiki Model](spec/wiki-model.md) and [Chinese](spec/CN/wiki-model.md)
- [External References](spec/external-references.md) and [Chinese](spec/CN/external-references.md)
- [Whero Wiki Views](spec/views.md) and [Chinese](spec/CN/views.md)
- [Preserved Boundaries](spec/preserved-boundaries.md) and [Chinese](spec/CN/preserved-boundaries.md)
- [Links](spec/links.md) and [Chinese](spec/CN/links.md)
- [Conformance](spec/conformance.md) and [Chinese](spec/CN/conformance.md)

The English documents are normative. Chinese files are synchronized
translations. [Open Knowledge Format v0.1](references/okf-v0.1.md) is historical
background, not Whero Wiki conformance authority.
