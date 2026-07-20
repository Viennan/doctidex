---
name: whero-wiki
description: "Create, organize, maintain, query, cite, curate, review, preserve, and selectively disclose a Whero Wiki: a source-preserving, agent-readable Markdown knowledge base identified by `whero-wiki-meta.md` in a root directory of any name. Use when establishing a new Whero Wiki; importing, deriving, reviewing, or refreshing knowledge; declaring non-invasive preserved boundaries; creating framework indexes, logs, or agent-curated concepts; repairing or marking local-looking links; searching complete or partially disclosed material; answering from local snapshots; or building and incrementally expanding a structure-preserving symlink view. Do not impose these conventions on an unrelated knowledge base unless the user asks to adopt the Whero Wiki model."
---

# Whero Wiki

Use this skill with any repository that adopts a Whero Wiki. The root directory
may have any name; a valid `whero-wiki-meta.md` with `whero_wiki: true` is the
identity contract. Do not infer Wiki identity from a directory name alone.

## Start Here

1. Locate the Wiki root from the user's paths or host instructions. Otherwise
   search for `whero-wiki-meta.md` and verify its required frontmatter.
2. Classify the available material before acting:
   - complete Wiki or partial disclosure;
   - collected source, maintained knowledge, or framework metadata;
   - ordinary directory, preserved path, nested Wiki, partial view, or Git
     submodule mount.
3. Choose one primary operation:
   - **Query**: read, search, compare, cite, or answer; remain read-only.
   - **Maintain**: establish structure, curate, refresh authorized sources,
     repair links, or update indexes/logs.
   - **Disclose**: build or expand a structure-preserving symlink view.
   - **Review**: compare curated claims with source authority without editing.
4. For code-related work, distinguish non-invasive third-party analysis from a
   development-mode project Wiki in `references/project-knowledge.md`. For
   curated concepts, read `references/curated-knowledge.md`; for links, mounts,
   or disclosure expansion, read `references/links-and-mounts.md`. For an
   independent curated review, use `references/curated-review-agent-prompt.md`.
5. Query first for mixed tasks, report material conflicts, and write only within
   the user's explicitly authorized maintenance or disclosure scope.

Resolve the repository, skill, and Wiki paths from supplied context rather than
inventing a root or silently using the web. Whero Wiki uses preserved snapshots,
maintained routing, local-first retrieval, and optional partial disclosure.

Host repository instructions override defaults about language, tooling, test
commands, and change scope. Source preservation remains a defining Whero Wiki
contract; replace or version a snapshot instead of rewriting its collected prose.

## Knowledge Model

Treat `whero_maintenance` and `whero_scope_required` as independent dimensions:
use `whero_maintenance` as the canonical key spelling.

Mnemonic: `whero_maintenance` answers who owns a file; `whero_scope_required`
answers whether it must travel with every disclosed descendant scope.

- `whero_maintenance: true` means Whero Wiki created or maintains the file.
  Missing means `false`. This flag says who owns the file, not whether it is
  framework metadata or must be copied into every available sub-scope.
- `whero_scope_required: true` means the file is framework metadata required to
  interpret or operate its scope. Missing means `false`. A disclosure builder
  carries these files along every selected ancestor path.
- Every scope-required file must also set `whero_maintenance: true`.

Distinguish four file classes:

1. **Collected sources** are external or upstream snapshots. They normally have
   neither flag. Preserve their original language and content.
2. **Maintained knowledge** is inferred, synthesized, normalized, or otherwise
   authored by Whero Wiki. It sets `whero_maintenance: true` without
   `whero_scope_required: true`. Treat it as knowledge content during query and
   disclosure, not as framework metadata; include it only when selected or when
   its containing directory is selected.
3. **Framework metadata** describes the Wiki structure and operation. It sets
   both flags. `whero-wiki-meta.md`, `index.md`, and `log.md` are standard
   examples; future framework file types use the same pair.
