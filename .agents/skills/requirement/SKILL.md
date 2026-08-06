---
name: requirement
description: Create and maintain Requirement records in docs/requirements. Use when the user explicitly asks to define, record, refine, or track a requirement, or to update an existing Requirement.
---

# Requirement

Create and maintain Requirements.

## Workflow

1. Confirm the user's explicit recording intent and scope. Do not create a Requirement for ordinary
   documentation or infer one from current behavior.
2. Proactively use `$interactive-docs-refinement` to surface and resolve uncertain or undecided
   points with the user before finalizing the Requirement.
3. Inspect `docs/requirements/` before choosing the next zero-padded number. Store a normal
   Requirement as `NNNN-<slug>.md`. For a large Requirement, use
   `NNNN-<slug>/overview.md` with child files, and keep every child reachable from the overview.
4. Keep each record focused: title, status, intent, affected surfaces, decisions, dependencies,
   and acceptance criteria. Use one visible lowercase status: `draft`, `implemented`, or
   `approved`; only explicit user approval permits `approved`.
5. Write or revise the Requirement before modifying artifacts it governs. A Requirement request
   alone does not authorize code, design, tests, or Skills; obtain explicit implementation
   authorization.
6. Validate numbering, links, status, acceptance criteria, and consistency with current repository
   files. Do not invent facts or history.
