---
name: issue
description: Create and maintain Issue records in docs/issues. Use when the user explicitly asks to define, record, refine, or track an issue, or to update an existing Issue.
---

# Issue

Create and maintain Issues.

## Workflow

1. Confirm the user's explicit recording authorization and scope. Do not create an Issue from a
   report or review alone.
2. Inspect `docs/issues/` before choosing the next zero-padded number. Store an Issue as
   `NNNN-<slug>.md`.
3. Keep each record focused: title, status, observed problem, impact, evidence, expected behavior,
   and disposition. Use one visible lowercase status: `open`, `confirmed`, `resolved`, or `ignored`;
   change status only on explicit user direction.
4. Writing or revising an Issue does not authorize code, design, tests, or Skills; obtain explicit
   implementation authorization separately.
5. Validate numbering, links, status, evidence, and consistency with current repository files. Do
   not invent facts or history.