4. **Disclosure status** is generated `partial-disclosure.md` with both flags and
   `whero_partial_disclosure: true`. It belongs only in a generated partial view,
   never in the source wiki.

Agent-curated concepts are a provenance-tracked subset of maintained knowledge.
Set `whero_curated: true` on them, but never make them scope-required. Read
`references/curated-knowledge.md` before creating, restructuring, refreshing, or
reviewing a curated collection.

A **preserved path** is an index-declared ownership boundary, not a fifth file
class and not frontmatter added to the preserved content. A maintained,
scope-required `index.md` declares files or directories relative to its own
directory:

```yaml
---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
whero_preserved_paths:
  - vendor
  - snapshots/raw-export.md
---
```

Each entry must be a safe, non-overlapping relative POSIX path to an existing
file or directory in a full Wiki. It must not name `index.md`, `log.md`,
`whero-wiki-meta.md`, or `partial-disclosure.md`. The declaration means the
outer Wiki may route to, query, and cite the path, but does not inject metadata,
validate or repair its internals, create framework files within it, or otherwise
perform in-place maintenance there. A preserved boundary overrides nested mount
discovery below it. Use a mount instead when the outer Wiki must delegate partial
disclosure or independent Wiki operations inside that content.

Apply these invariants in every workflow:

- Treat collected sources as immutable snapshots. Never translate, normalize,
  reformat, correct, summarize, or annotate their prose.
- The default in-place exceptions are a Markdown destination repair and the
  exact unresolved marker `<!-- whero:unresolved-local-link -->`. Preserve link
  labels, surrounding text, and all unrelated content.
- Import or refresh source material only when authorized, and preserve acquired
  content exactly. Put interpretation, limitations, and routing summaries in
  maintained metadata.
- Update maintained knowledge only through an authorized derivation or
  maintenance workflow. Keep its provenance and distinction from collected
  snapshots clear.
- Never perform Whero maintenance inside an index-declared preserved path. Read
  it when useful, but treat changes as owner-managed replacements or as a
  separate task rooted at that content's own ownership boundary.
- Write maintained instructions, framework files, and logs in English unless the
  host repository specifies another language.
- Match each index entry's language to the source or source group it describes.
  Preserve source titles, product names, terminology, and characteristic
  phrasing; use multilingual entries in mixed-language scopes.
- Standard relative Markdown links may cross directories. A partial view may
  legitimately leave parent, sibling, or other wiki links unresolved.
- Use `whero-wiki:/path` in maintained documents when a stable Wiki-rooted link
  is clearer, especially beyond three parent traversals. Resolve it from the
  current owning Wiki root. Read `references/links-and-mounts.md` for link and
  nested ownership rules.

## Query a Wiki

### Establish Available Scope

1. Use paths supplied by the user or host. Otherwise search for
   `whero-wiki-meta.md` and accept a candidate root only when its frontmatter has
   `whero_wiki: true`, `whero_maintenance: true`, and
   `whero_scope_required: true`.
2. Read the meta file for the Wiki title, description, format version, scope,
   organization, and operational constraints. Do not assume the root directory
   is named `whero-wiki`.
3. At an identified root, inspect `partial-disclosure.md` when present.
   `whero_partial_disclosure: true` identifies a generated partial view. Treat
   its source, validation mode, layout, and inventory as operational metadata.
4. A disclosure may omit parents, siblings, knowledge files, or linked targets,
   but must retain scope-required framework files along disclosed paths. Treat
   unavailable knowledge as a coverage limitation, not malformed content.
5. Treat a preserved path as opaque to outer Wiki validation and graph scans.
   It may still be read directly for a query. In a partial view, an undisclosed
   preserved path is an availability limitation, not a malformed declaration.
6. If explicitly supplied material lacks a valid meta file, it may still be read
   as ordinary documents, but do not identify it as a Whero Wiki or apply Whero
   maintenance/disclosure assumptions without user direction.
