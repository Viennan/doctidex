---
name: dev-workflow
description: Coordinate repository development and maintenance from user intent through Requirements, Architecture, implementation, validation, and linked documentation. Use when a change spans product behavior, design, code, tests, or project docs.
---

# Dev Workflow

Coordinate the repository's standard development and maintenance workflow.

## Workflow

1. **Clarify intent.** Confirm scope with the user. Use `$requirement` and
   `$interactive-docs-refinement` to refine the active Requirement progressively and resolve
   uncertain or undecided points.
2. **Design from Architecture.** Read the relevant Architecture and linked implementation documents
   before proposing a solution. Reason from product models, workflows, and constraints; do not solve
   a surface symptom from isolated code fragments. Ensure the proposal satisfies model
   responsibilities and design constraints. If it requires an Architecture change, state the
   affected models, constraints, rationale, and scope in the proposal and update Architecture with
   `$write-architecture-docs` when authorized.
3. **Implement the approved plan.** Follow the implementation workflow below. If implementation
   reveals that the plan no longer fits, stop, report the evidence, and revise the Requirement or
   plan before continuing; do not silently force a local design decision.
4. **Keep design and implementation aligned.** Update Architecture promptly when implementation
   reveals or changes a key model, abstraction, or constraint. Link Architecture, Requirements,
   Issues, and implementation documents or code where links improve the project knowledge network;
   keep the link structure small enough to maintain.
5. **Validate and hand off.** Validate the Requirement, Architecture, implementation, tests, links,
   and their consistency before reporting completion.

## Requirement Change Authorization

When the user requests a change directly in a non-Requirement document or artifact, including code,
first identify the active Requirement governing it, or use `$requirement` to establish one. Integrate
and clarify the change there before implementation; do not implement directly from the artifact
request.

When the user changes an active Requirement, integrate the change into the Requirement first. Do not
automatically implement it unless the user gives explicit authorization, such as "implement this
change now" or "automatically implement my changes from now on."

## Implementation

Use this workflow when an active Requirement authorizes implementation:

1. Confirm that the Requirement contains the current implementation plan and that the user has
   explicitly authorized the requested scope. When creating or revising the plan, record each
   phase's bounded scope, concrete outputs, and validation/review checkpoint in the Requirement;
   keep a phase small enough to remain human-reviewable. A `planned` status records readiness and
   plan state; it does not authorize code, tests, Architecture changes, or other artifact changes
   by itself.
2. Before editing, read the relevant Architecture, Requirement sections, and existing code. Treat
   each phase as part of one coherent product design. A phase may establish foundations needed by
   later phases, but it must not prematurely freeze details that are strongly coupled to a later
   model or workflow.
3. When a later-stage detail is intentionally undecided, preserve the design space with a small
   explicit placeholder, such as Python `pass`, and a concise comment describing what later phase
   must determine. Do not invent a partial contract merely to make the current phase appear
   complete. Keep the placeholder visible and reachable from the relevant Requirement or phase
   record.
4. Implement only the current phase's settled behavior. If a local implementation choice affects
   later phases, record the assumption, alternatives rejected, and expected follow-up instead of
   scattering an implicit contract across helpers or tests.
5. At phase completion, validate the implemented behavior and briefly record in the Requirement
   overview: what was implemented, what remains intentionally deferred, which placeholders or
   assumptions were introduced, and what the next phase must revisit. Keep later phases `pending`
   until their own scope is authorized.
6. Stop for user review after the phase. Multiple phases in one pass require explicit authorization
   for that broader scope. Do not mark the Requirement `implemented` until all planned phases and
   their validation evidence are complete.
