---
name: wiki-reader
description: Search, navigate, read, compare, and cite a fully or partially disclosed Markdown reference wiki while keeping research local-first and source-aware. Use for questions that require facts, examples, API guidance, schemas, provider comparisons, or historical snapshots from all or selected parts of `whero-wiki`, including views that omit parent directories, `index.md`, `log.md`, sibling topics, or linked files.
---

# Wiki Reader

Use the wiki as a progressively disclosed reference corpus. Remain read-only:
do not edit source documents, indexes, or logs while using this skill.

## Establish the Disclosed Scope

1. Use every reference path supplied by the user or host. The disclosed material
   may be one directory, several non-adjacent directories, or individual files.
2. Treat those paths as the available search scope. Follow explicit links when
   their targets are available, but do not assume that parents, siblings,
   repository instructions, indexes, logs, or companion skills were disclosed.
3. Otherwise, use `whero-wiki/` when it exists in the current repository.
4. If neither is available, inventory Markdown with `rg --files -g '*.md'` and
   identify likely reference paths from their directory structure. Prefer an
   `index.md` when one exists, but do not require it. Ask for the disclosed paths
   only when discovery leaves multiple plausible scopes.

Do not assume that the corpus name, current working directory, or neighboring
agent configuration is fixed. When advising how to disclose selected content,
recommend preserving its original relative paths beneath `whero-wiki/` rather
than flattening the directory structure.

## Navigate Before Searching

1. Read any available `index.md` that covers the question, starting with the
   shallowest disclosed index when several exist.
2. Follow the narrowest relevant disclosed index and source entries.
3. Treat indexes as routing summaries, not as evidence that replaces the linked
   source.
4. If parent or local indexes are absent or incomplete, inventory every disclosed
   directory recursively with `rg --files <path>` and include explicitly supplied
   files in the candidate set.
5. Treat `log.md` as optional. Read an available log only when update history or
   snapshot provenance matters; do not infer freshness from a missing log.

Infer provider and product context from the local index, source documents, and
any available preserved path segments. Missing parent context is a coverage
limitation, not evidence that the local index is malformed.

## Fall Back Without Indexes

When no useful `index.md` is disclosed:

1. Inventory all disclosed Markdown files recursively.
2. Group candidates by preserved path, provider or product names, filename, and
   apparent document family such as guidance, API reference, or schema.
3. Extract headings with `rg -n '^#{1,6} '` from plausible candidates.
4. Search filenames, headings, and bodies for the user's terms and close
   synonyms, then read only the most relevant ranges.
5. Build a temporary routing model in memory; do not create navigation files.

Absence of an index or log does not reduce a source document's evidentiary value.
It only removes navigation or provenance context.

## Handle Cross-Scope Links

- Resolve a relative link from the directory containing the linking document.
  Follow `../` links and other cross-directory paths when the target exists in
  the connected reference layout.
- Accept unresolved links in a partially disclosed view. Do not treat them as
  corruption, silently rewrite them, or discard the relationship they express.
- Decide whether a missing target is necessary for the user's question. If it is
  optional, continue with available sources and mention the limitation only when
  material. If it is necessary, identify the missing path and explain what the
  link indicates, then ask the user to connect or provide that file or subtree.
- Do not substitute a web search for a missing local target unless the user asks
  for live verification or authorizes external research.

## Search Efficiently

Start with filenames and headings, then search bodies:

```bash
rg --files <scope> | rg -i '<provider|topic|endpoint>'
rg -n '^#{1,6} ' <candidate-files>
rg -n -i '<exact term|synonym|API field>' <scope>
```

- Search spelling variants, product names, endpoint names, and exact schema
  fields when the first query is sparse.
- Use `wc -l -w -c` to size unfamiliar or generated documents before reading.
- For large documents, read the introduction, heading map, relevant section, and
  representative examples with targeted ranges. Do not load thousands of
  repeated schema lines without a reason.
- Follow links only when they resolve the question or explain a dependency.

## Select Sources

- Prefer the smallest source that directly answers the question.
- Distinguish explanatory guidance from exact API or schema references.
- Keep provider claims separate; compatibility does not imply identical
  behavior.
- Treat collected pages as snapshots, not guaranteed current truth. Use dates,
  versions, deprecation notes, and index warnings when available.
- When current accuracy is essential and external verification is authorized,
  compare the snapshot with the provider's official source. Clearly label which
  claims came from the local snapshot and which were verified live.
- If sources conflict, report the conflict and each source's scope instead of
  silently choosing one.

## Answer with Traceable Evidence

Synthesize the answer instead of pasting long excerpts. Preserve exact names,
field optionality, enums, units, and lifecycle order when those details matter.
Link to the relevant available Markdown files, adding headings or line locations
when useful. Preserve meaningful unresolved paths in the explanation and state
any material coverage or freshness limitation. Phrase negative findings as "not
found in the disclosed material" unless the complete corpus was actually
searched.

Do not claim that the disclosed material contains no answer until available
indexes, if any, and every plausible disclosed path have been searched.
