---
name: doctidex-git-validate
description: Validate a doctidex directory tree and Git plugin readiness without modifying files or implicitly preparing mounts. Use for conformance checks, filter or link diagnostics, mount declaration checks, semantic index or log review, remote selector checks, or pre-handoff validation.
---

# Doctidex Git Validate

If the common path, root, CLI, and output model is not already established, load
`$doctidex-git-guide` before continuing.

## Terms

- **Protocol structure**: deterministic markers, continuity, filters, path boundaries, parsed link
  boundaries, and mount declaration structure.
- **Semantic review**: candidates that require reading index/log/content/Git changes.
- **Plugin readiness**: root `.gitignore`, tracked mount content, and Git mount extension validity.
- **Offline check**: validates local structure and state without refreshing remote selectors.
- **Online check**: additionally fetches and compares declared Git selectors; it does not prepare or
  synchronize mounts.

## Command Contract

```bash
doctidex-git check ROOT --json
doctidex-git check ROOT --online --json
```

`ROOT` is a filesystem path. Prefer the exact doctidex root directory; a contained file can select
its root but may be ambiguous when roots nest. Default check is offline and read-only. Use
`--online` only when the user asks whether branch/tag selectors have changed or authorizes needed
network/credentials.

Online output `remote[]` contains:

- `effective_commit`: current readable commit or null;
- `remote_commit`: selector result just fetched;
- `update_available`: true only when a non-null effective commit differs from remote.

Online check never applies `remote_commit`. Use `$doctidex-git-mount` and sync dry-run/apply for an
explicit update.

## Filter Semantics

`atomic_entries`, `excludes`, and `protected` each accept a list of one-field conditions:

```yaml
- path: relative/path
- regex: '(^|/)generated(?:/|$)'
```

Use relative `/`-separated paths. Do not use an absolute path or `..`. A path condition covers the
matching path and descendants. Regex uses `regex` VERSION1 Unicode search, is case-sensitive by
default, adds no anchors, and sees no trailing `/` on directories. For a target such as
`guide/generated/file.md`, the current matcher checks successive path prefixes, allowing a
directory match to cover descendants. Use inline regex options when different case behavior is
needed.

## Interpret the Three Domains

- Fix each `protocol_structure: fail` finding at its reported path, then rerun check.
- For `semantic_review: required`, read the responsible index, applicable log, candidate path, and
  actual Git diff. Confirm sufficient prose or author needed content yourself.
- For `plugin_readiness: blocked`, handle root Git ignore or tracked mount content separately. Do
  not call it a doctidex protocol failure or remove tracked content without user direction.

A protocol pass does not prove that every link target exists. Current validation checks
machine-parsed Markdown path boundaries, but not target existence, anchors, or non-standard link
extensions. Atomic content is opaque to recursive protocol conformance, so check does not validate
links inside an atomic unit. Use native file tools and task-specific requirements for those checks.

## Output and Failure

Top-level `status: warning` can accompany useful findings/candidates and may exit successfully;
inspect the three domains rather than relying only on exit status. Check `collection` before
claiming all findings were reviewed.

Report each confirmed issue with its path, code, evidence, and next action. Ask the user for
credentials, network access, ambiguous root/revision choice, tracked-content decisions, or
potentially destructive Git actions. Do not prepare, synchronize, edit, commit, or push during
validation.
