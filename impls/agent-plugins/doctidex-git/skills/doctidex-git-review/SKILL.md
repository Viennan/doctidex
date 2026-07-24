---
name: doctidex-git-review
description: Review doctidex-aware Git changes for one or multiple maintenance roots before delivery. Use when checking content changes, index/log follow-up, filtering or protection boundaries, mount revisions, and unresolved Git actions without modifying the working tree.
---

# Doctidex Git Review

## Prepare the CLI

Install `whero-doctidex` before using the review commands. In this repository run
`.venv/bin/python -m pip install -e impls/libs/python`; otherwise install the distribution in the
active Python environment. Ask the user if installation is blocked.

## Review

For each independent root:

1. Run `doctidex-git changes PATH --json` and `doctidex-git check PATH --json`.
2. For mounted-source work, run `doctidex-git maintenance handoff MAINTENANCE_ROOT --json`.
3. Inspect the actual Git diff with native Git tools. Confirm that changes stay inside the intended
   root and do not write through a host mount or unauthorized protected boundary.
4. Judge content accuracy, index description sufficiency, important log follow-up, and change
   reasonableness yourself. CLI findings are objective facts or explicitly labeled candidates.
5. Report each root's base revision, changed files, validation result, semantic decisions, selector
   impact, and remaining commit/push/merge actions.

Do not fix files during review, implicitly prepare or synchronize mounts, submit Git changes, or
discard user work. If one root fails, preserve and report all other root results independently.
