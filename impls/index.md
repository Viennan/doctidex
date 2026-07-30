---
type: index
doctidex:
  type: index
  atomic-indexing:
    - path: agent-plugins
    - path: libs
---

# Implementations

This directory contains non-normative implementations of the doctidex
standard. Source and published agent surfaces remain atomic implementation
artifacts; their maintained design documentation lives in the repository-level
[`docs/`](../docs/index.md) tree.

- [`agent-plugins/`](agent-plugins/) contains published agent-facing plugins and
  Skills. It uses atomic indexing; use each plugin's own Skill surface for
  operational guidance.
- [`libs/`](libs/) contains shared implementation source libraries. It is
  indexed atomically; use
  [doctidex-git Details](../docs/doctidex-git/details/index.md) as the current
  code-reading map.
