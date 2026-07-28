---
type: index
doctidex:
  type: index
  atomic_entries:
    - path: agent-plugins
    - path: libs
---

# Implementations

This directory contains non-normative implementations of the doctidex
standard. Design documentation explains each implementation's current model;
source and published agent surfaces remain atomic implementation artifacts.

- [Implementation documentation](docs/index.md) provides the maintained design,
  requirement history, and implementation maps.
- [`agent-plugins/`](agent-plugins/) contains published agent-facing plugins and
  Skills. It is atomic; use each plugin's own Skill surface for operational
  guidance.
- [`libs/`](libs/) contains shared implementation source libraries. It is
  atomic; use the linked implementation documentation as the code-reading map.
