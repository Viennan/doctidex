# Repository Guide

## Project Status

This repository is undergoing a breaking, from-zero redesign from `whero-wiki`
to `doctidex`. Do not preserve or infer compatibility with the previous design
unless explicitly requested.

`doctidex` is an emerging knowledge-organization standard for use by both
agents and humans. Its current design goals are interoperability, extensibility,
and minimal format constraints.

## Repository Layout

- `spec/overview.md` contains the draft `doctidex` protocol.
- `spec/reference-implementations/` contains non-normative implementation
  designs.
- `spec/refs/` contains background reference material.
- `libs/docs/` contains the code knowledge base used by humans and agents.
- `libs/python/` contains the Python implementation.
- `agent-plugin/` contains agent plugins and will host `doctidex`-based skills.
- `.asserts/` contains read-only source material used to construct tests.
- `.tmp/` contains disposable test workspaces and is ignored by Git.

## Sources of Context

- `TODO.md` records the current direction, but incomplete sections are not yet
  established protocol.
- `stale-AGENTS.md` is historical context only and is not authoritative.
- `spec/reference-implementations/` may define stricter implementation
  conventions, but those conventions are not protocol requirements.
- `spec/refs/` contains background references, not `doctidex` requirements.
- `.asserts/` contains collected source material. Treat it as read-only.

## Working Rules

- Design from the stated `doctidex` requirements; do not carry forward
  `whero-wiki` concepts by default.
- Keep proposals, accepted specification, and implemented behavior visibly
  distinct.
- Keep the protocol focused on observable structure, semantics, and
  conformance. Implementation, construction, and maintenance workflows belong
  to implementation variants.
- Do not turn placeholders such as "refer to OKF" into detailed requirements
  without an explicit design decision.
- Make small, coherent changes and preserve unrelated user work.
- Keep documentation, implementation, and tests aligned once a behavior spans
  those layers.
- Validate changes in proportion to their scope using the tooling that exists
  at the time of the change.
