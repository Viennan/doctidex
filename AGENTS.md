# Doctidex Developing Guide

## Introduction

`doctidex` is a directory-tree structure standard that keeps Markdown and ordinary files readable
while providing stable navigation for humans, agents, and programs. It supports repositories as
navigable, traceable knowledge bases, including controlled links to fixed Git revisions in other
repositories.

Version 2.x.x is the active development line. The former 1.x.x codebase and its historical guidance
are preserved in `archive/v1/`; do not treat them as authority for v2 design or implementation.

## Documentation Roles

`docs/user/` is authoritative for the product's user-visible surface: interfaces, parameters,
results, diagnostics, recovery guidance, and usage patterns.
`docs/architecture/` is authoritative for the product's current design: product model, design
constraints, responsibilities, workflows, and implementation architecture.
`docs/requirements/` records the incremental trajectory of the product's evolution; it does not
replace either user or Architecture documentation as authority for the current product.

Architecture documents must remain self-contained as the authority on the current product. They must
not delegate that authority to Requirements through links, but may link to Requirements to express
the design requirements from which an architectural decision originated. User and Architecture
documentation must be organized from the complete current product design, not by the incremental
numbering or local structure of Requirements.

## Repository Skill Maintenance

Keep operations and data separate: repository Skills define workflows and rules, while other
repository files provide the data those workflows consume. Do not embed repository data in a Skill;
reference its authoritative location and direct the Skill to read it instead.

## Engineering Rules

Do not declare, emphasize, or encode artifact-maintenance rules in an artifact's functional content.
Apply those rules only during artifact development and validation.

Prefer thoughtful, elegant, lean, straightforward solutions; introduce additional abstractions only as complexity
grows and they provide clear value.

Do not speculate about error handling for incomplete areas or cases impossible under the established overall design.

Use diagrams, tables, code blocks, and other Markdown-renderable structures proactively to simplify
prose and improve comprehension.

## Python Development

Use the project-root `.venv` as the runtime environment for all Python code and tools in this
repository. Create it before use when it does not exist.

Develop all Python code in this repository against Python 3.12.