7. If a status inventory differs from readable symlinks after an interrupted
   update, use the readable filesystem. A later successful disclosure run can
   reconstruct status.

### Navigate and Search

1. Read the shallowest useful available `index.md`, then follow the narrowest
   relevant local index. When it declares `whero_curated_path`, prefer the
   relevant curated index and concepts for initial retrieval. Treat indexes and
   curated concepts as routing or synthesis, not evidence that replaces
   collected sources.
2. When indexes are absent or incomplete, inventory recursively. Use
   `rg --files -L` for views containing directory symlinks.
3. Group candidates by source-relative path, source or provider, product, topic,
   filename, and document family. Extract headings before reading large files.
4. Search filenames and headings first, then bodies and exact schema fields:

   ```bash
   rg --files -L <scope> | rg -i '<source|topic|endpoint>'
   rg -n -L '^#{1,6} ' <candidate-files>
   rg -n -L -i '<exact term|synonym|field>' <scope>
   ```

5. Size unfamiliar files with `wc -l -w -c`. For large or generated references,
   read introductions, heading maps, relevant sections, canonical roots, and
   representative examples instead of loading repeated structures wholesale.
6. Read `log.md` only when update history or provenance matters. Do not infer
   freshness from a missing log.

### Follow Links and Expand Deliberately

- Resolve relative links from the linking document and bundle-root-looking paths
  from the available wiki root when possible.
- Accept undisclosed or unresolved targets. Recheck a target followed by
  `<!-- whero:unresolved-local-link -->`, but do not assume it exists in source.
- Expand a partial disclosure only when a missing target is likely to supply a
  required definition, exact schema, prerequisite, authoritative explanation,
  or evidence needed to resolve a material gap or conflict.
- Do not expand for tangential context, duplicated explanations, optional
  examples, or speculative link chains when available material is sufficient.
- Prefer one or a few files when their relevance is narrow. If most material in
  a directory is likely useful, request the directory directly; this reduces
  output tokens and path-entry errors.
- After each expansion, re-inventory and reassess. Do not compute the transitive
  closure of links automatically.

If the source wiki or bundled disclosure script is unavailable, identify the
needed source-relative path and ask the user to provide it. Do not silently
replace missing local material with web research unless live verification is
requested or authorized.

### Answer from Sources

- Prefer curated knowledge for a clean initial model when it is available, then
  use the smallest collected source needed for exact support.
- Treat collected sources as more authoritative than curated knowledge. If they
  disagree, use the source as the Wiki conclusion and flag the curated concept
  for review.
- When external knowledge conflicts with the Wiki, compare it against the
  collected source rather than only the curated interpretation. State snapshot
  dates or version limits; source authority inside the Wiki does not prove that
  the snapshot is the latest real-world state.
- State that maintained knowledge was Whero-derived or synthesized when that
  provenance affects confidence.
- Distinguish guidance from exact API or schema references and keep claims from
  different sources separate.
- Treat snapshots as time-bounded evidence, not guaranteed current truth. State
  material version, date, conflict, or coverage limitations.
- Synthesize rather than paste. Preserve exact names, optionality, enums, units,
  and lifecycle order when they matter, and cite available Markdown paths.
- Phrase negative findings as "not found in the disclosed material" unless the
  complete wiki was actually searched.

## Establish or Maintain a Wiki

### Establish the Structure

1. Confirm authorization and choose a root directory with any suitable name.
2. Create `whero-wiki-meta.md` at that root before treating it as a Whero Wiki.
   Use this minimum frontmatter and add a concise body describing scope,
   organization, source boundaries, and important operating constraints:

   ```markdown
   ---
   type: Whero Wiki
   title: <wiki title>
   description: <compact retrieval and scope summary>
   format_version: "0.1"
   whero_wiki: true
   whero_maintenance: true
   whero_scope_required: true
   ---
   ```

   The filename plus `whero_wiki: true` is the identity standard. The two other
   flags establish that the meta file is Whero-maintained and required in every
   disclosed sub-scope.
