---
name: doctidex-issue-maintenance
description: Maintain Issue Notes under docs/dev/issues by creating, updating, archiving, consolidating, and moving them.
---

# Doctidex Issue Maintenance

This is a guide, not a script. It owns the execution rules for Issue Notes under [docs/dev/issues](../../../docs/dev/issues/README.md). Read that README for layout, classification, and in-file format. Trigger conditions are owned by [docs/dev/issues/AGENTS.md](../../../docs/dev/issues/AGENTS.md).

## Writing and updating

- Update the Issue Note that already owns the decision; do not create a duplicate.
- A purely mechanical or local edit with no change to behavior, contracts, structure, process, or rationale is exempt.
- Do not edit an Issue Note into a *different decision*; supersede it with a new note and keep both notes cross-linked unless fully consolidated later.
- Editing an `implemented/` Issue Note to track where its existing decision lives is required, not forbidden.

## Archiving

The archive path is `archived/{class}/yyyy-mm-dd-topic-title.md`; `implemented` is absent because only implemented notes can enter.

An archival change moves the complete English/Chinese/sidecar triplet, retains `Status: implemented`, inserts `Archived: YYYY-MM-DD` below that status in both language files, re-records the sidecar, and repairs or deletes inbound links. These are the only permitted content changes during archival.

Once sealed, an archived triplet is permanently frozen. Do not edit, translate, reformat, update, move, or delete it, and do not treat it as authority for current behavior. Archived sources are skipped by documentation checks, including their outbound links; active prose may link into an archived note when it intentionally cites history. Archived notes keep the closed class tree, complete triplets, archive metadata, sidecar hashes, and an append-only frozen-content manifest.

## Consolidation

Before deletion, preserve every unique rationale, alternative, consequence, required verification, and named coverage gap; repair every inbound link; and delete the Chinese counterpart and consistency record in the same change. Partial supersession does not qualify: keep both notes cross-linked and update every fact that remains current. Consolidation must not rewrite the old file into its opposite or rely on git history as the only copy of rationale.

The removal owner preserves the original motivation, why it no longer justified the feature, alternatives to full removal, the capability given up, conditions for reintroduction, and verification of complete absence. Obsolete implementation inventories and tests that only verified the deleted behavior are not current verification evidence. Removing one transport, default, implementation, or presentation is partial supersession, as is any surviving durable data or compatibility handling.

## Moving between lifecycles

Moving a file means updating the `Status:` line and re-satisfying that folder's skeleton in the same change; otherwise the move is invalid.

- `proposed/` → `developing/` expands `## Proposal` into `## Design`, `## Implementation plan`, and `## Progress`.
- `developing/` → `implemented/` rewrites the design and progress into a present-tense `## Decision`, folds the completed implementation into `## Consequences` (or a present-tense `## Testing`/`## Verification` section for what now pins the behavior), and drops in-flight plans.
- When moving `developing/` → `implemented/`, sync all affected documents under `docs/` in the same change using [doctidex-doc-maintenance](../doctidex-doc-maintenance/SKILL.md).
- `proposed/` → `rejected/` only adds the reason to the `Status:` line and freezes the file.

## Adding a class

Adding a class requires updating the classification table in the [Issue Note README](../../../docs/dev/issues/README.md#classification) before introducing that folder.

## Review

After maintaining Issue Notes, verify that:

- No centralized `INDEX.md` was introduced; search or browse the tree directly.
- Cross-references use relative Markdown links, never bare prose or numbers.
- Prose is calibrated using [doctidex-prose-standard](../doctidex-prose-standard/SKILL.md).
