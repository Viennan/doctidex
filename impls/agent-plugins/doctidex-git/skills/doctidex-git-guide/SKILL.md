---
name: doctidex-git-guide
description: Establish the user-facing doctidex Git mental model, explain common CLI argument and output conventions, and route work to the correct specialized Skill. Use at the first doctidex-git task in a conversation, when terms or command behavior are unfamiliar, when a task spans multiple workflows, or before choosing setup, read, mount, maintain, workspace, validate, or review.
---

# Doctidex Git Guide

Use this Skill once to establish the shared model. Then load only the specialized Skill needed for
the task; do not reload this guide before every command.

## Prepare the CLI

Verify that `doctidex-git` is available in the active Python environment:

```bash
doctidex-git --help
```

If it is unavailable, install the public distribution in that environment:

```bash
python -m pip install whero-doctidex
```

Ask the user for access if installation requires unavailable network access or permissions.

## User Model

- **Doctidex root**: the directory whose `index.md` declares `doctidex.root: true`.
- **Root index**: that root `index.md`; it is the only file that declares mounts.
- **Responsible index**: the nearest applicable `index.md` for a local path. Use it as a
  recommended navigation and maintenance entry, not as a file-access gate.
- **Applicable log**: the nearest `log.md` that can provide change background. It is optional.
- **Host root**: the root from which the current CLI operation and mount namespace are selected.
- **Source root**: a complete external doctidex tree referenced by a mount.
- **Mount path**: a logical read-only path below `/.doctidex/mounts/` in the host root.
- **Declared revision**: exactly one Git commit, tag, or branch named in a mount declaration.
- **Effective commit**: the exact commit currently readable through that mount. First prepare
  selects it; later ordinary reading or prepare does not move it, and only explicit sync can select
  a different commit.
- **Maintenance root**: an independent writable source root returned for changing mounted content.
- **Semantic candidate**: an item that requires reading and agent judgment; it is not a confirmed
  defect.

Use native file, search, edit, and Git tools freely. `doctidex-git` supplies doctidex-aware facts
and workflows; it is not a replacement file reader and does not generate prose or decisions.

## Path Argument Types

Do not interchange these argument types:

| Placeholder | Required form | Example |
|---|---|---|
| `PATH` | A filesystem file or directory path. Relative values use the current working directory. | `docs/api.md`, `/work/project/docs` |
| `INTERNAL_PATH` | A `/`-prefixed path relative to a doctidex link root, not the filesystem root. | `/.doctidex/mounts/design/index.md` |
| `MOUNT_PATH` | An exact normalized strict child of `/.doctidex/mounts`; no `.` or `..`. | `/.doctidex/mounts/design` |
| `MAINTENANCE_ROOT` | The filesystem path returned by `maintenance open`; pass it back unchanged. | `/path/returned/by/maintenance-open` |

Mount and maintenance commands do not accept a host-root option. Run them with the current working
directory inside one unambiguous host root; prefer the exact root directory. Use
`doctidex-git context PATH --json` first when the root is uncertain.

For `context`, `inspect`, `init`, and `check`, omitting the optional filesystem `PATH` uses the
current working directory. For `changes`, omission selects the root from the current directory and
runs Git status for that root; an explicit path changes the Git status target but not the selected
root reported in the result. Prefer explicit paths in multi-root work.

## Common CLI Grammar

### Read command syntax

- Lowercase command words and `--options` are literal. Uppercase words such as `PATH`, `URL`, and
  `MOUNT_PATH` are placeholders to replace; do not type the placeholder itself.
- `[VALUE]` is optional, `A | B` lists alternatives, parentheses group a choice, and `...` means
  the preceding positional argument may be repeated. Do not type brackets, parentheses, or `...`.
- Global options `--json`, `--limit`, `--cursor`, and `--depth` may appear before or after the
  subcommand. The specialized Skill gives the exact positional and command-specific options.
- A missing required argument, unknown option, or mutually exclusive option combination exits 2
  and may use plain stderr even with `--json`; correct the invocation from the documented contract
  instead of retrying variants.

### Output and bounds

- Add `--json` when another agent step must inspect fields or errors. It may appear anywhere, but
  place it last consistently.
