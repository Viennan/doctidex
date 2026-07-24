---
name: doctidex-git-validate
description: Validate a doctidex directory tree and Git plugin readiness without modifying files or implicitly preparing mounts. Use for conformance checks, filter or link diagnostics, mount declaration checks, semantic index/log review, or pre-handoff validation.
---

# Doctidex Git Validate

## Prepare the CLI

Install `whero-doctidex` before validation. In this repository run
`.venv/bin/python -m pip install -e impls/libs/python`; otherwise install it in the active Python
environment. Ask the user if installation needs unavailable access.

## Validate

Run `doctidex-git check PATH --json` for the default offline check. Use `--online` only when the
user asks to verify current remote selectors or authorizes network access. Neither mode prepares or
synchronizes mounts.

Interpret the result domains separately:

- `protocol_structure`: deterministic protocol fields, continuity, filter, path, link, and mount
  structure.
- `semantic_review`: candidate entries requiring agent judgment. Read the relevant index, log,
  files, and Git changes with native tools before concluding conformance.
- `plugin_readiness`: Git ignore, tracked mount content, and operational prerequisites. A blocked
  plugin operation is not automatically a doctidex protocol failure.

Regex errors identify the index, field, and list position. Correct patterns using the public
`regex` VERSION1 Unicode search semantics; do not replace them with host-language defaults.

Report every confirmed issue with its path and an actionable next step. Escalate credentials,
ambiguous roots or revisions, tracked-content decisions, and potentially destructive Git actions
to the user. Do not expose internal storage or mapping diagnostics.
