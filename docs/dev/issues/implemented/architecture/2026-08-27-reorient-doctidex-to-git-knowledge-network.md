# Issue Note: Reorient doctidex around Git repositories as an interconnected knowledge network

Status: implemented

## Problem

The previous product vision treated doctidex as a general directory-tree organization standard. That vision forced the
repository to design abstract structural concepts before there was enough use experience to know which abstractions were
correct. In particular, `index.md` root identity and `DoctidexRoot` were promoted from an implementation convenience into
architectural requirements, and the directory-tree convention was published as a standalone specification even though
`doctidex-git` was the only implemented consumer.

The abstraction surface was larger than the observed problem: the shipped tool manages Git repositories, Installations,
Refs, Worktrees, and boundary points, but the documentation described a generic directory-tree standard around that tool.
The unvalidated abstractions also made future changes harder because documentation and validation were organized around
concepts the product no longer promised.

## Decision

Doctidex is now a pattern and CLI for organizing multiple Git repositories into a connected knowledge network that is
friendly to people and agents. The shipped surface is `doctidex-git`; there is no separate universal doctidex standard.
A Git repository is simultaneously an ordinary development workspace, a knowledge base, and an authoritative external
knowledge source for repositories that import it.

Remote Git hosts such as GitHub are the publication and distribution surface for these knowledge packages, in the same
way Go modules use source repositories for package distribution. A person or agent that fetches one repository can use its
`doctidex-git` model to discover, navigate, and validate declared associated repositories and their context.

The Git root is the only root concept. `DoctidexRoot` is not a separate domain object. Repository-internal paths begin
with `/` and are rooted at the selected Git root. The retained work model remains:

- **Installation**: one external Git source at one fixed commit and one read-only install path.
- **Recursive sub-Installation**: an Installation carries its own `.doctidex-git` model; a sub-Installation can be
  discovered and restored into the owner work model.
- **Ref**: a managed symbolic link from a repository path into an Installation.
- **Worktree**: a managed, untracked editable Git worktree based on a recorded base commit.
- **BoundaryPoint**: a custom or model-derived path where the current repository's link and scan rules stop.
- **StructuredLinkAnnotation**: a `doctidex` HTML-comment YAML block on one Markdown link; it records
  `cross-boundary-point`.

`init` creates only the `.doctidex-git` workspace and its state projections. It does not create or modify `index.md`.
`validate` checks the work model, Markdown links, cross-boundary annotations, and managed physical objects without
requiring `index.md`; the `index.conforms` diagnostic is gone. `index.md` is an ordinary Markdown file.

The standalone directory-tree specification is removed. Its surviving link and boundary contracts are owned by
[docs/dev/architecture/overview.md](../../../architecture/overview.md). The user workflow is described by
[docs/user/overview.md](../../../user/overview.md), and the glossary no longer defines `DoctidexRoot`, `RootIndex`,
`IndexDocument`, or `BoundarySet`.

The code surface changed accordingly:

- `root_index.py` was removed.
- `initialization.py` no longer has root-index preparation.
- `validate.py` no longer has `_index_diagnostics` or `index.conforms`.
- `cli/main.py` no longer maps root-index frontmatter errors.
- Root-index creation and validation tests were replaced with tests that verify `index.md` is ordinary.

## Testing

The Python test suite passes with 94 tests. `ruff check` and `git diff --check` pass. Documentation references to the
removed directory-tree/root-index model were checked outside Issue Notes and none remain.

## Alternatives considered

**Keep the universal directory-tree standard and defer only the unproven parts.**
This preserves the long-term ambition, but it leaves the documentation and validation tied to abstractions that still lack
usage evidence. The narrower Git-repository scope was chosen because the immediate product and authoritative vocabulary
could be corrected with less rework.

**Keep the directory-tree spec but make `index.md` optional.**
This removes one requirement while retaining a second structural authority. It still forces the documentation to explain
two overlapping models and does not answer whether the remaining directory-tree abstractions are justified.

**Make `DoctidexRoot` a formal alias for the Git root.**
An alias would preserve existing wording with minimal documentation edits, but it keeps a named abstraction with no
distinct contract. The plain Git root is used instead.

## Consequences

The product surface is now aligned with the implemented `doctidex-git` CLI. Installation, Ref, Worktree, BoundaryPoint,
recursive sub-Installation, and StructuredLinkAnnotation retain their contracts, while root-index and directory-tree
concepts no longer add an unvalidated architectural layer.

The trade-off is narrower generality. A future directory-tree standard or non-Git consumer is not ruled out, but it is
also not promised by the current model. Existing repositories that contain old root-index frontmatter treat that
`index.md` as ordinary Markdown; no migration path is defined.
