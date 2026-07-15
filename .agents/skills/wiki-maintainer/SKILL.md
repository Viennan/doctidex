---
name: wiki-maintainer
description: Maintain a source-preserving Markdown reference wiki and partial-disclosure-friendly navigation metadata. Use when importing, refreshing, moving, removing, indexing, restructuring, auditing, or repairing exported and site-root links in material under `whero-wiki`, when preparing selected corpus content for external disclosure, and whenever creating or updating hierarchical `index.md` files, chronological `log.md` files, link coverage, or corpus maintenance rules.
---

# Wiki Maintainer

Maintain the corpus as collected source snapshots plus compact, agent-authored
navigation. Borrow Markdown hierarchy, reserved filenames, and progressive
disclosure from OKF v0.1 without requiring source documents to conform to OKF.

## Separate Sources from Maintained Metadata

- Treat collected documents as immutable except for narrowly scoped link-target
  repair. Never correct, translate, reformat, or annotate their prose, and do not
  change link labels when repairing destinations.
- Treat `index.md` and `log.md` as repository-owned metadata when they were
  created for this wiki.
- Record stale claims, duplicates, naming anomalies, links that cannot be
  confidently repaired, and other limitations in the nearest index.
- Add or refresh a source only when explicitly authorized. Preserve the acquired
  bytes and represent any interpretation in maintained metadata.
- Write skills, logs, and non-index maintained metadata in English unless the
  repository's governing instructions require otherwise.

## Inventory Before Editing

Treat the directory supplied for the task as the maintenance boundary. Read its
local `index.md` when present; use `whero-wiki/index.md` only when the whole
corpus is in scope. Consult accessible ancestors or linked sibling scopes when
they provide useful context, but inventory the complete target subtree with
`rg --files` before editing it. Do not infer its shape from a shallow listing.
For unfamiliar or large material, measure files with `wc -l -w -c`, map headings
with `rg -n '^#{1,6} '`, and inspect targeted ranges before summarizing.

Classify the change as one or more of:

- source ingestion or refresh;
- navigation-only maintenance;
- collected-source link repair;
- corpus reorganization or removal;
- maintenance-policy change.

## Repair Links in Collected Documents

Treat a direct child of `whero-wiki/` as a provider subtree. For example,
`whero-wiki/openai/docs/...` and `whero-wiki/openai/references/...` share the
`openai` provider subtree; `whero-wiki/anthropic/...` does not.

- Inspect exported site-root destinations such as `/docs/...`, broken relative
  links, and other clearly localizable documentation routes during authorized
  material maintenance.
- Search for candidates recursively within the linking document's provider
  subtree. Use the destination basename, path suffix, link label, nearby prose,
  document titles, headings, and relevant content to identify a match.
- Require a confident content match. A similar filename alone is a candidate,
  not proof, especially when snapshots contain duplicated or mislabeled files.
- Rewrite only the Markdown destination to a correct relative local path.
  Preserve the link label, surrounding text, formatting, and all unrelated bytes.
- Retain an anchor only after confirming that the target heading exists. Do not
  invent a local anchor from an upstream website fragment.
- Keep the original link unchanged when no confident local target exists. Do not
  force every link to resolve or fabricate a destination.
- Limit default matching and repair to the same provider subtree. Search or link
  across different direct children of `whero-wiki/` only when the user explicitly
  requests cross-provider repair.
- After mechanical repeated replacements, inspect representative changes and
  validate every changed target. A source link left unchanged may remain broken
  or remote; a link rewritten as local must resolve in the full repository.

## Create and Maintain Indexes

Use lowercase `index.md` as the entry point for a directory. Do not add
frontmatter. Treat an index as a high-density routing guide, not a bare file
listing or a replacement for source content.

- Design indexes for partial disclosure. Parent indexes, local indexes, logs,
  siblings, and linked targets may be absent from the material given to a reader;
  navigation must degrade usefully rather than require complete hierarchy.
- Create or update a local `index.md` when it materially improves routing for its
  scope. Do not create an index solely because that directory might be disclosed,
  and do not assume every disclosed selection includes one.