- Use `--limit N` to cap each returned list; default 100, accepted range 1..1000.
- If `collection` reports `truncated: true`, narrow `PATH` or the specific mount first. Otherwise
  pass its opaque `next_cursor` back with `--cursor TOKEN`.
- One cursor currently advances every top-level list in the payload. Do not assume it belongs to
  only `findings` or only `items`.
- Do not rely on `--depth`; the current CLI accepts 0..32 but does not use it to change results.

### Preview and apply

Commands that can change public files or mount selection use `--dry-run` and `--apply`. Always pass
one explicitly:

```bash
doctidex-git init PATH --dry-run --json
doctidex-git init PATH --apply --json
```

Omitting both currently behaves like a preview, but do not rely on that implicit default. Review a
dry-run before apply. `mount prepare` and `maintenance open/close` are explicit lifecycle actions
and do not have dry-run flags.

### Network behavior

- `context`, `inspect`, `resolve`, `init`, `mount list/add/remove`, `maintenance scope/status/
  handoff/close`, `changes`, and default `check` are offline at the user-content level.
- `mount prepare` may need network or credentials when the required commit is not locally
  available.
- `mount sync --dry-run` may fetch to discover a new commit even though it does not apply it.
- `check --online` may fetch current selectors but does not prepare or synchronize mounts.

Ask before enabling unavailable network access or credentials. Do not infer that a command is
offline merely because its output lacks a `network` field.

## Output Model

Read results in this order:

1. `status`: `ok`, `warning`, or `blocked` for the requested operation.
2. `result`: what completed or remains available.
3. Operation-specific fields such as root, mount state, commits, or changes.
4. `findings`: deterministic issues with actions.
5. `semantic_candidates`: prompts for agent judgment, not findings.
6. `collection`: truncation and continuation information.

For `check` and `maintenance handoff`, keep these domains independent:

- `protocol_structure`: `pass` or `fail` for deterministic protocol checks.
- `semantic_review`: `clear` or `required`; read the content before deciding.
- `plugin_readiness`: `ready`, `blocked`, or `not_applicable` for Git plugin prerequisites.

`status: warning` can still contain usable results. `status: blocked` means stop that operation,
report the preserved `result`, follow `findings[].actions`, and ask the user when `requires_user`
names a missing decision or authorization. Use JSON for blocked or batch results; human output may
show only the first finding.

Exit 0 means the command returned a usable non-blocked result, not that every validation domain
passed. Exit 1 means `protocol_structure: fail`; exit 2 means a blocked operation or CLI syntax
error; exit 130 means interruption. Inspect the JSON domains and status instead of relying only on
the exit code.

The field `changed` is operation-specific: init/add/remove use a path list, mount sync uses a
boolean commit comparison, and lifecycle commands may return an empty list despite changing mount
or maintenance state. Use `operation` before interpreting it.

## Choose a Specialized Skill

| User intent | Load next | Main result |
|---|---|---|
| Create, adopt, or repair a root | `$doctidex-git-setup` | Planned/applied root structure plus semantic follow-up. |
| Navigate, search, resolve links, or recover a required lazy mount | `$doctidex-git-read` | Reading context and a native-tool-readable path. |
| Add, remove, prepare, list, or synchronize Git mounts | `$doctidex-git-mount` | Mount declarations and explicit readable commit state. |
| Edit one local doctidex root | `$doctidex-git-maintain` | Content changes with index/log decisions and validation. |
| Change a mounted source or coordinate multiple roots | `$doctidex-git-workspace` | Independent writable roots and per-root handoff. |
| Check conformance, filters, links, or plugin readiness | `$doctidex-git-validate` | Separated structure, semantic, and readiness results. |
| Review results without modifying them | `$doctidex-git-review` | Findings and per-root delivery decisions. |

Load more than one specialized Skill only when the task actually crosses workflows. Typical chains
are Read -> Mount for lazy recovery, Maintain -> Validate, Workspace -> Maintain -> Validate ->
Review, and Setup -> Validate.

## Safety Baseline

- Preserve unrelated user changes.
- Do not write through a host mount path; use a maintenance root.
- Do not modify protected content without explicit user direction.
- Do not automatically commit, push, merge, reset, clean, switch the user's branch, remove tracked
  content, or discard a maintenance result.
- Report credentials, revision choices, tracked mount content, and destructive Git actions as user
  decisions with a concrete next action.
