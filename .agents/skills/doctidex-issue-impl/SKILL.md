---
name: doctidex-issue-impl
description: Build implementation plans and follow implementation rules for developing Issue Notes. Use when an Issue Note has a design and needs an implementation plan or implementation execution guidance.
---

# Doctidex Issue Impl

This is a guide, not a script. It owns how to turn a developing Issue Note's design into an implementation plan and how to implement it. Read the [Issue Note README](../../../docs/dev/issues/README.md) and [doctidex-issue-design](../doctidex-issue-design/SKILL.md) before starting. Trigger conditions are owned by [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md).

## Planning workflow

### Read the design first

- Read the `## Design` section in the developing Issue Note.
- Re-read the relevant architecture documents and design decisions when implementation reveals a mismatch.

### Create the implementation plan

- Re-read the relevant code and documentation before planning.
- Break the design into bounded phases with concrete outputs and validation checkpoints.
- Split phases by considering both design needs and code implementation dependencies or interference.
- If phases share code, functions, or other implementation points and their logic must satisfy both designs together, create a separate phase for that interference.
- Do not sacrifice implementation quality to make phases simpler.
- End the plan with a final quality-improvement phase that changes no design requirements; re-evaluate all prior phases, improve implementation quality and elegance, and remove redundancy introduced by poor inter-phase communication.
- State representative code cases and sequencing, not exhaustive code paths.
- Keep `## Progress` current as work proceeds.
- Planning the implementation plan is not implementation authorization; implementation requires separate explicit user authorization.

## Implementation workflow

Follow the code conventions in [src/AGENTS.md](../../../src/AGENTS.md).

### Implement from design semantics

- Follow design intent and architecture semantics; do not let existing code narrow the design.
- If implementation exposes a missing design fact, return to [doctidex-issue-design](../doctidex-issue-design/SKILL.md) rather than inventing a local contract.

### Test-Driven Development

- Implement using Test-Driven Development.
- Design tests from requirements, not from the current code.
- Cover the functional behavior of every public interface.
- Test complex internal implementation units only when necessary; do not test simple or self-evident internal interfaces.
- Raise coverage through more complete public-interface tests; never add tests for small internal interfaces merely to increase coverage.
- Organize tests by design architecture, product feature, and module; do not bloat them into one undifferentiated test file.

### Keep a global perspective across phases

- Keep the whole design and later phases in view while implementing a phase.
- If a logic point must combine the needs of later phases, mark it with `@todo from ${issue-name} phase-${phase-number}` and add a following comment line with background and deferral reason; report the deferred decision in `## Progress`. Do not invent a premature local contract.
- When a later phase reveals that an earlier implementation substantially limits quality, change the earlier implementation if the design requirements remain intact. If a design change is needed, pause implementation, record progress, and ask the user.
- At the start of each phase, scan prior todos and resolve the ones this phase can complete.

### Design authority and internal implementation

- Design requirements are the highest authority: change tests and implementation to satisfy the design, not the reverse. If the resulting code-change area is large, ask the user before continuing.
- Do not preserve internal call compatibility or add compatibility logic such as if-else handling for obsolete parameters. Change all affected call sites.
- If an existing internal implementation unit's semantics no longer support the new design without violating design or architecture, refactor it thoroughly under the new design rather than forcing compatibility.
- Example: if an internal call chain has responsibilities that are now semantically wrong or unclear under the new design, refactor it from the new design rather than extending parameters to preserve the old behavior.

## Review

After implementation planning or execution, verify that:

- the plan follows the design and its phases are bounded;
- representative code cases illustrate semantics without exhaustive code rules;
- implementation does not narrow design constraints;
- `## Progress` reflects the current state;
- the prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
