# Issue Note: Add Twin Skill support to doctidex-git

Status: implemented

## Problem

The `doctidex-git` CLI had most of its runtime capability but no canonical, version-matched operating contract for an
agent. Agents independently re-derived the workflows for installing external repositories, creating Refs, writing
cross-boundary Markdown links, and using editable Worktrees. User documentation existed but was not packaged as a skill,
and there was no supported way to install that skill into another repository's `.agents/skills` directory.

## Decision

The product ships a top-level `skills/` output artifact. `skills/doctidex-git/SKILL.md` is an agent-facing usage guide
covering prerequisites, common Git-repository scenarios, and mandatory document-access rules. Its `references/`
directory contains the flat user documentation.

`doctidex-git skills install --path <DEST>` installs the bundled Twin Skill into `<DEST>/doctidex-git/`, replacing only that
subtree. The command is user-level: it does not resolve a Git root, open a work model, or use Installation context.
Success returns `skills` and `install-path`; handleable failures use `skills.install.target.unavailable` and
`skills.install.unavailable`.

The Python package resolves the skill from the repository-root `skills/` tree during development and from
`whero.doctidex._skill_data` in an installed distribution. A candidate root is accepted only when it contains
`doctidex-git/SKILL.md`, which prevents an unrelated `skills/` directory from being mistaken for the bundled tree.

The build materializes development-time reference symlinks and copies `skills/doctidex-git/` into
`src/python/whero/doctidex/_skill_data/doctidex-git/` through a setuptools `build_py` subclass. `pyproject.toml`
declares `_skill_data/**/*` as package data, and `.gitignore` excludes the generated directory.

The user-document link and self-containment contract is owned by
[the implemented process issue](../process/2026-08-31-add-user-doc-link-validation-and-structure-rules.md). Packaging
runs `scripts/validate-user-doc-links.py` against `docs/user/` and `skills/doctidex-git/references/` and aborts on a
non-zero result.

The architecture overview records `skills/` as a product output, `skills install` in the command inventory, and
[skills.py](../../../../../src/python/whero/doctidex/skills.py) as the skill resolution and installation implementation.
The user guide documents the command in [skills.md](../../../../user/skills.md).

## Verification

- `ruff check` passes for `skills.py`, the CLI, setup, and the skills tests.
- `src/python/tests/test_skills.py` and `src/python/tests/test_skills_cli.py` pass.
- The full default test suite passes.
- A built wheel contains real files under `whero/doctidex/_skill_data/doctidex-git/`, not symlinks.
- `scripts/validate-user-doc-links.py --docs-root docs/user --references-root skills/doctidex-git/references` passes.
- `git diff --check` passes.

## Alternatives considered

**Publish skills only as documentation in a separate repository or by manual copy.**
Rejected: it does not tie the skill to the CLI release, so the agent workflow and command surface can drift and there is
no one install path.

**Use the repository-internal `.agents/skills/` tree as the Twin Skill.**
Rejected: that tree is development scaffolding for this repository, not a build output, and is not packaged with the
CLI.

**Keep symbolic links in the published skill.**
Rejected: the installed skill would depend on the source repository or publishing host and would break when copied to
another machine or repository.

**Derive `SKILL.md` automatically from the user reference documents at build time.**
Rejected: the agent workflow is a distinct orientation over the same facts and needs its own sequencing and guardrails.

**Install skill files without bundling them into the Python package.**
Rejected: a wheel-installed `doctidex-git` would have no skill source to copy, defeating version alignment.

**Use setuptools `data-files` outside the package instead of package data.**
Rejected: package data gives `skills install` a deterministic `importlib.resources` path independent of the install
prefix and virtualenv layout.

**Accept any directory at the computed source path without checking for `doctidex-git/SKILL.md`.**
Rejected: an unrelated `skills/` directory could shadow the packaged skill and cause installation to fail.

## Consequences

Agents now receive a version-matched, installable operating contract through `doctidex-git skills install`. User
documentation remains the authoritative reference, and the packaging step keeps its links reachable and self-contained.

The trade-off is additional packaging surface: the build materializes symlinks, package data is generated under
`_skill_data`, and that directory is ignored by Git. The resolver's marker check prevents false source-tree detection
but requires the bundled tree to retain `doctidex-git/SKILL.md`.

## Related

- [Add repository search guidance to the doctidex-git Twin Skill](2026-08-31-add-repository-search-guidance-to-doctidex-git-twin-skill.md)
- [Standardize doctidex-git Twin Skill and CLI version alignment](2026-09-01-standardize-doctidex-git-twin-skill-cli-version-alignment.md)
- [Restate the doctidex-git Twin Skill narrative contract](2026-09-01-restate-doctidex-git-twin-skill-narrative-contract.md)
