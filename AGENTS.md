# Doctidex Developing Guide

## Introduction

`doctidex` is a directory-tree structure standard that keeps Markdown and ordinary files readable
while providing stable navigation for humans, agents, and programs. It supports repositories as
navigable, traceable knowledge bases, including controlled links to fixed Git revisions in other
repositories.

Version 2.x.x is the active development line. The former 1.x.x codebase and its historical guidance
are preserved in `archive/v1/`; do not treat them as authority for v2 design or implementation.

## Documentation Roles

`docs/architecture/` is the authoritative description of the product's current state.
`docs/requirements/` records the incremental trajectory of the product's evolution.

Architecture documents must remain self-contained as the authority on the current product. They must
not delegate that authority to requirements through links, but may link to requirements to express
the design requirements from which an architectural decision originated.

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
