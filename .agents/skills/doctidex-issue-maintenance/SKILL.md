---
name: doctidex-issue-maintenance
description: Maintain Issue Notes under docs/dev/issues by creating, updating, moving them between lifecycles, archiving, and consolidating them.
---

# Doctidex Issue Maintenance

This is a guide, not a script. It owns the execution rules for Issue Notes under [docs/dev/issues](../../../docs/dev/issues/README.md). Read that README for layout, classification, and in-file format. Trigger conditions are owned by [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md).

## Writing and updating

- Update the Issue Note that already owns the decision; do not create a duplicate.
- A purely mechanical or local edit with no change to behavior, contracts, structure, process, or rationale is exempt.
- Do not edit an Issue Note into a *different decision*; supersede it with a new note and keep both notes cross-linked unless fully consolidated later.
- Editing an `implemented/` Issue Note to track where its existing decision lives is required, not forbidden.

## Linking and dependencies

Consider creating bidirectional Markdown links only when Issue Notes have a strong dependency or a direct design relationship; do not link merely related issues. A parent Issue may create multiple child Issues; add bidirectional parent-child links only when a child's design directly depends on the parent.

Use links to make context search easier, but do not rely on links alone: also search active issues by content and decision impact.

Maintain bidirectionally linked issues together throughout their lifecycles. When one linked issue changes:

- sync affected facts and links in the linked issues;
- during consolidation, preserve and repair the relationship in the surviving note;
- during archiving, repair or remove inbound links and update any dependent active issue.

## Archiving

The archive path is `archived/{class}/yyyy-mm-dd-topic-title.md`; `implemented` is absent because only implemented notes can enter.

An archival change moves the complete English/Chinese/sidecar triplet, retains `Status: implemented`, inserts `Archived: YYYY-MM-DD` below that status in both language files, re-records the sidecar, and repairs or deletes inbound links. These are the only permitted content changes during archival.

Once sealed, an archived triplet is permanently frozen. Do not edit, translate, reformat, update, move, or delete it, and do not treat it as authority for current behavior. Archived sources are skipped by documentation checks, including their outbound links; active prose may link into an archived note when it intentionally cites history. Archived notes keep the closed class tree, complete triplets, archive metadata, sidecar hashes, and an append-only frozen-content manifest.

## Consolidation

Before deletion, preserve every unique rationale, alternative, consequence, required verification, and named coverage gap; repair every inbound link; and delete the Chinese counterpart and consistency record in the same change. Partial supersession does not qualify: keep both notes cross-linked and update every fact that remains current. Consolidation must not rewrite the old file into its opposite or rely on git history as the only copy of rationale.

The removal owner preserves the original motivation, why it no longer justified the feature, alternatives to full removal, the capability given up, conditions for reintroduction, and verification of complete absence. Obsolete implementation inventories and tests that only verified the deleted behavior are not current verification evidence. Removing one transport, default, implementation, or presentation is partial supersession, as is any surviving durable data or compatibility handling.

## Moving between lifecycles

Moving a file means updating the `Status:` line and re-satisfying the target lifecycle's skeleton in the same change; otherwise the move is invalid. The `implemented/` → `archived/` move follows [Archiving](#archiving), not this list.

### `proposed/` → `developing/`

- Set `Status: developing`.
- Expand `## Proposal` into `## Design`, `## Implementation plan`, and `## Progress`.
- Bring the rest of the body to the `developing/` skeleton; keep `## Problem` and `## Alternatives considered`.

### `developing/` → `implemented/`

- Set `Status: implemented`.
- Rewrite the design and progress into a present-tense `## Decision`.
- Fold the completed implementation into `## Consequences`, or into a present-tense `## Testing`/`## Verification` section when that section now pins the behavior.
- Drop in-flight plans.
- In the same change, sync all affected documents under `docs/` using [doctidex-doc-maintenance](../doctidex-doc-maintenance/SKILL.md).
- Run the supersession hook: search active issues for candidates covering the same decision or mechanism. For `implemented/` candidates, classify any full or partial supersession, archive every qualifying implemented triplet in the same change, and keep partial supersessions active and cross-linked. For `developing/` or `proposed/` candidates, state the reason by default and ask the user before acting.

### `proposed/` → `rejected/`

- Set `Status: rejected — <why, in one line>`.
- Freeze the file as the proposal; make no other content changes.

## Adding a class

Adding a class requires updating the classification table in the [Issue Note README](../../../docs/dev/issues/README.md#classification) before introducing that folder.

## Review

After maintaining Issue Notes, verify that:

- No centralized `INDEX.md` was introduced; search or browse the tree directly.
- Cross-references use relative Markdown links, never bare prose or numbers.
- Bidirectional links are present where a strong dependency or direct design relationship matters, and linked issues were updated across the lifecycle change.
- Prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