3. Organize direct children as coherent top-level source, provider, domain, or
   collection scopes. Preserve useful upstream structure below them.
4. Add collected sources without rewriting them. Do not add frontmatter merely
   to make snapshots conform to a format.
5. Create `index.md` or `log.md` only where current content makes it useful. Do
   not create empty scaffolding; use the bundled CLI when deterministic
   frontmatter scaffolding is helpful.
6. Mark derived or synthesized knowledge with `whero_maintenance: true`. Add
   `whero_scope_required: true` only when the file describes framework structure
   or operation and must accompany every selected descendant scope.
7. For agent-curated concepts and collections, follow
   `references/curated-knowledge.md`; keep whole-document provenance separate
   from claim-local Markdown links and preserve source authority.
8. When the Wiki is also a software project, read
   `references/project-knowledge.md`; preserve code vocabulary, keep durable
   requirement evolution separate from normalized current design and
   implementation knowledge, and maintain concepts with code changes.
9. Declare owner-managed source trees, exports, or documents under
   `whero_preserved_paths` when Whero must not maintain their internals and
   whole-only disclosure is acceptable. Keep the declaration in the nearest
   useful owning index; do not add metadata to the preserved target.

Treat the directory named by the maintenance task as the write boundary. Read
available indexes, then inventory the complete boundary recursively with
`rg --files`; do not infer its shape from a shallow listing. Consult accessible
ancestors or linked sibling scopes only for useful context.

### Maintain Indexes

Use lowercase `index.md` as a high-density routing guide, not a bare file list or
substitute for sources. Begin every maintained index with:

```yaml
---
type: Whero Wiki Index
whero_maintenance: true
whero_scope_required: true
---
```

- Explain the local scope, boundaries, source or provider, product or topic,
  document kinds, important relationships, and snapshot limitations needed to
  choose what to read next.
- Design for partial disclosure. An index must remain useful when ancestors,
  siblings, logs, or linked targets are absent, without duplicating context that
  source-relative paths already convey.
- Group entries by retrieval intent, such as provider, product area, developer
  problem, API family, guidance, or schema reference.
- Link documents or subdirectories with standard relative Markdown links and
  state what question each entry answers.
- For a small scope, summarize each source. For a large scope, summarize coherent
  groups and add deeper indexes only where distinctions improve routing.
- Form one reachable index chain. When the root has `index.md`, it is the sole
  entry; otherwise each direct-child `index.md` is an entry. Link a child
  directory or its `index.md` from a reachable parent before relying on that
  child to route knowledge. An isolated index does not provide coverage.
- Make every collected source discoverable through an index chain or an
  explicitly described grouped scope where indexes are maintained.
- Allow useful cross-scope links and acceptable dangling links under partial
  disclosure. Do not flatten or rename paths to make a selected view look
  self-contained.
- Update the owning index when a source or child scope is added, refreshed,
  moved, removed, or materially reclassified.
- Use `whero_preserved_paths` for explicit non-invasive boundaries. Keep entries
  relative to the declaring index, non-overlapping, and accompanied by enough
  index prose for a reader to understand ownership and why only whole disclosure
  is available.

### Maintain Logs

Use lowercase `log.md` only where change history improves provenance or handoff.

Begin every maintained log with:

```yaml
---
type: Whero Wiki Log
whero_maintenance: true
whero_scope_required: true
---
```

- Start with a descriptive level-one heading.
- Group entries under ISO `YYYY-MM-DD` headings, newest first.
- Use concise labeled bullets such as `**Initialization**`, `**Import**`,
  `**Refresh**`, `**Move**`, `**Removal**`, `**Index**`, or `**Link Repair**`.
- Record corpus and navigation changes, not routine reading or searches.
- Describe snapshot replacement as a refresh and destination or marker changes
  as link repair; do not imply collected prose was rewritten.
