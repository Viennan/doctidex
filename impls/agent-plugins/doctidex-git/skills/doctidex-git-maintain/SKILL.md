---
name: doctidex-git-maintain
description: Maintain content within one explicitly selected doctidex root and its Git working tree. Use when updating documents, indexes, or logs while respecting atomic, excluded, protected, and mount boundaries and preserving unrelated user changes.
---

# Doctidex Git Maintain

## Prepare the CLI

Install `whero-doctidex` before using `doctidex-git`. In this repository run
`.venv/bin/python -m pip install -e impls/libs/python`; otherwise install it into the active Python
environment. Ask the user if installation requires unavailable access.

## Workflow

1. Run `doctidex-git context PATH --json`, `doctidex-git inspect PATH --json`, and
   `doctidex-git changes PATH --json` as needed. Establish exactly one root and preserve existing
   Git changes.
2. Use native agent file and search tools to inspect and edit. The CLI does not generate content.
3. Do not write excluded content, protected content without explicit user direction, or any host
   mount path. For a mounted source, switch to `$doctidex-git-workspace`.
4. Update the responsible `index.md` when the actual content change requires it. If an applicable
   `log.md` exists, decide whether the change is important and write the entry yourself.
5. Run `doctidex-git check PATH --json` and `doctidex-git changes PATH --json`.
6. Review protocol findings, semantic candidates, and the Git diff. Form the content-quality and
   completeness conclusion yourself.

Return changed files, index/log decisions, validation facts, and unresolved user actions. Do not
commit, push, reset, clean, switch the user's branch, or discard unrelated work.
