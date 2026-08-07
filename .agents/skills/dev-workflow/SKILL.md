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
3. **Implement the approved plan.** Obtain explicit implementation authorization, then follow the
   approved plan without silently changing it. If blocked or if the plan no longer fits, stop,
   report the evidence to the user, and discuss the revision before continuing.
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
