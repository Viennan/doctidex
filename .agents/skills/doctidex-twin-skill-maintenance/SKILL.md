---
name: doctidex-twin-skill-maintenance
description: Maintain Twin Skills under skills/ when adding, removing, or renaming docs/user/*.md; changing skills/doctidex-git/SKILL.md or its references/; or rebuilding _skill_data for packaging.
---

# Doctidex Twin Skill Maintenance

This is a guide, not a script. It owns maintenance of the Twin Skills under `skills/`, especially
`skills/doctidex-git`. It does not own the repository-internal `.agents/skills/` scaffolding.

## Scope

A Twin Skill mirrors the flat [user documentation](../../../docs/user) and the `doctidex-git` CLI. Keep the three views
aligned: `docs/user/`, `skills/doctidex-git/`, and the packaged `whero.doctidex._skill_data` copy.

## SKILL.md narrative contract

The Twin Skill's `SKILL.md` is the first capability view an external agent reads. Maintain it from that perspective:

- Review from a fresh external agent's point of view. Every fact the agent needs must be reachable from `SKILL.md`
  and its `references/` alone, without browsing this development repository.
- Open with a concise, complete capability space: what the CLI can do and which capabilities are most distinctive.
  Do not omit a core capability to save space.
- Use heuristic, permissive language. Describe capabilities and useful compositions without implying a fixed command
  sequence or an unsupported restriction.
- Treat scenarios as reasoning examples. Each one should show a capability, suggest how it composes with others, and
  let the agent generalize new workflows. Do not present the listed scenarios as the only supported paths.
- Keep detailed syntax, errors, edge cases, and exhaustive rules in `docs/user/`; link to the owning reference from the
  skill.

Use these checks as examples:

- **Good:** "Initialize a workspace when needed; `init` and `validate --only-model-structure` form a common check
  pair, not a mandatory global order."
- **Bad:** "Always run `init`, then `import install`, then `import ref` before doing anything else."
- **Good:** "Get the wheel URL from https://github.com/Viennan/doctidex/releases."
- **Bad:** "Get the wheel URL from this repository's release list."

## Execution rules

- `skills/doctidex-git/references/` mirrors the flat `docs/user/*.md` files through development-time symbolic links.
- When a user-document file is added, removed, or renamed, update the matching reference link in the same change.
- When the CLI changes in a way that affects agent behavior, especially a new core capability, a boundary-expanding
  behavior, or a breaking change, update the affected `SKILL.md` scenarios and mandatory rules in the same change.
- Follow the [SKILL.md narrative contract](#skillmd-narrative-contract).
- Keep the frontmatter `description` concise and scoped to the Twin Skill identity and the product promise.
- Keep a top-level `doctidex.version` field equal to the co-released CLI version.
- When the CLI version changes, update `doctidex.version` in the same change as the Python package version.
- Run [scripts/validate-user-doc-links.py](../../../scripts/validate-user-doc-links.py) before publication.
- Materialize package data so `src/python/whero/doctidex/_skill_data/` contains real files, not symlinks. The generated
  directory is ignored by Git.

## Review

Verify that:

- every flat `docs/user/*.md` has a matching `skills/doctidex-git/references/` entry;
- `SKILL.md` has a `doctidex.version` field equal to `whero.doctidex.__version__`;
- `SKILL.md` links resolve;
- the user-document link validator passes;
- `_skill_data` is materialized when packaging changed;
- rules here do not duplicate [doctidex-doc-maintenance](../doctidex-doc-maintenance/SKILL.md).
