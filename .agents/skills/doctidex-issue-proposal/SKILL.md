---
name: doctidex-issue-proposal
description: Develop or refine a proposed Issue Note in docs/dev/issues; keep the proposal focused on problem, impact, and approach while treating user input as discussion rather than implementation.
---

# Doctidex Issue Proposal

This is a guide, not a script. It owns how to create and refine an Issue Note in `proposed/`. Read the [Issue Note README](../../../docs/dev/issues/README.md) for the proposed skeleton and [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md) for routing and triggers.

## Authorization boundary

A proposed Issue Note does not authorize substantive, non-trivial repository changes. Do not change code, documentation outside the Issue Note, or other repository state while the issue is only proposed.

By default, treat user comments, quotes, or instructions about code or documents as discussion for the proposal, not as commands to edit those files. When a user quotes text or code and says how it should behave, use that information to improve the proposal; do not apply it to the repository.

To perform substantive changes, the issue must leave `proposed/` and receive explicit authorization for that change.

## Purpose

Keep proposal work focused on:

- the problem to solve;
- the likely impact;
- a solution approach.

Do not move into detailed design or implementation planning while the issue remains `proposed/`; those phases use [doctidex-issue-design](../doctidex-issue-design/SKILL.md) and [doctidex-issue-impl](../doctidex-issue-impl/SKILL.md).

## Workflow

- Match the user input to an active proposed Issue Note using the routing rule in [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md). When no matching proposed Issue Note exists, apply the triggers in that `AGENTS.md` before creating one; use [doctidex-issue-maintenance](../doctidex-issue-maintenance/SKILL.md) to create a new proposal only when the input warrants it, such as a non-trivial change.
- Search active issues for related or decision-affecting context before updating the proposal.
- Read relevant documentation and code only to understand the problem and impact; do not edit them.
- Update `## Problem`, `## Proposal`, `## Alternatives considered`, `## Acceptance criteria`, and `## Risks` as understanding improves.

## Review

After refining the proposal, verify that:

- the problem, impact, and solution approach are stated;
- no substantive repository change was made from the proposed state;
- user quotes and instructions were treated as discussion rather than edits;
- related active issues were searched and their links remain valid;
- the prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
