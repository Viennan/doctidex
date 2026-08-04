# Validate Protocol Structure

Run:

```text
DOCTIDEX_GIT validate [ROOT] [--scope INTERNAL_DIRECTORY]...
  [--limit N] [--cursor TOKEN] --json
```

`ROOT` is an optional exact existing readable doctidex root directory. Omission selects the unique
root containing cwd. `--scope` is repeatable and accepts `/` or a root-absolute POSIX path to an
existing readable directory, with no anchor. Omission means `/`. Values are lexically normalized,
sorted, deduplicated, and descendants covered by an ancestor are removed. Any invalid scope blocks;
it never falls back to full validation.

The command is offline, read-only, deterministic, and has no dry-run/apply. It checks the requested
directories plus the root/index/configuration/navigation/link support needed to interpret them. It
does not read Git remotes, managed external state, or plugin registries.

Read all result fields:

- `coverage` is `full` only for scopes `["/"]`; otherwise it is `scoped`.
- `protocol_structure` is `pass` or `fail` for that coverage. A scoped pass is not a full-root
  conformance conclusion.
- `scan_complete` says whether all required safe content was read.
- `semantic_review` and `semantic_candidates` identify agent judgments, independent of protocol
  findings.
- `findings` contains mechanically confirmed protocol errors. `collection.lists.findings` and
  `.semantic_candidates` give total/returned/truncated counts; use `next_cursor` unchanged for the
  next page with the same root, scopes, and limit.

A protocol fail is a completed warning and exit 1. Fix finding codes such as invalid root or
frontmatter, index/log continuity, local configuration, atomic indexing, unsafe declaration,
unreachable paths, invalid link paths/annotations, or reserved-name conflict, then rerun the same
coverage. `scope_invalid`, root-selection errors, and `cursor_invalid` are blocked exit 2; correct
the input or restart at page one. Do not interpret an empty candidate list as semantic approval.
