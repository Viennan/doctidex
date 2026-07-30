---
type: index
doctidex:
  type: index
  root: true
  atomic-indexing:
    - path: .agents
    - path: .codex
    - path: spec
  unsafe:
    - path: .git
    - path: .asserts
    - path: .tmp
    - path: .venv
    - path: .ruff_cache
---

# doctidex Repository

This repository defines the doctidex directory-tree standard and contains its
non-normative implementations. Start with the protocol when deciding what a
conforming tree means; use the design documentation, implementation code, and
agent surfaces when building or maintaining a concrete variant.

## Primary Entrypoints

- [Protocol specification](spec/overview.md): the normative Draft v1.0.0 and
  the authority for current doctidex conformance. The `spec/` directory uses
  atomic indexing; this document is its primary entrypoint.
- [Archived v0.1.0 protocol](spec/archive/v0.1.0.md): the unchanged historical
  protocol superseded by the current specification.
- [Design documentation](docs/index.md): current implementation Architecture,
  project-wide Requirements, and concrete implementation Details.
- [Implementations](impls/index.md): shared libraries and agent-facing plugins.
- [Repository guide](AGENTS.md): repository layout, maintenance boundaries, and
  documentation and Skill design rules.
- [License](LICENSE): repository licensing terms.
- [Git ignore rules](.gitignore): local and generated paths excluded from Git.

## Atomic Repository Content

- [`.agents/`](.agents/) contains repository-local maintenance Skills.
- [`.codex/`](.codex/) contains local Codex configuration.

These support directories and the `spec/` protocol directory are indexed only
by purpose. Their contents remain available to native file and search tools
without expanding the doctidex index hierarchy.

## Declared Unsafe Material

- [`.asserts/`](.asserts/) contains read-only collected sources used to
  construct tests.
  <!-- doctidex: {unsafe: true} -->
- [`.tmp/`](.tmp/) contains disposable test workspaces.
  <!-- doctidex: {unsafe: true} -->
- [`.venv/`](.venv/) contains the local Python environment.
  <!-- doctidex: {unsafe: true} -->
- [`.ruff_cache/`](.ruff_cache/) contains generated linter state.
  <!-- doctidex: {unsafe: true} -->
- [`.git/`](.git/) contains Git's repository metadata.
  <!-- doctidex: {unsafe: true} -->

These directories remain readable and discoverable, but their generated,
collected, or disposable internal structures are not required to conform to
the protocol.
