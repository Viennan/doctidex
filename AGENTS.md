# Repository Guide

## Project Scope

`doctidex` is an emerging directory-tree structure standard for use by both
agents and humans. Its current design goals are interoperability, extensibility,
and minimal format constraints.

## Repository Layout

- `spec/overview.md` contains the draft `doctidex` protocol.
- `spec/refs/` contains background reference material.
- `impls/` contains the non-normative implementations of the standard,
  including implementation design documents, shared libraries, and public
  surfaces used by agents.
- `impls/docs/` contains implementation design documents.
- `impls/libs/` contains shared implementation libraries.
- `impls/libs/python/` contains the Python implementation.
- `impls/agent-plugins/` contains agent plugins and their agent-facing
  surfaces. `doctidex-git/` provides the plugin for Git repositories.
- `.asserts/` contains read-only source material used to construct tests.
- `.tmp/` contains disposable test workspaces and is ignored by Git.

## Sources of Context

- `impls/docs/` may define stricter implementation conventions, but those
  conventions are not protocol requirements.
- `spec/refs/` contains background references, not `doctidex` requirements.
- `.asserts/` contains collected source material. Treat it as read-only.

## Working Rules

- Keep proposals, accepted specification, and implemented behavior visibly
  distinct.
- Keep `spec/` focused on standard definitions and `impls/` focused on
  non-normative implementation design, code, and agent-facing surfaces.
- Keep the protocol focused on observable structure, semantics, and
  conformance. Implementation, construction, and maintenance workflows belong
  to implementation variants.
- Do not turn placeholders such as "refer to OKF" into detailed requirements
  without an explicit design decision.
- Make small, coherent changes and preserve unrelated user work.
- Keep implementation design documents, shared libraries, agent-facing
  surfaces, and tests aligned once a behavior spans those layers.
- Validate changes in proportion to their scope using the tooling that exists
  at the time of the change.
