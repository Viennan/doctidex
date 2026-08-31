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

## Execution rules

- `skills/doctidex-git/references/` mirrors the flat `docs/user/*.md` files through development-time symbolic links.
- When a user-document file is added, removed, or renamed, update the matching reference link in the same change.
- When the CLI changes in a way that affects agent behavior, especially a new core capability, a boundary-expanding
  behavior, or a breaking change, update the affected `SKILL.md` scenarios and mandatory rules in the same change.
- Keep `SKILL.md` an agent-facing usage guide:
  - state prerequisites;
  - require `overview.md` before use;
  - treat `references/` as authoritative;
  - give common Git-repository scenarios with command snippets, not an exhaustive command list;
  - state mandatory document-access rules;
  - use heuristic tone except for hard requirements;
  - keep the frontmatter `description` concrete: briefly state the vision that Git repositories become interoperable
    knowledge nodes, then name the workflows `doctidex-git` takes over under that vision.
- Run [scripts/validate-user-doc-links.py](../../../scripts/validate-user-doc-links.py) before publication.
- Materialize package data so `src/python/whero/doctidex/_skill_data/` contains real files, not symlinks. The generated
  directory is ignored by Git.

## Review

Verify that:

- every flat `docs/user/*.md` has a matching `skills/doctidex-git/references/` entry;
- `SKILL.md` links resolve;
- the user-document link validator passes;
- `_skill_data` is materialized when packaging changed;
- rules here do not duplicate [doctidex-doc-maintenance](../doctidex-doc-maintenance/SKILL.md).
