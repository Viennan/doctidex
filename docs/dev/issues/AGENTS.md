# Issue Notes: Agent Guide

Read [README.md](README.md) for the directory layout, classification, and in-file format. Use [doctidex-issue-maintenance](../../../.agents/skills/doctidex-issue-maintenance/SKILL.md) for lifecycle, archiving, consolidation, and moving rules, [doctidex-issue-design](../../../.agents/skills/doctidex-issue-design/SKILL.md) for developing-stage design, and [doctidex-issue-impl](../../../.agents/skills/doctidex-issue-impl/SKILL.md) for implementation planning and execution rules.

## Finding and reviewing

Treat the lifecycle/class folders as the working inventory: browse `proposed/`, `developing/`, `implemented/`, and `rejected/`; treat `archived/` as sealed history.

## When to use the skill

### Write or update

- Use when a non-trivial change alters behavior, architecture, a contract shared across files or packages, process or tooling, testing strategy, an on-disk, wire, or configuration format, or another decision a maintainer may reasonably revisit.
- Use when a substantial future-work proposal moves into design and implementation.
- Use when an existing `implemented/` Issue Note must be updated to track where its existing decision now lives.
- Use when a decision must be superseded by a new Issue Note rather than rewritten in place.

**Every new implemented Issue triggers a supersession check.** Search the active tree for older issues covering the same decision or mechanism, classify any full or partial supersession with the skill, and archive every qualifying implemented triplet in the same PR. Keep partial supersessions active and cross-linked.

### Design

- Use when an Issue Note enters `developing/` and must receive `## Design`.
- Use when an existing `developing/` Issue Note needs its design refined.

### Plan and implement

- Use when a developing Issue Note has a design and must receive `## Implementation plan`.
- Use when implementation rules or execution guidance are needed for an existing plan.

### Archive or delete

- Use when an `implemented/` Issue Note's decision is complete and its rationale is unlikely to guide future work.
- Use when a rejected Issue Note no longer prevents a plausible mistake.
- Do not use archival for a `proposed/` or `developing/` note; reject an obsolete proposal or finish development first.

### Consolidate

- Use when an `implemented/` Issue Note is fully superseded by the current owning note.
- Use feature-addition consolidation only when the feature is absent from production code, configuration, schemas, durable or wire formats, migration, and compatibility behavior; no current documentation presents it as available; and no test exercises it as supported behavior.

### Move between lifecycles

- Use when a note must move between `proposed/`, `developing/`, `implemented/`, `rejected/`, or `archived/`.

### Add a class

- Use when a new Issue Note class must be introduced.

## How to use the skill

1. Read [README.md](README.md) for the correct lifecycle, class, and file skeleton.
2. Match the request to a trigger above.
3. Use [doctidex-issue-design](../../../.agents/skills/doctidex-issue-design/SKILL.md) for design, [doctidex-issue-impl](../../../.agents/skills/doctidex-issue-impl/SKILL.md) for implementation planning and execution, or [doctidex-issue-maintenance](../../../.agents/skills/doctidex-issue-maintenance/SKILL.md) for lifecycle, archiving, consolidation, and moving.
4. Run the relevant skill's review checks after the change.
