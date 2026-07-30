---
type: index
doctidex:
  type: index
  root: true
  atomic_entries:
    - path: .agents
    - path: .codex
    - path: spec
  excludes:
    - path: .doctidex/mounts
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

- [Protocol specification](spec/overview.md): the normative draft and the
  authority for doctidex conformance. The `spec/` source directory is atomic;
  this document is its primary entrypoint.
- [Design documentation](docs/index.md): current implementation Architecture,
  project-wide Requirements, and concrete implementation Details.
- [Implementations](impls/index.md): shared libraries and agent-facing plugins.
- [Repository guide](AGENTS.md): repository layout, maintenance boundaries, and
  documentation and Skill design rules.
- [License](LICENSE): repository licensing terms.
- [Git ignore rules](.gitignore): local and generated paths excluded from Git.

## Atomic Repository Support

- [`.agents/`](.agents/) contains repository-local maintenance Skills.
- [`.codex/`](.codex/) contains local Codex configuration.

These support directories are indexed only by purpose. Their contents remain
available to native file and search tools without expanding the doctidex index
hierarchy.

## Excluded Material

`.asserts/` contains read-only collected sources used to construct tests;
`.tmp/`, `.venv/`, `.ruff_cache/`, `.git/`, and `/.doctidex/mounts/` are local,
runtime, metadata, or reserved content outside this directory tree's indexing
and maintenance scope.
