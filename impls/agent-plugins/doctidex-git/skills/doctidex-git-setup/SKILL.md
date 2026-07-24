---
name: doctidex-git-setup
description: Create or adopt a doctidex root inside a Git working tree. Use when asked to initialize doctidex, repair the required root structure, add the mount exclusion and Git ignore rule, or assess an existing directory before adopting it.
---

# Doctidex Git Setup

## Prepare the CLI

Before using any `doctidex-git` command, verify that the `whero-doctidex` Python distribution is
installed in the active project environment. In this repository, install it with:

```bash
.venv/bin/python -m pip install -e impls/libs/python
```

For an installed distribution, use `python -m pip install whero-doctidex`. Run the CLI from the
same environment. If installation needs network access or permissions that are unavailable, stop
and ask the user for that access; do not substitute an unrelated tool.

## Workflow

1. Run `doctidex-git context PATH` to discover Git and doctidex roots. If several roots match, ask
   the user or select an exact root from explicit task context.
2. Run `doctidex-git init PATH --dry-run --json`. Explain planned files, that it is offline, and
   that it does not commit.
3. Inspect existing `index.md`, `.gitignore`, and unrelated Git changes with native file and Git
   tools. Preserve their content.
4. After write authorization, run `doctidex-git init PATH --apply --json`.
5. Review every `semantic_candidate`. Decide whether existing prose is already a recognizable
   index entry; write descriptions and links yourself where needed. The CLI must not write them.
6. Run `doctidex-git check PATH --json`. Treat `protocol_structure`, `semantic_review`, and
   `plugin_readiness` as separate results.

Report the selected root, changed files, remaining semantic decisions, and any action the user must
take. Never commit, push, reset, clean, or remove tracked content automatically.