- Correct an existing entry only when fixing the log itself. Otherwise add a new
  entry under the current date.

### Repair Collected-Source Links

Use each direct child of the wiki root as the default localization boundary.
Never repair links or add unresolved markers inside a preserved path.

1. Inspect exported site-root destinations such as `/docs/...`, broken relative
   links, and other clearly local-looking routes during authorized maintenance.
2. Search recursively inside the same top-level source scope. Use path suffixes,
   basenames, link labels, nearby prose, titles, headings, and content to identify
   candidates. A filename match alone is not proof.
3. On a confident match, rewrite only the destination to the correct relative
   local path. Retain a fragment only after confirming the target heading.
4. If no confident match exists, preserve the destination. For a local-looking
   absolute or relative destination, append the marker immediately after the
   Markdown link or image, only once:

   ```markdown
   [Unavailable guide](/docs/missing)<!-- whero:unresolved-local-link -->
   ```

5. Do not mark `https://`, `http://`, protocol-relative URLs, recognizable URI
   schemes such as `mailto:`, `tel:`, or `data:`, or clear hostnames.
6. Do not search or repair across different top-level source scopes unless the
   user authorizes that broader boundary.
7. Validate every localized target and retained anchor. A marked link may remain
   unresolved; a rewritten local link must resolve in the full source wiki.

### Maintenance Completion

1. Make the smallest authorized source, navigation, and log changes.
2. Keep source additions or refreshes, affected indexes, and meaningful log
   updates aligned in the same change.
3. Validate link syntax, localized targets, acceptable partial-view dangling
   links, index coverage, language alignment, and exact unresolved markers.
4. Inspect the diff to confirm collected source content changed only where
   explicitly authorized by the source-preservation contract.

## Build or Expand a Partial Disclosure

Create `<target>/<view-name>/` as a read-through symlink view of a source Wiki
identified by a valid `whero-wiki-meta.md`. The default `<view-name>` is the
source directory name; use `--view-name` to choose another single directory name.
Resolve `<skill-directory>` as the directory containing this `SKILL.md`, and use
the Python interpreter required by the host repository:

```bash
<python> <skill-directory>/scripts/build_partial_disclosure.py \
  --source /path/to/source/wiki-root \
  --target /path/to/view-parent \
  --view-name task-reference \
  --include source-scope/topic/document.md
```

Use the builder rather than normalizing paths or creating symlinks manually. Pass absolute,
`~`-based, source-relative, or working-directory-relative paths through `--include` or
`--include-from`; list entries may be relative to that file. The builder stores canonical POSIX
selections. Use an absolute path on ambiguity and `--dry-run` when uncertain.

Use this expansion loop: select the narrowest useful path, run a dry run, read
the disclosed view, and expand only when a missing link would close a material
answer gap. Re-inventory after each expansion; the builder does not follow links
transitively or decide whether a structural repair is appropriate.

### Selection and Layout

- The model stores source-root-relative POSIX selections without `.` or `..`; let
  the builder derive this form, and never flatten, rename, or relocate it.
- Select files for narrow needs. Select a directory explicitly when most of its
  contents are useful and the entire subtree may be disclosed.
- When a relevant curated collection exists, prefer disclosing its narrowest
  useful concept or directory first. Add original sources when exact
  verification, ambiguity, conflict, or comparison with external knowledge
  makes their higher authority material.
- Do not add scope-required files to selections merely because they occur on the
  ancestor or owning path of selected knowledge. The builder discovers and adds
  those files automatically.
- When the desired content is a framework file itself, such as one directory's
  `index.md`, select that exact file instead of the directory. The builder still
  adds other scope-required files along its path, but does not select ordinary
  sibling knowledge. Use `--collapse-threshold 0` when the view must remain
  framework-only, so adaptive collapse cannot broaden the selection to the whole
  directory.
