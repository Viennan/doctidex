---
name: requirement
description: Create and maintain Requirement records in docs/requirements. Use when the user explicitly asks to define, record, refine, or track a requirement, or to update an existing Requirement.
---

# Requirement

Create and maintain Requirements.

## Workflow

1. Confirm the user's explicit recording intent and scope. Do not create a Requirement for ordinary
   documentation or infer one from current behavior.
2. When the user asks to create a Requirement but provides an incomplete description, inspect
   historical records in `docs/requirements/` and use their established structure to create a
   document template. Do not over-infer the user's intent or turn assumptions into facts; leave
   the corresponding sections blank for the user to complete.
3. Proactively use `$interactive-docs-refinement` to surface and resolve uncertain or undecided
   points with the user before finalizing the Requirement. Preserve the blank or unresolved
   sections from an incomplete request until the user supplies the missing information.
4. Inspect `docs/requirements/` before choosing the next zero-padded number. Store a normal
   Requirement as `NNNN-<slug>.md`. For a large Requirement, use
   `NNNN-<slug>/overview.md` with child files, and keep every child reachable from the overview.
5. Keep each record focused: title, status, intent, affected surfaces, decisions, dependencies,
   and acceptance criteria. Use one visible lowercase status: `draft`, `planned`, `implemented`,
   or `approved`; only explicit user approval permits `approved`.
6. Write or revise the Requirement before modifying artifacts it governs. A Requirement request
   alone does not authorize code, design, tests, or Skills; obtain explicit implementation
   authorization.
7. Validate numbering, links, status, acceptance criteria, and consistency with current repository
   files. Do not invent facts or history.

## Status and Document Structure

The Requirement document is authoritative for its own record structure, status, scope, decisions,
dependencies, and acceptance criteria. For a large Requirement, `overview.md` is authoritative for
the overall record and navigation to its child Requirements; each child remains authoritative for
its own focused subject. Keep the links from the overview to every child current.

Use the statuses as follows:

- `draft`: the Requirement is incomplete or not yet approved for implementation.
- `approved`: the Requirement definition has explicit user approval; implementation still requires
  an implementation plan and explicit implementation authorization.
- `planned`: the phased implementation plan is recorded, but not all phases are complete; this status
  does not by itself authorize implementation.
- `implemented`: every planned phase is complete and validated.

Only explicit user approval permits the `approved` status. Set `implemented` only after every planned
outcome is complete and validated. The Requirement status does not replace explicit authorization
for implementation work.
