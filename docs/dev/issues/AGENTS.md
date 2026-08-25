# Issue Notes: Agent Guide

Read [README.md](README.md) for the directory layout, classification, and in-file format. Use [doctidex-issue-proposal](../../../.agents/skills/doctidex-issue-proposal/SKILL.md) for proposed-stage discussion, [doctidex-issue-design](../../../.agents/skills/doctidex-issue-design/SKILL.md) for developing-stage design, [doctidex-issue-impl](../../../.agents/skills/doctidex-issue-impl/SKILL.md) for implementation planning and execution, and [doctidex-issue-maintenance](../../../.agents/skills/doctidex-issue-maintenance/SKILL.md) for lifecycle, archiving, consolidation, and moving rules.

## Terminology

**Active issues** are Issue Notes in `proposed/`, `developing/`, `implemented/`, and `rejected/`. A non-deleted `rejected/` note remains active because it records a rejected design decision that can guide new work. `archived/` is sealed history, not active.

## Routing user input

Try to match user input to the active Issue Note it concerns, preferring an issue already active in the session context and falling back to repository search. If a `proposed/` issue matches, use [doctidex-issue-proposal](../../../.agents/skills/doctidex-issue-proposal/SKILL.md); if a `developing/` issue matches, use [doctidex-issue-design](../../../.agents/skills/doctidex-issue-design/SKILL.md).

## Finding and reviewing

While an issue is `proposed/` or `developing/`, search active issues for content-related issues whose decisions may affect it. Prefer active issues already present in the session context; use issue links as one signal, not the only search method. Treat the active lifecycle/class folders as the working inventory.

## When to use the skill

### Propose or discuss

- Use when a new proposal is created or an existing `proposed/` Issue Note is refined; use [doctidex-issue-proposal](../../../.agents/skills/doctidex-issue-proposal/SKILL.md).
- Use when a user discusses a proposed issue or comments on code or documents in its context; treat that input as proposal discussion, not repository changes.

### Write or update

- Use when a non-trivial change alters behavior, architecture, a contract shared across files or packages, process or tooling, testing strategy, an on-disk, wire, or configuration format, or another decision a maintainer may reasonably revisit.
- Use when a substantial future-work proposal moves into design and implementation.
- Use when an existing `implemented/` Issue Note must be updated to track where its existing decision now lives.
- Use when a decision must be superseded by a new Issue Note rather than rewritten in place.

### Design

- Use when an Issue Note enters `developing/` and must receive `## Design`.
- Use when an existing `developing/` Issue Note needs its design refined.

### Plan and implement

- Use when a developing Issue Note has a design and must receive `## Implementation plan`.
- Use when implementation rules or execution guidance are needed for an existing plan.
- Authorizing design does not authorize implementation planning; `doctidex-issue-impl` requires separate explicit user authorization.

### Archive or delete

- Use when an `implemented/` Issue Note's decision is complete and its rationale is unlikely to guide future work.
- Use when a rejected Issue Note no longer prevents a plausible mistake.
- Do not use archival for a `proposed/` or `developing/` note; reject an obsolete proposal or finish development first.

### Consolidate

- Use when an `implemented/` Issue Note is fully superseded by the current owning note.
- Use feature-addition consolidation only when the feature is absent from production code, configuration, schemas, durable or wire formats, migration, and compatibility behavior; no current documentation presents it as available; and no test exercises it as supported behavior.

### Move between lifecycles

- Use when a note must move between `proposed/`, `developing/`, `implemented/`, `rejected/`, or `archived/`.
- Use when a note moves into `implemented/`; run the supersession hook described in [doctidex-issue-maintenance](../../../.agents/skills/doctidex-issue-maintenance/SKILL.md).

### Add a class

- Use when a new Issue Note class must be introduced.

## How to use the skill

1. Read [README.md](README.md) for the correct lifecycle, class, and file skeleton.
2. Match the user input to an active Issue Note using the routing rule above; prefer session-context active issues.
3. Use [doctidex-issue-proposal](../../../.agents/skills/doctidex-issue-proposal/SKILL.md) for `proposed/`, [doctidex-issue-design](../../../.agents/skills/doctidex-issue-design/SKILL.md) for `developing/` design, [doctidex-issue-impl](../../../.agents/skills/doctidex-issue-impl/SKILL.md) for implementation planning and execution, or [doctidex-issue-maintenance](../../../.agents/skills/doctidex-issue-maintenance/SKILL.md) for lifecycle, archiving, consolidation, and moving.
4. Run the relevant skill's review checks after the change.