- Give each index enough local context for a fresh-context reader to identify its
  provider, product, topic, document kind, and scope. Do not duplicate all
  ancestor context when preserved paths or cross-scope links convey it clearly.
- Allow links to parents, siblings, and other `whero-wiki/` locations when they
  express useful relationships or route to relevant knowledge. Prefer relative
  paths based on the existing `whero-wiki` directory layout.
- Preserve that relative layout when recommending or preparing selected content
  for disclosure. Do not flatten or rename path segments merely to make a partial
  view look complete.
- Accept dangling links when disclosed material does not include their targets.
  Do not remove, rewrite, or mark them invalid solely because the view is partial;
  they can become resolvable when related paths are disclosed later.
- Provide enough local explanation for useful routing under partial disclosure,
  while allowing parent indexes, logs, and cross-scope documents to supply
  optional detail when present.
- Explain the scope, boundaries, and snapshot limitations that affect routing.
- Match an index entry's language to the source or source group it describes.
  Do not impose a single language across an index whose sources use multiple
  languages.
- Preserve source titles, product names, technical terminology, and distinctive
  wording. Prefer the source's own phrasing when it is concise enough for
  routing, and avoid translation when it could introduce ambiguity.
- In mixed-language scopes, use multilingual sections or entries as needed so
  each source remains accurately represented. Favor fidelity and retrieval
  clarity over linguistic uniformity.
- Group entries by provider, product area, developer problem, API family, or
  another retrieval-oriented distinction.
- Link immediate documents or subdirectories with standard relative Markdown
  links and describe what question each entry answers.
- For a small directory, summarize every document. For a large directory,
  summarize coherent subdirectories or document groups and create deeper local
  indexes where their distinctions matter.
- Ensure every collected document is discoverable through a chain of indexes or
  an explicitly described grouped scope.
- Prefer guidance sources for workflows and schema references for exact fields,
  enums, unions, and return shapes. Explain overlap when multiple sources cover
  the same API family.
- Keep summaries factual and source-bounded. Do not turn external documentation
  into repository policy or product commitments.
- Update the owning index whenever a source or child scope is added, refreshed,
  moved, removed, or materially reclassified.

## Create and Maintain Logs

Use lowercase `log.md` only for scopes where change history improves provenance
or maintenance handoff. Do not create empty logs in every directory.

- Start with a descriptive level-one heading.
- Group entries beneath ISO `YYYY-MM-DD` headings, newest date first.
- Use concise bullets beginning with a conventional label such as
  `**Initialization**`, `**Import**`, `**Refresh**`, `**Move**`, `**Removal**`,
  `**Index**`, `**Link Repair**`, or `**Correction**`.
- Link the affected maintained index or source path when useful.
- Record corpus and navigation changes, not routine reading or searches.
- Describe what changed without implying that source prose was edited. Identify
  snapshot replacement as a refresh and destination-only changes as link repair.
- Update an existing entry only to correct the log itself; otherwise append the
  event under the current date while preserving newest-first order.

## Maintenance Workflow

1. Confirm that the task authorizes corpus or metadata changes.
2. Inventory sources, existing indexes, logs, and links in the affected scope.
3. Preserve source bytes while making the smallest necessary change; for
   authorized link repair, change destinations only.
4. Add or update the maintenance boundary's index and relevant descendant indexes
   for locally useful progressive disclosure while preserving cross-scope
   relationships.
5. Add a log entry when the scope maintains meaningful change history.
6. Validate link syntax and resolve targets against the full repository when it
   is available. Require repaired local source links to resolve, preserve
   unmatched source links, distinguish intentional dangling index links caused by
   partial disclosure, and confirm local index coverage recursively where indexes
   are maintained.
7. Inspect changed paths to ensure only authorized sources and maintained
   metadata changed.
8. Run skill validation when skill files changed and run `git diff --check`
   before handoff.

When revising the repository's format policy or resolving ambiguity in index or
log conventions, read `references/okf-v0.1.md`. Treat it as design input, not a
strict conformance contract; in particular, do not add frontmatter to collected
snapshots merely to satisfy OKF.
