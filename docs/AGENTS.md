# AGENTS.md — The documentation standard

This file defines document structure, Markdown tiers, writing rules. Use [doctidex-prose-standard](../.agents/skills/doctidex-prose-standard/SKILL.md) for required coverage and editorial judgment.

## Directory organization

- **`user/`**: User documentation. Contains all information belonging to the user surface.
  - Overview documents that provide necessary prerequisites and hot-using paths, quickly building the user's mental model of using the `doctidex-git` CLI.
  - Detailed per-command-cluster reference manuals with complete input/output definitions and error handling.
- **`dev/`**: Development documentation. Reference this area while developing and maintaining the repository.
  - **`glossary.md`**: Term quick reference; each entry links to its authoritative explanation with a path-plus-fragment link.
  - **`architecture/`**: Architecture documentation, organized and written using Domain Driven Design pattern.
  - **`cookbook/`**: Step-by-step how-tos with numbered verification steps; best-practice implementation patterns, recommended coordination patterns across modules, and best practices for implementing features on the existing base architecture.
  - **`issues/`**: Issue documentation. The authoritative home for an issue document is its corresponding **scoped-AGENTS.md**; see [dev/issues/AGENTS.md](dev/issues/AGENTS.md).

## Documentation responsibilities

- Issue documents are the authoritative home for design rationale; do not repeat that rationale in other documents.
- Non-issue documents state the current state; Issue documents retain the trajectory that produced the current state.

## Maintenance routing

When creating or revising a document, use [doctidex-doc-maintenance](../.agents/skills/doctidex-doc-maintenance/SKILL.md) to choose its type, scope, and tree location. When wording or reviewing prose, use [doctidex-prose-standard](../.agents/skills/doctidex-prose-standard/SKILL.md) to calibrate wording.
