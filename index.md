---
type: index
doctidex:
  type: index
  root: true
  atomic-indexing:
    - path: .agents
    - path: .codex
    - path: .github
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

- [Protocol specification](spec/overview.md): the normative Draft v1.1.0 and
  the authority for current doctidex conformance. The `spec/` directory uses
  atomic indexing; this document is its primary entrypoint.
- [Archived v0.1.0 protocol](spec/archive/v0.1.0.md): the unchanged historical
  protocol superseded by the current specification.
- [Design documentation](docs/index.md): current implementation Architecture,
  project-wide Requirements and Issues, and concrete implementation Details.
- [Implementations](impls/index.md): shared libraries and agent-facing plugins.
- [Repository guide](AGENTS.md): repository layout, maintenance boundaries, and
  documentation and Skill design rules.
- [License](LICENSE): repository licensing terms.
- [Git ignore rules](.gitignore): local and generated paths excluded from Git.

## Atomic Repository Content

- [`.agents/`](.agents/) contains repository-local maintenance Skills.
- [`.codex/`](.codex/) contains local Codex configuration.
- [`.github/`](.github/) contains GitHub CI and automation configuration.

These support directories and the `spec/` protocol directory are indexed only
by purpose. Their contents remain available to native file and search tools
without expanding the doctidex index hierarchy.

## Declared Unsafe Material

- [`.asserts/`](.asserts/) <!-- doctidex: {unsafe: true} --> contains read-only collected sources used
  to construct tests.
- [`.tmp/`](.tmp/) <!-- doctidex: {unsafe: true} --> contains disposable test workspaces.
- [`.venv/`](.venv/) <!-- doctidex: {unsafe: true} --> contains the local Python environment.
- [`.ruff_cache/`](.ruff_cache/) <!-- doctidex: {unsafe: true} --> contains generated linter state.
- [`.git/`](.git/) <!-- doctidex: {unsafe: true} --> contains Git's repository metadata.

These directories remain readable and discoverable, but their generated,
collected, or disposable internal structures are not required to conform to
the protocol.
