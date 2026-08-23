---
name: doctidex-doc-maintenance
description: Maintain Doctidex documentation by document type, including common rules and type-specific requirements. Use when writing, reorganizing, or reviewing docs under docs/, and when a non-trivial repository change, an issue being implemented.
---

# Doctidex Doc Maintenance

This is a guide, not a script. It owns execution rules for documents under [docs/](../../../docs/AGENTS.md). Read that AGENTS.md for directory organization and responsibility boundaries.

## Common rules

A document's subject and tree position fix its scope: describe its own subject at appropriate detail and direct children only by purpose, responsibility, and high-level behavior; link to the owning descendant for lower-level detail. Document type does not widen that scope. A reference may be exhaustive only about its own subject. Testing mechanisms, fixtures, and harnesses belong at the lowest owning level; higher documents link there.

Documentation must stay consistent with non-trivial repository changes. When an Issue Note becomes implemented, update the affected documentation in the same change or as a coordinated follow-up.

Keep each concept and other information in one home. Reference it with a path-plus-fragment link; never use bare filenames or issue numbers.

Classify every in-scope document as a tutorial or reference. Tutorials follow an ordered path to an outcome and introduce only what each step needs. References define a lookup scope and current behavior without a teaching sequence. Separate substantial tutorial and reference content; label a section when either part is small.

Before writing a tutorial, privately classify the reader's starting knowledge and each concept as beginner, intermediate, or advanced. Establish prerequisites before dependent concepts, increase difficulty gradually, and move unnecessary advanced material to a later tutorial or reference.

Author in this order: locate the document in the tree; set its permitted detail; choose tutorial or reference; for a tutorial, order concepts by prerequisite and difficulty; relocate descendant-owned detail; replace lower-level explanations with links to their owners.

Use [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md) to calibrate prose wording.

## User documentation

- Keep all user-surface information under `docs/user/`.
- Provide overview documents with prerequisites and hot-using paths.
- Provide detailed per-command-cluster reference manuals with complete input/output definitions and error handling.
- Make user documentation self-sufficient: a user should obtain enough usage information from `docs/user/` alone. Include brief architecture explanations and links when they help understanding, but require opening a link only for extreme detail.
- Ensure `docs/user/overview.md` covers every key usage behavior. If a behavior is still unexpected after a careful read of the overview, add it to the overview. The mental model established by the overview must hold across the entire user surface.

## Architecture documentation

- Keep architecture documentation under `docs/dev/architecture/`.
- Organize and write it using Domain Driven Design.
- Every design concept it involves must exist as a term.
- Treat architecture documents as the current-design authority; use the same DDD language in related design work.

## Glossary documentation

- Keep `docs/dev/glossary.md` synchronized with the architecture documents.
- Include terms defined in development and design documents.
- Do not include terms defined only in `AGENTS.md` or other agent-scaffolding documents.

## Cookbook documentation

- Keep cookbook documentation under `docs/dev/cookbook/`.
- Write step-by-step how-tos with numbered verification steps.
- Record recommended coordination patterns across modules, and best practices for implementing features on the existing base architecture.

## Issue documentation

- Issue documents are the authoritative home for design rationale; do not repeat that rationale in other documents.
- Non-issue documents state the current state, while Issue documents retain the trajectory that produced the current state.
- For developing-stage design, use [doctidex-issue-design](../doctidex-issue-design/SKILL.md).
- For implementation planning and execution, use [doctidex-issue-impl](../doctidex-issue-impl/SKILL.md).
- For lifecycle, archiving, consolidation, and moves, use [doctidex-issue-maintenance](../doctidex-issue-maintenance/SKILL.md).

## Review

After maintaining documents, verify that:

- each document stays within its subject and tree scope;
- tutorials and references are not mixed without clear labels;
- every affected link resolves;
- the glossary contains every design concept defined in the architecture documents;
- non-trivial repository changes are reflected in the affected documents;
- no document contains outdated current-state content; issue history that preserves design trajectory is not treated as outdated;
- issue rationale is not duplicated in non-issue documents;
- prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
