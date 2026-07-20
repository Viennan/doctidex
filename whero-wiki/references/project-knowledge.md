# Project Knowledge Modes

## Contents

- [Third-Party Code Analysis](#third-party-code-analysis)
- [Development-Mode Project Wiki](#development-mode-project-wiki)
- [Adapting an Existing Project](#adapting-an-existing-project)
- [Development-Mode Knowledge Areas](#development-mode-knowledge-areas)
- [Requirement History](#requirement-history)
- [Code-Derived Knowledge](#code-derived-knowledge)
- [Provenance](#provenance)
- [Development Workflow](#development-workflow)

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

When third-party code or documentation should remain readable but wholly opaque
to Whero maintenance, declare its root in the containing index's
`whero_preserved_paths`. This is simpler than a mount when whole-only disclosure
is acceptable. Use a Git submodule or nested Wiki mount when tasks must validate,
maintain, or partially disclose paths inside it.

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
create all five directories.

Project source directories, generated references, or legacy documentation may
be declared preserved when Whero must never inject metadata, repair links, or
create framework files within them. They remain readable and valid provenance
targets. Do not preserve a knowledge area that Whero is expected to maintain,
and do not use preserved boundaries when file-level partial disclosure inside
that area is required.

## Adapting an Existing Project

Adapting an established repository is a collaborative migration, not a blind
scaffold operation:

1. Inventory existing source and documentation directories before choosing Wiki
   paths; use root `docs/` unless it conflicts with an existing meaning or
   ownership boundary.
2. Ask the user for missing intent, constraints, requirement history, and
   especially design history; do not infer product philosophy from
   implementation alone.
3. If `docs/` conflicts, use a semantically similar, user-approved parent such
   as `knowledge/` or `project-docs/`, then link it from the root index while
   leaving source paths untouched.
4. Record the agreed layout and design decisions in maintained concepts before
   treating the project as fully adopted.

## Development-Mode Knowledge Areas

Create areas only when content exists:

- `docs/user`: usage, development setup, public behavior, and API documentation.
- `docs/requirements`: durable product or engineering needs and the useful
  history of how they changed, including superseded or rejected directions when
  their rationale still explains the current system.
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

## Requirement History

Use a focused requirement document when a capability or constraint has an
evolution worth retaining beyond the concise Wiki-maintenance history in
`log.md`. `Requirement` is a useful descriptive concept type, not a closed
schema or required type name. A requirement document should identify:

- the user, product, operational, or engineering need and its relevant scope;
- constraints and acceptance criteria when they are known;
- material changes in the requirement, their rationale, and their outcome;
- material design or implementation transitions when they explain how the
  project responded to the requirement, without duplicating the normalized
  current-state concepts;
- which directions were accepted, superseded, rejected, or deferred, with the
  version or time boundary needed to prevent an old statement from reading as
  current; and
- links to the current design, implementation, user guidance, discussions, and
  Git revisions that establish the relationship.

Treat these documents as maintained knowledge: set `whero_maintenance: true`
and, when using the curated concept model, `whero_curated: true`; do not set
`whero_scope_required: true`. Organize by cohesive requirement or capability,
not as one repository-wide chronological journal.

Requirements preserve decision context that would otherwise be lost when
`docs/design` and `docs/impl` are normalized after a change. They do not make
every discarded idea permanent. Keep history only when it explains a current
constraint, tradeoff, reversal, compatibility obligation, or likely future
decision. Remove obsolete speculation and redundant intermediate prose that
would mislead retrieval. Clearly labeled historical statements may remain, but
the current requirement statement remains authoritative for the present need,
and current design and implementation concepts remain authoritative for the
present model and code.

Do not use a requirement document as a larger `log.md`. The log records concise
corpus, navigation, and maintenance events; requirement documents explain the
evolution of the project need itself. Conversely, do not preserve requirement
history inside current-state design or implementation prose merely for
completeness. Link those concepts to the relevant requirement history instead.

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
    reference: docs/requirements/session-state.md
```

Supported kinds are `collected-source`, `repository-path`, `git-revision`,
`discussion`, and `user-authored`. Existing `source_documents` is the compact
form of `collected-source` provenance and remains supported.

Use these fields and validation rules:

| Kind | Required fields | Meaning and checks |
| --- | --- | --- |
| `collected-source` | `path`, `sha256` | `path` names an existing file inside the Wiki; `sha256` hashes its exact bytes. |
| `repository-path` | `path` | `path` names an existing file or directory inside the Wiki. Optional `git_commit` must resolve to a real commit in the containing repository. |
| `git-revision` | `commit` | Optional `repository` defaults to `.` and must name a Git repository inside the Wiki; `commit` must resolve to a real commit there. |
| `discussion` | `reference` | `reference` names an existing stable record with `whero_maintenance: true`; transient chat is invalid. |
| `user-authored` | `reference` | `reference` names an existing stable record with `whero_maintenance: true`; attribution alone is insufficient. |

All paths are Wiki-root-relative POSIX paths and must remain inside the Wiki
after symlink resolution. In an available partial view, undisclosed paths and
commits are notices rather than full-Wiki absence errors. Digest or recorded
HEAD drift remains a review diagnostic unless strict stale validation is used.

## Development Workflow

Make Wiki maintenance part of development completion:

1. Record new or materially changed needs in `docs/requirements` when their
   evolution has durable explanatory value.
2. Normalize direction-changing why/what decisions into current
   `docs/design` concepts, linking requirement history when useful.
3. Update language-specific `docs/impl` concepts with the code change.
4. Keep user guidance aligned with public behavior when in scope.
5. Inspect affected knowledge and validate before completion:

   ```bash
   git diff --name-status
   <python> <skill-directory>/scripts/whero_wiki.py affected \
     --wiki . --git-diff HEAD
   <python> <skill-directory>/scripts/whero_wiki.py validate \
     --wiki . --mode full --strict-stale
   git diff --check
   ```

The affected query checks `repository-path`, `collected-source`, `discussion`,
and `user-authored` provenance. A Git rename contributes both its old and new
path so concepts bound to the old location remain discoverable. The query does
not edit concepts or automatically mark them current.
