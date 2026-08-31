# Issue Note: Formalize doctidex-git Twin Skill maintenance in scaffolding

Status: implemented

## Problem

The shipped `skills/doctidex-git/` tree is a Twin Skill. Its `SKILL.md` and `references/` must stay aligned with
`docs/user/` and the `doctidex-git` CLI, and its package-data copy must be materialized before a release.
The maintenance duties were recorded in
[the feature decision](../feature/2026-08-31-add-agent-skill-support-to-doctidex-git.md) and
[the link-validation decision](./2026-08-31-add-user-doc-link-validation-and-structure-rules.md), but were not encoded
in repository scaffolding.

## Decision

`.agents/skills/doctidex-twin-skill-maintenance/SKILL.md` owns maintenance of the Twin Skills under `skills/`, not the
repository-internal `.agents/skills/` scaffolding. It records the execution rules and review checks for keeping each
Twin Skill aligned.

Concrete trigger conditions live at the trigger sites, not in the skill body. The root `AGENTS.md` directory diagram
records `skills/` as the Twin Skill output and routes these actions to the skill:

- adding, removing, or renaming `docs/user/*.md`;
- changing `skills/doctidex-git/SKILL.md` or its `references/`;
- changing CLI behavior that affects how an agent follows a Twin Skill, including a new core capability, a
  boundary-expanding behavior change, or a breaking change;
- rebuilding `_skill_data` for packaging.

`doctidex-doc-maintenance` points user-document additions, removals, renames, and changes that affect
`skills/doctidex-git/` back to the same skill. The skill itself states:

- `references/` mirrors the flat `docs/user/*.md` files through development-time symbolic links;
- `SKILL.md` is an agent-facing usage guide with prerequisites, mandatory `overview.md` reading, authoritative
  references, scenario-based command guidance, mandatory document-access rules, and a concrete frontmatter
  `description`;
- publication runs the link validator and materializes `_skill_data` as real files;
- the generated package-data directory remains ignored by Git.

## Verification

- The new skill, root `AGENTS.md`, and `doctidex-doc-maintenance` cross-references resolve.
- `git diff --check` passes.
- No duplicated maintenance rule remains between the new skill and `doctidex-doc-maintenance`.

## Alternatives considered

**Fold the rules into `doctidex-doc-maintenance`.**
Rejected: `skills/` is a product output, not a document under `docs/`; mixing the two widens that skill's scope.

**Leave the maintenance rules only in the implemented Issue Notes.**
Rejected: Issue Notes are not on the path an agent follows while editing `skills/` or `docs/user/`.

**Encode everything in the root `AGENTS.md`.**
Rejected: the root `AGENTS.md` is routing and orchestration; a detailed write-oriented maintenance workflow belongs in
a skill.

**Automate maintenance entirely and omit guidance.**
Rejected: symlink and package-data checks can be scripted, but deciding when `SKILL.md` scenarios change still requires
scoped guidance.

## Consequences

Twin Skill maintenance is now discoverable from the repository's agent scaffolding, with concrete triggers at the
places that need them and execution rules in a dedicated skill. The maintenance boundary is explicit: user documentation
ownership stays with `doctidex-doc-maintenance`, while Twin Skill output ownership lives in
`doctidex-twin-skill-maintenance`.

## Related

- [Add repository search guidance to the doctidex-git Twin Skill](../feature/2026-08-31-add-repository-search-guidance-to-doctidex-git-twin-skill.md)
