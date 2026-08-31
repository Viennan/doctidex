# Issue Note: Add repository search guidance to the doctidex-git Twin Skill

Status: implemented

## Problem

The `doctidex-git` Twin Skill previously taught agents to discover Installations and Worktrees through the CLI:
`import query` for Installations and `worktree query` for Worktrees. Query is the authoritative way to resolve an
identity, restore state, and confirm exact selectors, but an agent that only needs to read files often had to run a
query first to learn a path it could already derive.

The physical layout was already highly searchable. Installations live under a selector-derived hierarchy, and
default Worktrees live under a parallel hierarchy:

```text
/.doctidex-git/imports/<domain>/<repository-path>/<branch|tag|commit>/<value>
/.doctidex-git/worktrees/<domain>/<repository-path>/<tree-name>
```

That layout was not stated as a user contract, and the Twin Skill did not tell an agent to use it.

## Decision

`doctidex-git` ships [layout.md](../../../../user/layout.md) as the reference for the stable managed directory
organization. It documents the selector-derived Installation layout:

```text
/.doctidex-git/imports/<domain>/<repository-path...>/<selector-kind>/<selector-value...>
```

and the default Worktree layout:

```text
/.doctidex-git/worktrees/<domain>/<repository-path...>/<tree-name...>
```

Branch and tag selector paths are symbolic links into the shared commit checkout at
`.../commit/<commit-hash>`; a direct commit Installation uses that commit checkout path itself. The document states
that the layout is for locating content, not a replacement for authoritative state.

[overview.md](../../../../user/overview.md#repository-layout-at-a-glance) links to the layout reference from its
illustration, while [import.md](../../../../user/import.md) and [worktree.md](../../../../user/worktree.md) point to
it from their path descriptions instead of repeating the full contract.

[SKILL.md](../../../../../skills/doctidex-git/SKILL.md) includes a short heuristic in "Before you start": treat
`/.doctidex-git/imports/` and `/.doctidex-git/worktrees/` as searchable directories, and search the derived path
directly when a domain, repository, or selector is already known. It does not prescribe a query-first or search-first
order.

The reference mirror `skills/doctidex-git/references/layout.md` symlinks to `docs/user/layout.md`, and the packaged
`whero.doctidex._skill_data` copy contains the file as a real file.

No CLI behavior, durable state, or path derivation changed.

## Verification

- `scripts/validate-user-doc-links.py` passes against `docs/user/` and `skills/doctidex-git/references/`.
- `src/python/tests/test_skills.py` and `src/python/tests/test_skills_cli.py` pass.
- The default test suite passes: 222 passed, 7 deselected.
- `src/python/whero/doctidex/_skill_data/doctidex-git/references/layout.md` is a real file, not a symlink.
- `git diff --check` passes.

## Alternatives considered

**Put the search hint only in the Twin Skill, without a user document.**
Rejected: `docs/user/` is the authoritative reference set that the Twin Skill mirrors, and a directory contract
belongs in user-facing documentation so humans and agents share one explanation.

**Add the layout explanation to the existing overview instead of a dedicated document.**
Rejected: the overview already carries the whole surface map. A dedicated layout document gives the contract one
stable home and keeps `overview.md` from absorbing more detail than a quick-start reader needs.

**Leave discovery entirely to `import query` and `worktree query`.**
Rejected: query remains correct for identity, state, exact paths, and Refs, but making it mandatory for every
read-only file lookup adds unnecessary commands and latency when the path is derivable.

**Encode a strict search-first workflow with query fallback in the Twin Skill.**
Rejected: that would overprescribe an order the agent does not need. The useful hint is that the directories are
searchable, mirroring the issue notes' "working inventory" guidance, not a sequence to follow.

**Expose the layout through a new CLI command or structured output.**
Rejected: the paths already exist and the information is static. A new command adds surface without changing what an
agent needs to search; documentation and skill guidance are the smaller change.

## Consequences

Agents can now derive Installation and default Worktree paths for direct filesystem search, reducing unnecessary
query calls when they already know the source and selector. The layout is a documented, stable contract shared by
user documentation and the Twin Skill.

The trade-off is that future path refactors must preserve the documented contract or update `layout.md`, the Twin
Skill, and the packaged reference in the same change. Branch and tag selector paths remain symlinks, so search
guidance must continue to say that the selector path resolves to the shared commit checkout.

## Related

- [Add Twin Skill support to doctidex-git](2026-08-31-add-agent-skill-support-to-doctidex-git.md)
- [Formalize doctidex-git Twin Skill maintenance in scaffolding](../process/2026-08-31-formalize-doctidex-git-twin-skill-maintenance.md)
- [Add commit selector prefix to Installation share paths](../architecture/2026-08-31-add-commit-prefix-to-installation-share-paths.md)
