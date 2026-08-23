# Doctidex Directory Tree v2 Architecture

This document defines the current directory-tree architecture for doctidex v2. It is authority for how a repository becomes a navigable knowledge base without ceasing to be an ordinary file tree.

## Purpose and scope

A doctidex tree is an ordinary directory tree whose root `index.md` declares root identity. Other files and directories remain ordinary content. Indexes can appear where they improve navigation; they are not required at every ancestor.

The architecture separates stable structural concepts from navigation policy:

- Root identity is mechanical and fixed.
- Index placement and navigation are intentional and can evolve with content.
- Boundary points mark paths where this tree's structural rules stop.

## Domain model

| Concept | Definition | Responsibility |
|---|---|---|
| **DoctidexRoot** | A directory that directly contains a valid root index. | Provides the start of the tree. |
| **RootIndex** | The `index.md` in the root. | Declares root identity and provides top-level navigation. |
| **IndexDocument** | Any `index.md` inside the current tree. | Supplies scoped navigation or query entry points without requiring an ancestor index chain. |
| **OrdinaryContent** | Files and directories outside the root index. | Carries the tree's actual content. |
| **BoundarySet** | The set of escape directories for the current tree. | Ends the current tree's structural rules at a boundary. |
| **BoundaryPoint** | One directory in the boundary set. | Identifies where path interpretation changes. |
| **MarkdownDocument** | Any Markdown document inside the current tree. | Uses the same local link semantics as index documents. |
| **StructuredLinkAnnotation** | A `doctidex` HTML-comment YAML block after a link. | Records structural link metadata, currently `cross-boundary-point`. |

## Root identity

A directory is a DoctidexRoot when it contains `index.md` with exactly:

```yaml
---
type: index
doctidex:
  type: index
  root: true
---
```

All three fields are required. A missing or conflicting field means the directory is not a doctidex v2 root.

Root identity is not inherited by nested indexes. A nested `index.md` is an IndexDocument, not a root declaration.

## Index placement

An IndexDocument may appear anywhere inside the current tree. Its ancestors are not required to contain indexes. An index exists only where its navigation value justifies it; empty or ceremonial indexes are not part of the model.

Index content has no fixed template. It may use headings, tables, links, and code blocks. It must preserve progressive disclosure and lead readers to authoritative content rather than duplicating it.

## Boundary semantics

The BoundarySet is the current tree's escape boundary. Once a path crosses a BoundaryPoint, the current tree's structural rules no longer apply. The path may belong to another doctidex tree, a Git installation, a worktree, or any other ordinary tree.

The directory-tree architecture does not define a storage format for the BoundarySet. Concrete tools, such as `doctidex-git`, supply boundary records and derived boundary points.

## Link semantics

All Markdown documents in the current tree share these link rules:

- A path beginning with `/` is relative to the current DoctidexRoot.
- A path not beginning with `/` is relative to the source document's directory.
- Relative paths are preferred when they express the same target.
- A link may be repeated where it improves navigation or query behavior.
- A link is not required to cover every document in scope.

For cross-boundary links, `StructuredLinkAnnotation` records the first BoundaryPoint crossed:

```markdown
[External](/external/guide.md)
<!-- doctidex: {cross-boundary-point: /external} -->
```

The annotation must be a full path-segment prefix of the link path and must resolve to the first crossed BoundaryPoint.

## Responsibilities

| Owner | Responsibility |
|---|---|
| RootIndex | Declare root identity and provide repository-wide entry points. |
| IndexDocument | Provide scoped navigation where the root cannot remain clear. |
| MarkdownDocument | Reference local content with the tree's link semantics. |
| BoundaryPoint | End this tree's structural interpretation. |
| OrdinaryContent | Preserve ordinary file-system behavior. |

This architecture defines current structure only. Requirement history and rationale belong in Issue Notes, not here.
