# Issue Note: Restate the doctidex-git Twin Skill narrative contract

Status: implemented

## Problem

The rules that controlled how `skills/doctidex-git/SKILL.md` was written were embedded inside
`.agents/skills/doctidex-twin-skill-maintenance/SKILL.md` as a short bullet list. That list did not express the
Twin Skill's primary purpose clearly enough: in a small amount of space, show a fresh agent what the CLI can do,
what it needs before use, and which rules are mandatory, without requiring the agent to browse this development
repository beyond `SKILL.md` and `references/`.

The Twin Skill mixed capability overview with detailed scenarios and hard wording. It could be read as a fixed
sequence rather than an invitation to reason from the CLI's capability space.

## Decision

`.agents/skills/doctidex-twin-skill-maintenance/SKILL.md` now has a dedicated `## SKILL.md narrative contract`
section. That section owns the rules for reviewing and writing the Twin Skill:

- review from a fresh external agent's perspective, using only `SKILL.md` and `references/`;
- open with a concise and complete capability space, without omitting core capabilities;
- use heuristic, permissive language and avoid inventing fixed sequences or unsupported restrictions;
- treat scenarios as reasoning examples that invite new compositions;
- keep detailed syntax, errors, and edge cases in `docs/user/`, with links from the skill.

Discrimination examples show good and bad wording, including explicit release URLs versus the ambiguous phrase
"this repository".

`skills/doctidex-git/SKILL.md` is reorganized around the capability-first shape:

- `## Capability space` lists the command clusters and what they provide;
- `## Common scenarios` shows short examples and states that they are not the only supported workflows;
- `## Install and update`, `## Before you start`, and `## Rules you must follow` retain the operational contract.

The capability map includes Installation context as a distinctive `doctidex-git` capability.

## Verification

- `scripts/validate-version-alignment.py` passes.
- `scripts/validate-user-doc-links.py --docs-root docs/user --references-root skills/doctidex-git/references` passes.
- Every `references/` link in `skills/doctidex-git/SKILL.md` resolves.
- `git diff --check` passes.

## Alternatives considered

**Keep the narrative rules embedded in the general Twin Skill maintenance list.**
Rejected: the narrative contract is a distinct review lens and deserves its own section so the rules stay visible
when `SKILL.md` changes.

**Rewrite only the ambiguous installation wording and leave the previous scenario-heavy shape.**
Rejected: the problem was the overall narrative frame, not one phrase; keeping the previous shape would preserve the
fixed-sequence reading.

**Move the detailed command snippets entirely into `docs/user/`.**
Rejected: concise scenarios are useful as capability demonstrations and reasoning triggers, provided they link to the
owning reference.

## Consequences

The Twin Skill now gives a fresh agent a capability map before detailed guidance, states that scenarios are examples
rather than a fixed workflow, and keeps detailed command rules in `docs/user/`. The maintenance skill makes that
contract explicit and preserves Good/Bad cases for review.

The trade-off is that the Twin Skill is slightly more structured and explicit, and the maintenance skill now carries a
larger narrative-contract section. The user documentation remains the authoritative command detail.

## Related

- [Add Twin Skill support to doctidex-git](2026-08-31-add-agent-skill-support-to-doctidex-git.md)
- [Formalize doctidex-git Twin Skill maintenance in scaffolding](../process/2026-08-31-formalize-doctidex-git-twin-skill-maintenance.md)
- [Standardize doctidex-git Twin Skill and CLI version alignment](2026-09-01-standardize-doctidex-git-twin-skill-cli-version-alignment.md)
