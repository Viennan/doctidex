# Repository Agent Guide

## Purpose

Maintain this repository as a local, agent-readable reference wiki. The collected
material under `whero-wiki/` reduces repeated web searches and provides stable
snapshots for research. Treat the on-disk spelling `whero-wiki` as the canonical
corpus path. External consumers may receive only a selected part of the corpus to
reduce noise; that disclosed view may omit parent directories, indexes, logs,
sibling topics, or linked files.

## Language

- Write repository-authored instructions, skills, logs, and non-index navigation
  metadata in English.
- Match each index entry's language to the source material it describes. Allow
  multilingual indexes for mixed-language scopes instead of imposing one
  repository-wide index language.
- Preserve source titles, product names, terminology, and characteristic phrasing
  in indexes. Avoid translation when it could introduce ambiguity or alter the
  source's meaning.
- Do not translate or otherwise normalize collected source documents. Their
  original language is part of the preserved snapshot.

## Source Preservation

- Treat collected documents under `whero-wiki/` as immutable source snapshots.
- Never correct, translate, reformat, or summarize inside a collected document.
  Link-target repair is the only default in-place exception: change the Markdown
  destination when a reliable local equivalent exists, while preserving the link
  label and all other source content.
- Add repository-owned navigation only through reserved `index.md` and `log.md`
  files. Do not mistake these maintained files for collected sources.
- Add or refresh source snapshots only when the task explicitly authorizes
  ingestion, and preserve the acquired content exactly.
- Record limitations, stale claims, filename anomalies, and upstream links that
  cannot be confidently repaired in the nearest maintained index instead of
  changing source prose or guessing a target.

## Collected-Source Link Repair

- Treat each direct child of `whero-wiki/` as a provider subtree, such as
  `whero-wiki/openai/` or `whero-wiki/anthropic/`.
- When maintaining collected material, inspect broken or exported links and try
  to map site-root paths such as `/docs/...` to an existing local Markdown file.
  Use path suffixes and filenames as candidates, then confirm the match from
  titles, headings, or relevant content before editing.
- By default, search and repair only inside the same provider subtree as the
  linking document. Repair a link across provider subtrees only when the user
  explicitly requests that broader scope.
- Preserve the original link when no confident local match exists. Link repair is
  opportunistic, not a requirement to make every destination local or resolvable.
- After a repair, validate the relative target and any retained heading anchor.

## Skills

- Use `$wiki-reader` from `.agents/skills/wiki-reader/` to locate, search, read,
  and cite wiki material.
- Use `$wiki-maintainer` from `.agents/skills/wiki-maintainer/` whenever adding,
  removing, reorganizing, or indexing material, or when maintaining update logs.
- Use both skills when a task requires research followed by a corpus change.

## Partial Disclosure

- Design navigation for partial disclosure: an agent may receive one directory,
  several selected directories, or individual files rather than the complete
  `whero-wiki` tree.
- Treat `index.md` and `log.md` as useful but optional in a disclosed view. A
  missing parent or local index is not an error and must not prevent recursive
  discovery of the material that is available.
- Give each maintained `index.md` enough local context to identify its provider,
  product, topic, and scope when parent navigation is undisclosed. Do not
  duplicate context already conveyed clearly by preserved paths or cross-scope
  links.
- Allow links to parents, siblings, and other locations under `whero-wiki/` when
  they express useful relationships. A link may remain unresolved when its target
  is not disclosed; do not remove or rewrite it solely for that reason.
- Prefer preserving each selected item's original relative path beneath
  `whero-wiki/` instead of flattening or renaming it. Preserved paths retain
  context and let later disclosures satisfy existing links.
- Make local summaries useful without this `AGENTS.md`, either skill, parent
  navigation, or logs, while allowing cross-scope links to disclose optional
  context.

## Skill Maintenance

- Keep each skill concise and focused on its own workflow.
- Keep `wiki-reader` self-contained: it must remain safe to copy to another agent
  without `wiki-maintainer`, this file, repository-specific helper scripts, or
  bundled references.
- Keep detailed format background in the maintainer's `references/` directory and
  load it only when revising format policy.
- Validate each changed skill with the skill validator and keep
  `agents/openai.yaml` aligned with its `SKILL.md`.

## Change Discipline

1. Start from the material actually available or placed in maintenance scope;
   use `whero-wiki/` only when the whole corpus is in scope.
2. Read available indexes when present, then inventory every disclosed or scoped
   path recursively; do not assume parent navigation exists or a shallow listing
   is complete.
3. Make the smallest authorized change.
4. Update affected indexes and logs in the same change.
5. Validate link syntax, repaired targets, acceptable dangling links, coverage of
   maintained indexes, language alignment, whitespace, and preservation of source
   content other than authorized link destinations.
