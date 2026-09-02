# Issue Note: Add `--force` to the recommended pipx install command

Status: implemented

## Problem

`doctidex-git` releases are distributed as wheel assets in GitHub Releases. The current user guide and Twin Skill
recommend `pipx install <WHEEL-URL>`. When pipx already has a `doctidex-git` installation, `pipx install` does not
overwrite the existing version unless `--force` is supplied. Users following the current command can therefore appear
to install a release while silently keeping the previous CLI.

The affected instruction appears in `docs/user/overview.md` and `skills/doctidex-git/SKILL.md`. The Twin Skill's
`references/overview.md` is a symlink to `docs/user/overview.md`, so the same user-guide text reaches the packaged
Twin Skill through that link.

## Decision

The recommended pipx install command is now `pipx install --force <WHEEL-URL>`. The `--force` flag is included in the
default command, not only in a separate update note.

The change is documentation-only and affects:

- `docs/user/overview.md`;
- `skills/doctidex-git/SKILL.md`;
- the Twin Skill reference symlink `skills/doctidex-git/references/overview.md` implicitly, because it points at the
  user-guide file.

The packaged `src/python/whero/doctidex/_skill_data/` copy was materialized from the updated Twin Skill.

## Testing

`scripts/validate-user-doc-links.py` passes after the documentation change.

## Consequences

Users who already have a `doctidex-git` pipx installation can now follow the same documented command for both first
install and update, and the updated wheel asset replaces the previous installation instead of leaving it in place.
The trade-off is that the documented command is slightly more aggressive on every install; this is acceptable because
releases are versioned wheel assets and the existing update guidance already expects replacement.

## Alternatives considered

**Leave the default command unchanged and add a separate upgrade note.**
Rejected: users already follow the default command; a separate note is easy to miss and leaves the documented update
path incorrect.

**Recommend `pipx reinstall` instead of adding `--force`.**
Rejected: `pipx install --force` covers both first installs and updates with one command, which matches the existing
single recommended install path.
