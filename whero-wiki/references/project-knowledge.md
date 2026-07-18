# Project Knowledge Modes

Code-related curation has two different operating modes. Choose the mode before
creating metadata or directories; do not apply the development layout merely
because the source happens to be a Git repository.

## Third-Party Code Analysis

Treat an existing third-party codebase as a collected source to analyze. The
analysis is non-invasive: never add `index.md`, `log.md`, frontmatter, or other
Whero framework files inside the source tree.

Two common layouts are valid:

- Make the standalone analysis repository itself a Whero Wiki. Mount the
  codebase within it as a Git submodule, and keep the Wiki framework and curated
  knowledge elsewhere in the same repository, outside the source mount.
- In an existing Whero Wiki, create a scope for the third-party project, mount
  the source repository below that scope, and put curated concepts in sibling
  directories owned by the containing Wiki.

Use any concept-oriented organization that improves retrieval. `user`, `design`,
`impl`, and `references` are optional in this mode, not a required template.
Keep the source mount's ownership boundary and provenance explicit. Do not set
`whero_project_wiki: true` solely because the source is a repository.

## Development-Mode Project Wiki

Set `whero_project_wiki: true` only when the project itself is being maintained
as a Whero Wiki while agents and users develop it. Initialize this mode with:

```bash
<python> <skill-directory>/scripts/whero_wiki.py init-project-wiki \
  --root <repository> --title <title> --description <description> \
  --agent-guide AGENTS.whero.md
```

The command creates only root metadata, `index.md`, `log.md`, and an optional
portable agent guide. It does not create empty knowledge directories and does
not modify source directories.

Keep curated knowledge in a separate `docs/` directory at the project root by
default, outside the source tree. The root `index.md` must identify and link
that directory once it contains knowledge. If `docs/` cannot safely serve this
purpose because of an existing directory or naming conflict, choose another
semantically similar, user-approved name such as `knowledge/` or
`project-docs/`. The areas below are a routing convention, not a requirement to
create all four directories.

## Adapting an Existing Project

Adapting an established repository is a collaborative migration, not a blind
scaffold operation:

1. Inventory existing source and documentation directories before choosing Wiki
   paths; use root `docs/` unless it conflicts with an existing meaning or
   ownership boundary.
2. Ask the user for missing intent, constraints, and especially design history;
   do not infer product philosophy from implementation alone.
3. If `docs/` conflicts, use a semantically similar, user-approved parent such
   as `knowledge/` or `project-docs/`, then link it from the root index while
   leaving source paths untouched.
4. Record the agreed layout and design decisions in maintained concepts before
   treating the project as fully adopted.

## Development-Mode Knowledge Areas

Create areas only when content exists:

- `docs/user`: usage, development setup, public behavior, and API documentation.
- `docs/design`: why, what, philosophy, constraints, tradeoffs, and user intent.
- `docs/impl/<language>`: code maps, entry points, responsibilities, field semantics,
  and call relationships. Do not repeat design reasoning already captured.
- `docs/references`: ordinary files, mounted full or partial Whero Wikis, and Git
  submodules. Preserve each mounted Wiki's ownership boundary.

Use concept documents throughout. Add an overview when it materially connects
multiple concepts or lets a fresh-context agent decide what to open next.
Make every current concept reachable through the root index and any maintained
local indexes. Linking a directory from its parent index and its concepts from a
local index satisfies this chain without forcing a flat root inventory.

## Code-Derived Knowledge

- Preserve concepts and terminology already expressed by code and source
  documentation. Do not invent a competing vocabulary for stylistic neatness.
- Explain every field in documented records, schemas, configs, DTOs, events, and
  public request or response objects.
- Use implementation code to establish concrete relationships between concepts.
- Prefer Mermaid `sequenceDiagram` diagrams for critical calls and workflows.
  Avoid UML class diagrams unless a user specifically requires one; their visual
  and maintenance cost usually exceeds their retrieval value.
- Write high-level analyses from the actual problem outward in why, what, how
  order: the problem, the model introduced to solve it, its tradeoffs, and a
  small number of distinctive implementation excerpts. Do not let excerpts turn
  an analytical concept into a source listing.

Discussion-derived designs must also explain why, what, and how. Persist user or
agent discussion decisions in a maintained record before citing them as
provenance; transient chat history is not a stable reference.

## Provenance

Project concepts may use `provenance` alongside or instead of
`source_documents`:

```yaml
provenance:
  - kind: repository-path
    path: src/runtime/session.py
    git_commit: "<reviewed commit>"
  - kind: git-revision
    repository: .
    commit: "<decision commit>"
  - kind: discussion
    reference: docs/design/session-state.md
  - kind: user-authored
    reference: requirement/session-state
```

Supported kinds are `collected-source`, `repository-path`, `git-revision`,
`discussion`, and `user-authored`. Existing `source_documents` is the compact
form of `collected-source` provenance and remains supported.

## Development Workflow

Make Wiki maintenance part of development completion:

1. Record direction-changing why/what decisions in `docs/design`.
2. Update language-specific `docs/impl` concepts with the code change.
3. Keep user guidance aligned with public behavior when in scope.
4. Inspect affected knowledge and validate before completion:

   ```bash
   git diff --name-status
   <python> <skill-directory>/scripts/whero_wiki.py affected \
     --wiki . --git-diff HEAD
   <python> <skill-directory>/scripts/whero_wiki.py validate \
     --wiki . --mode full --strict-stale
   git diff --check
   ```

The affected query uses repository-path provenance to identify concepts for
review; it does not edit or automatically mark them current.
