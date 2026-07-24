---
name: doctidex-git-workspace
description: Open isolated writable roots for mounted Git sources and coordinate tasks spanning multiple doctidex roots. Use when a host mount must be changed, the host repository is itself mounted, or one task requires separate source and host results.
---

# Doctidex Git Workspace

## Prepare the CLI

Install `whero-doctidex` first. In this repository run
`.venv/bin/python -m pip install -e impls/libs/python`; otherwise install the distribution into the
active Python environment. Ask the user if required access is unavailable.

## Plan Independent Roots

Run `doctidex-git maintenance scope PATH... --json`. Treat each returned root as an independent
result with its own base commit, writable boundary, diff, validation, and Git delivery actions.
The CLI reports objective scopes and explicit dependency facts; decide the actual task order
yourself.

For a mounted source, ensure it has an effective commit, then run:

```bash
doctidex-git maintenance open /.doctidex/mounts/source --json
```

Work only under the returned `maintenance_root`, using the source's own `index.md` and native agent
file tools. Never modify the host mount path. The host remains on its existing effective commit,
including when the source is the current host repository.

## Handoff and Close

Run `doctidex-git maintenance handoff MAINTENANCE_ROOT --json` for each source. Review and explain
each diff separately. Ask the user to authorize any commit, push, merge, or selector update; the
plugin does not perform them automatically.

Run `maintenance close` only after the result is clean or the user has explicitly disposed of it.
If changes remain, the CLI must preserve the root and return the next action. A multi-root task is
not atomic: preserve and report successful roots when another root fails.
