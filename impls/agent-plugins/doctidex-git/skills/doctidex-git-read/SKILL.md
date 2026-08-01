---
name: doctidex-git-read
description: Navigate and investigate doctidex directory trees in a main repository or installed external repository while preserving native file and search tools. Use for progressive index/link reading, boundary or unsafe interpretation, locating relevant content, and diagnosing an inaccessible or broken symlink with the installed link parser; do not automatically install, restore, or modify external content.
---

# Read a doctidex Tree

If `$doctidex-git-overview` has not already been read for this task, read it once and return here.

Start at the selected root `index.md`, follow only the entries relevant to the question, and enter a
child `index.md` when it takes over responsibility. Use native search and file tools freely; an
index is a progressive map, not an access-control list. Treat `atomic-indexing` content as one
indexed unit while retaining native access to its files. Treat `unsafe` as a protocol-content
exception, not a trust verdict or read prohibition.

Resolve `/path` Markdown links from the current doctidex root and relative links from their source
document. Do not interpret `/` as the host filesystem root or resolve `..` beyond the doctidex root.
Cross-boundary and safe-to-unsafe links may have an adjacent structured doctidex annotation; retain
it and use it to understand the lexical boundary. Do not rewrite annotations merely to read.

## Diagnose an Inaccessible Symlink

Use native file access first. In either the main tree or an installed doctidex repository, if a
symlink cannot be entered because its target is missing or inaccessible, run the parser on the
symlink itself:

```text
doctidex-git external link-parse PATH [--root ROOT] --json
```

`PATH` is a cwd-relative or absolute existing readable directory or symlink; a broken symlink itself
is valid even though its target does not exist. Other nonexistent paths and ordinary files are
rejected. The command is offline, read-only, single-result, and has no dry-run, apply, limit, or
cursor. Omit `--root` to recover the unique outer managed owner from `PATH`, or otherwise the unique
containing root. If supplied, `ROOT` must be the exact outer owner; an installed repository's inner
content root is not the owner and produces `root_mismatch`.

Read these fields before deciding:

- `managed`, `mapping_origin` (`owner_root`, `installed_repository`, or null), `created_by`, `root`,
  `content_root`, `input_path`, `input_kind`, and `presentation_path` identify the mapping context.
- `install_id`, `install_path`, `install_role`, `dependency_of`, and
  `dependency_parent_install_id` identify the current outer install relationship when one exists.
- `source_url`, `source_relation`, `revision_selector`, `default_branch`, `resolved_commit`, and
  `repository_relative_path` preserve source and fixed-position facts.
- `target_state`, `working_path`, `safe_state`, and `responsible_index` determine the next read.

`created_by` is `install`, `link`, or null. `source_relation` is `host_repository`, `other`,
`unknown`, or null and does not grant write authority. `safe_state` is `safe`, `unsafe`, or null and
describes presentation classification, not trust. For `dependency_not_installed`, `root`,
`source_url`, full `resolved_commit`, and `dependency_parent_install_id` are present and are the
exact values for optional dependency install; target install/path/role and `working_path` are null.

Act on `target_state`:

- `available`: continue native reading at `working_path`, not through a still-broken inner symlink.
- `owner_install_missing`: the durable owner-root link is intact but its direct install is missing.
  Load `$doctidex-git-maintenance` once if not already loaded and use restore with the returned
  install ID; do not rewrite the link.
- `dependency_not_installed`: this is a valid portable link in an installed repository whose
  dependency is not expanded in the outer owner. Report its exact source and commit. Only if the
  task calls for it, load Maintenance once and install with `source_url`,
  `--commit resolved_commit`, and `--dependency-of dependency_parent_install_id`. Never re-resolve
  the returned branch/tag provenance.
- `not_applicable`: return to native filesystem/Git diagnosis; unmanaged is not product damage.
- `unavailable`: preserve the path and follow the `mapping_damaged` finding actions. Do not guess a
  source, suffix, or owner.

This Skill never installs or restores by itself, modifies a broken symlink, validates the tree, or
creates managed state inside installed content. After optional Maintenance finishes, rerun the same
link-parse command and continue from the outer `working_path`. If Maintenance was already loaded,
resume it without reopening either Skill.
