# Doctidex Developing Guide

## Introduction

`doctidex` is a directory-tree structure standard that keeps Markdown and ordinary files readable
while providing stable navigation for humans, agents, and programs. It supports repositories as
navigable, traceable knowledge bases, including controlled links to fixed Git revisions in other
repositories.

Version 2.x.x is the active development line. The former 1.x.x codebase and its historical guidance
are preserved in `archive/v1/`; do not treat them as authority for v2 design or implementation.

## Repository Skill Maintenance

Keep operations and data separate: repository Skills define workflows and rules, while other
repository files provide the data those workflows consume. Do not embed repository data in a Skill;
reference its authoritative location and direct the Skill to read it instead.

## Engineering Rules

Do not declare, emphasize, or encode artifact-maintenance rules in an artifact's functional content.
Apply those rules only during artifact development and validation.

Prefer thoughtful, elegant, lean, straightforward solutions; introduce additional abstractions only as complexity
grows and they provide clear value.

Use diagrams, tables, code blocks, and other Markdown-renderable structures proactively to simplify
prose and improve comprehension.
