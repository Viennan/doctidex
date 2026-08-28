---
name: doctidex-issue-design
description: Design the solution for a developing Issue Note in docs/dev/issues. Use when elaborating the design of an Issue Note in the developing lifecycle.
---

# Doctidex Issue Design

This is a guide, not a script. It owns how to design a solution for an Issue Note in the `developing/` lifecycle. Read the [Issue Note README](../../../docs/dev/issues/README.md) for the developing skeleton and [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md) for triggers.

## User collaboration

When a user comments on an Issue Note, code, or another artifact, first infer intent and identify the developing Issue Note to which the comment applies. Before changing the design from that comment, collect missing context and re-determine the impact scope. Whether the comment addresses a local part or the whole issue, never draw conclusions or fix the design from only the comment's local information. Consider the complete issue and existing design; holistic review is an invariant of this skill.

## Authorization boundary

Authorization to produce a design does not authorize creating an implementation plan—whether through [doctidex-issue-impl](../doctidex-issue-impl/SKILL.md) or otherwise. Implementation planning requires separate explicit user authorization.

## Workflow

### Gather context before designing

- Search active issues for related or affected issues based on the proposal.
- Read the relevant documentation under `docs/user/`, `docs/architecture/`, and `docs/dev/`.
- Read the relevant code to understand the actual implementation details.

### Determine impact scope while designing

Identify the affected:

- user surface;
- architecture;
- code implementation;
- active issues that may be affected.

### Design from existing design

Base the solution on the current architecture and absorb accumulated design experience and best practices from `docs/dev/cookbook` and issue docs, including design decisions, trade-offs, and rationale from active issues. Use the same Domain Driven Design language as the architecture documents. The design shapes the architecture; do not let existing code or local implementation conventions reverse that direction.

### Keep code from narrowing the design

Distinguish design-mandated constraints from constraints introduced by programming-language idioms or current implementation habits. Do not treat an implementation restriction as a design fact.

For example, a design concept may include a path field. The design cares whether the path is accessible and can be passed to Git as a root, not whether it is a real path or a symbolic link. If existing create/read/update/delete logic rejects symbolic links by convention, that is implementation narrowing. If a later requirement supplies a symbolic link, re-read the architecture and decide whether the exclusion is design-mandated or implementation narrowing. Do not block on implementation narrowing or require a user decision; provide representative handling cases in the design.

### Focus on design semantics, not detailed code rules

Use the architecture, design intent, and problem semantics as guidance. Do not enumerate every code path, validation, or conditional change. Provide only representative code cases that illustrate the intended semantics.

## Review

After producing the design, verify that:

- the user surface, architecture, and code impact are identified;
- the design is grounded in existing architecture;
- implementation narrowing is not treated as a design constraint;
- the design states semantics and representative code cases rather than exhaustive code rules;
- the prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md);
- links to related issues and owning documents use path-plus-fragment references, never bare filenames or issue numbers.
