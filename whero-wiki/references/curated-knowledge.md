# Agent-Curated Knowledge

## Contents

- [Purpose and Authority](#purpose-and-authority)
- [Collection Discovery](#collection-discovery)
- [Concept Documents](#concept-documents)
- [Provenance and Links](#provenance-and-links)
- [Curation Decisions](#curation-decisions)
- [Indexes and Partial Disclosure](#indexes-and-partial-disclosure)
- [Lifecycle](#lifecycle)
- [Validation](#validation)

## Purpose and Authority

Use an agent-curated collection to reorganize collected source snapshots into
cleaner, concept-oriented knowledge. Curated concepts optimize retrieval,
comparison, and progressive disclosure; they do not replace their sources.

Apply this authority order:

1. Prefer curated concepts for initial navigation, reading, and disclosure when
   a relevant curated collection is available.
2. Treat collected source snapshots as more authoritative than curated
   concepts. If a source and a curated concept disagree, use the source as the
   Whero Wiki conclusion and mark the curated concept for review.
3. When external knowledge conflicts with the Wiki, compare the external claim
   against the collected source, not only against the curated interpretation.
   The collected source represents the Wiki side of the comparison. Report
   snapshot dates or version limits rather than implying that a snapshot is
   necessarily the latest real-world truth.

Curated concepts are Whero-maintained knowledge. Set `whero_maintenance: true`
and `whero_curated: true`, but do not set `whero_scope_required: true`.

## Collection Discovery

A Wiki top-level scope may declare one curated collection. Add
`whero_curated_path` to that scope's maintained `index.md`:

```yaml
---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_curated_path: agent-curated
---
```

The path must be one direct child directory name relative to the top-level
scope. Do not use an absolute path, `.` or `..`. A missing field means that the
scope has no declared curated collection.

Development-mode project Wikis are the exception to this top-level declaration:
their root `index.md` identifies project knowledge areas, and concepts under
`docs/` (or its approved replacement) do not need `whero_curated_path`.

Introduce and link the collection in the index body. The collection root must
contain a maintained, scope-required `index.md` with:

```yaml
---
type: Whero Curated Collection Index
title: Agent-Curated Knowledge
description: Concept-oriented knowledge derived from this scope's sources.
whero_maintenance: true
whero_scope_required: true
whero_curated_root: true
whero_curated_format_version: "0.1"
---
```

The declaration in the top-level index is authoritative. The collection-root
marker supplies local context when only part of the Wiki is available. Keep the
two values consistent.

Organize descendants by concepts and retrieval intent rather than by the source
directory layout. Use nested maintained indexes when they materially improve
routing. A collection may contain an optional maintained `log.md`.

## Concept Documents

Use one Markdown document for one cohesive, independently retrievable concept.
Use the Wiki-root-relative path without `.md` as its concept ID. Keep paths
stable and descriptive; a move changes the concept ID and requires link repair.

Start each concept with YAML frontmatter:

```yaml
---
type: API Model
title: Conversation and Tool-Call State
description: Message retention rules across ordinary and tool-calling turns.
whero_maintenance: true
whero_curated: true
curation_mode: synthesized
curation_status: draft
source_documents:
  - path: provider/guides/conversation.md
    sha256: "<hex digest>"
    role: primary
tags: [conversation, tools]
timestamp: 2026-07-17
---
```

Required fields:

- `type`: an open, descriptive domain type; do not maintain a global registry.
- `title`: the stable display name.
- `description`: a compact retrieval summary.
- `whero_maintenance: true` and `whero_curated: true`.
- `curation_mode`: `adapted`, `distilled`, or `synthesized`.
- `curation_status`: `draft`, `reviewed`, `needs-review`, or `deprecated`.
- `source_documents` and/or `provenance`: one or more whole-document
  provenance entries. Use `source_documents` for collected snapshots and
  `provenance` for repository paths, Git revisions, discussions, or user-authored
  decisions.
- `timestamp`: the date or timestamp of the last meaningful content or
  provenance update.

Optional fields include `tags`, `language`, `aliases`, and producer-specific
metadata. Preserve unknown fields when tooling rewrites frontmatter.

Use structural Markdown suited to the concept. Headings such as `Scope`,
`Model`, `Constraints`, `Relationships`, `Examples`, and `Source Differences`
are useful conventions, not mandatory sections. Preserve exact terminology,
parameter names, enum values, units, ordering, qualifications, and negative
statements. Label agent inference explicitly.

## Provenance and Links

Each `source_documents` entry identifies a collected source snapshot that
materially grounds the concept as a whole:

- `path` is required. Store a Wiki-root-relative POSIX path without a leading
  slash, fragment, `.` or `..` component.
- `sha256` is required. Hash the exact source file bytes so provenance remains
  portable across Git repositories and filesystem locations.
- `role` is optional descriptive context such as `primary`, `supporting`, or
  `contrast`; consumers must tolerate unknown role values.

A source may live inside an index-declared preserved path. The curated concept
may read, cite, and hash that source, but curation maintenance must not rewrite
the preserved source or add metadata within its boundary. Curated collection
roots and concept outputs themselves must not be created inside preserved paths.

For generalized `provenance`, use the kinds and fields in
`references/project-knowledge.md`. A `repository-path` may identify code in the
same project or a mounted third-party repository; a `git-revision` records a
decision or source repository revision; `discussion` and `user-authored` entries
must point to stable maintained records rather than transient chat context.

Use this materiality test: if a source change would require a substantive review
of the entire concept, list the source in frontmatter. If a source supports only
one local claim, link it near that claim instead.

Use standard relative Markdown links for local claims, exact sections,
examples, and relationships between curated concepts. A frontmatter source may
also appear as a body link; the two mechanisms are deliberately non-orthogonal.
Do not treat curated-to-curated links as a substitute for original provenance.
Avoid provenance cycles by pointing `source_documents` at collected snapshots,
not other curated concepts.

## Curation Decisions

Choose the least transformative useful treatment:

1. **Direct use**: when a source is already focused, structured, and accurate,
   route readers directly to it from an index instead of creating a duplicate.
2. **Adapted**: preserve strong source wording, tables, code, and organization;
   add only the concept boundary, retrieval metadata, and navigation needed.
3. **Distilled**: remove unrelated material and repetition while retaining the
   source's exact operational meaning.
4. **Synthesized**: combine multiple sources only when cross-source integration
   resolves a real retrieval need.

Split concepts when their questions, lifecycle, applicability, or provenance
sets differ. Merge source fragments when they describe one stable model. Never
silently resolve a source conflict. Record each source-specific position and the
scope in which it applies.

Keep the directory hierarchy restrained. Count the collection root as depth one;
depths one through three are normal. Create depth four or deeper only after
establishing that the source breadth and concept boundaries justify it. The
validator emits a review warning, not a conformance error, for deeper concepts.

As depth increases, make concepts more cohesive and specialized, with fewer
cross-branch curated links. Source links are not constrained by this guidance.
Do not manufacture depth or split cohesive medium and small concepts merely to
produce a visually regular tree.

For code repositories, project discussions, and development workflows, read
`project-knowledge.md`. First distinguish non-invasive third-party analysis
from a development-mode project Wiki. The former may use any concept-oriented
organization around an unchanged source mount; the latter defaults to
`docs/user`, `docs/requirements`, `docs/design`, `docs/impl`, and
`docs/references` outside source directories, with a semantically similar parent
when `docs/` conflicts. Requirement concepts may retain clearly labeled,
decision-relevant evolution while design and implementation concepts stay
normalized to the current model.

## Indexes and Partial Disclosure

Treat collection indexes as high-density concept maps. Group entries by domain
model, developer problem, lifecycle, or decision rather than source filename.
Make every current curated concept reachable through an index chain. The
top-level source index should also retain direct routes to authoritative source
material. If the Wiki has a root `index.md`, treat it as the chain entry;
otherwise treat each direct-child `index.md` as an entry. A nested index joins
the chain only when a reachable index links its directory or the index file
itself. Links from an isolated nested index do not satisfy concept coverage.

When building a partial disclosure:

- Prefer the narrowest useful curated concept or curated directory when it can
  answer the task with less noise.
- Retain top-level and collection indexes automatically through
  `whero_scope_required: true`.
- Do not automatically disclose `source_documents`; they remain selectable
  knowledge rather than framework dependencies.
- Expand to source material only when exact verification, ambiguity, conflict,
  missing detail, or comparison with external knowledge makes it useful.
- Treat undisclosed provenance and cross-concept links as coverage limitations,
  not malformed documents.
- A request for a preserved source document or any other descendant selects and
  discloses the entire declared preserved root. An explicit selection of the
  root or one of its ancestor directories has the same whole-boundary effect.

## Lifecycle

Create agent-authored concepts as `draft`. Promote a concept to `reviewed` only
after a deliberate source-based review. Prefer an independent review agent for
important or synthesized concepts; use `curated-review-agent-prompt.md` as a
self-contained prompt.

When a source digest, repository revision, or other recorded provenance changes:

1. Do not update the recorded digest or revision automatically.
2. Compare the recorded and current source or repository revisions.
3. If the change is irrelevant to the concept, record the new provenance and the
   completed review without rewriting otherwise correct prose.
4. If the change affects the concept, update the body, provenance, timestamp,
   owning index, and meaningful log entry together.
5. Set `curation_status: needs-review` when the impact cannot be resolved.
6. If a source disappears or moves, do not guess a replacement. Rebind the
   source through an authorized maintenance decision or deprecate the concept.

The bundled `record-source-digests` command updates `source_documents` only. For
repository revisions, discussions, or user-authored provenance, update the
frontmatter through an explicitly authorized maintenance pass after review.

Use `deprecated` only when the concept should no longer route current queries.
Link its replacement when one exists and remove it from current index routes.

## Validation

Run the bundled validator in full mode against a complete source Wiki and in
available mode against a partial disclosure:

```bash
<python> <skill-directory>/scripts/whero_wiki.py validate \
  --wiki /path/to/wiki --mode full
```

Validate mechanically:

- collection declaration and collection-root metadata agreement;
- required concept fields and allowed lifecycle values;
- absence of `whero_scope_required: true` on curated concepts;
- safe provenance paths, source existence, and applicable digest or revision
  freshness;
- framework type, ownership flags, title heading, and log date/order invariants;
- reachability of maintained indexes from the applicable chain entries;
- local Markdown targets and curated index coverage;
- full-Wiki errors versus acceptable unavailable targets in a partial view.

Treat source or revision mismatches and drafts as review diagnostics. Use
`--strict-stale` when CI should fail on stale provenance. Mechanical validation
cannot prove conceptual coherence, source fidelity, conflict handling, or the
quality of an inference; assign those checks to a review agent.