- Automatically retain every ancestor-path Markdown file marked
  `whero_scope_required: true`, including the root `whero-wiki-meta.md` and
  applicable `index.md`, `log.md`, or future framework files.
- Do not automatically retain a file merely because it has
  `whero_maintenance: true`. Maintained knowledge without the scope-required flag
  behaves like other knowledge content and must be selected by relevance.
- Expect links to undisclosed material to remain dangling. Add related content
  only when the consuming task needs it.
- Adaptive collapse counts recursively contained source files. When existing and
  requested coverage reaches `--collapse-threshold` (default `80` percent), the
  builder selects the whole directory. `80`, `80%`, and `0.8` are equivalent;
  `0` disables adaptive collapse.
- Treat a nested Whero Wiki or Git submodule as a mount boundary. Do not include
  it in outer collapse coverage. An internal selection delegates to a nested
  partial disclosure; selecting the mount root explicitly discloses it whole.
  Read `references/links-and-mounts.md` before disclosing mounted content.
- Treat each preserved file or directory as an atomic disclosure root. Selecting
  its exact path or any descendant promotes the selection to the preserved root
  and discloses it whole. Ancestor selections may also include it whole, but
  adaptive collapse neither crosses it nor counts its files. The outer builder
  does not inspect inner scope files. Wiki documents may link into preserved
  content; because links are not followed transitively, promotion occurs only
  when the target enters the actual selection set.

### Operational Safety

Every view contains generated `partial-disclosure.md` status and a symlinked
source `whero-wiki-meta.md`. Preflight all selections, source migration, boundary
rules, collapses, and collisions before mutation; use relative symlinks, never
copy or edit sources, and write status atomically.

For Git-controlled sources, require forward commit ancestry and stop when file
content or tree structure changes intersect disclosed roots. Before recording
`HEAD`, also reject selected tracked-file content edits, untracked or ignored
content, and uncommitted structural changes. Changes outside the final disclosure
roots and executable-bit-only changes may advance the recorded source. Reject
unsafe paths, invalid preserved declarations, non-forward history, unexpected
target content, and source identity mismatches. Remote metadata is guidance only
and must omit userinfo, query parameters, and fragments.

On failure, report **What happened**. Add **Possible handling** when committed or
uncommitted content changes require the user to review and repair or rebuild the
affected disclosure, or when an accepted forward Git update requires a reviewed
structural repair. Treat normal builder output as diagnostics and surface only
material scope expansion, relocation, commit advancement, warnings, and errors.

Read `references/links-and-mounts.md` for the exact status schema, Git identity
and relocation rules, structural comparison, preflight guarantees, recovery,
and error-response contract.

After disclosure, return to the query workflow against the generated view.

## Bundled Resources

- `scripts/build_partial_disclosure.py` implements deterministic disclosure and
  incremental expansion. Use it instead of recreating symlink logic.
- `scripts/whero_wiki.py` provides project initialization, maintained document
  scaffolding, curation, validation, affected-concept, link-graph, mount, and
  preserved-boundary commands for maintained knowledge and project Wikis.
- `references/curated-knowledge.md` defines curated collection discovery,
  concept frontmatter, source authority, provenance, lifecycle, and validation.
  Read it for every curated maintenance or review task.
- `references/project-knowledge.md` defines software-project Wiki organization,
  code/discussion provenance, diagrams, and Git-centered maintenance.
- `references/links-and-mounts.md` defines `whero-wiki:/`, backlink and graph
  queries, preserved ownership boundaries, nested Wiki ownership, and delegated
  submodule disclosure.
- `references/curated-review-agent-prompt.md` is a self-contained, read-only
  prompt for an independent curated-knowledge review agent. Replace its input
  placeholders and give it the available Wiki scope.
- `references/okf-v0.1.md` is optional format background; load it only for
  format-policy or index/log ambiguity and never treat it as conformance.
- `tests/` covers disclosure and maintained-knowledge tooling; run it whenever
  bundled Python behavior changes using the host repository's test environment.
