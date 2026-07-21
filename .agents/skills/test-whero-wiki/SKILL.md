---
name: test-whero-wiki
description: Run Whero Wiki repository tests and validation in isolated `.tmp` workspaces while protecting immutable `asserts/` fixtures. Use when changing Python behavior, protocol contracts, Skill content, references, framework files, or when asked to test, validate, reproduce a failure, or report verification for this repository.
---

# Test Whero Wiki

Read the repository `AGENTS.md` before running anything. Keep every generated
file inside a unique task workspace under `.tmp/`, and use the repository
`.venv` for Python commands.

## Select The Validation Surface

- For Python or behavioral changes, run focused tests first, then the full
  suite and Python compilation.
- For protocol changes, run the full suite, validate the self-hosted Wiki, and
  confirm the English and Chinese protocol trees stay synchronized.
- For Skill changes, validate each changed Skill directory. Validate
  `whero-wiki/` itself when its `SKILL.md`, references, scripts, metadata, or
  contract changed.
- For documentation-only changes, run the relevant Skill or Wiki validator and
  whitespace checks. Do not run unrelated expensive checks without a reason.

## Prepare An Isolated Run

1. Choose a unique descriptive run name and create `.tmp/<run>/tmp` and
   `.tmp/<run>/pycache`.
2. If `.venv` is absent, create it with `python3 -m venv .venv`.
3. Install missing Python dependencies with:

   ```bash
   .venv/bin/python -m pip install -r whero-wiki/requirements.txt
   ```

4. For fixture-backed tests, copy only the required fixture scope:

   ```bash
   mkdir -p .tmp/<run>/fixtures .tmp/<run>/tmp
   cp -a asserts/<selected-scope> .tmp/<run>/fixtures/
   ```

Never edit or run a mutating command against `asserts/`. Point the test and its
outputs at the copied fixture tree.

## Run Tests And Checks

Set both `TMPDIR` and `PYTHONPYCACHEPREFIX` on every repository Python command:

```bash
TMPDIR="$PWD/.tmp/<run>/tmp" \
PYTHONPYCACHEPREFIX="$PWD/.tmp/<run>/pycache" \
  .venv/bin/python -m unittest discover -s whero-wiki/tests -v
```

Use a discovery pattern for a focused file when useful:

```bash
TMPDIR="$PWD/.tmp/<run>/tmp" \
PYTHONPYCACHEPREFIX="$PWD/.tmp/<run>/pycache" \
  .venv/bin/python -m unittest discover \
  -s whero-wiki/tests -p 'test_views.py' -v
```

Compile Python sources after behavior changes:

```bash
TMPDIR="$PWD/.tmp/<run>/tmp" \
PYTHONPYCACHEPREFIX="$PWD/.tmp/<run>/pycache" \
  .venv/bin/python -m py_compile \
  whero-wiki/scripts/*.py \
  whero-wiki/scripts/whero_wiki_tools/*.py \
  whero-wiki/tests/*.py
```

Validate the self-hosted product Wiki when its contract or framework changes:

```bash
TMPDIR="$PWD/.tmp/<run>/tmp" \
PYTHONPYCACHEPREFIX="$PWD/.tmp/<run>/pycache" \
  .venv/bin/python whero-wiki/scripts/whero_wiki.py \
  validate --wiki whero-wiki --mode full
```

When the `skill-creator` validation helper is available, run
`quick_validate.py` separately against every changed Skill root, including
repository-local Skills under `.agents/skills/`. Confirm each
`agents/openai.yaml` still matches its `SKILL.md` when either file changes.

Finish with:

```bash
git diff --check
```

Also inspect untracked text files for trailing whitespace because
`git diff --check` does not cover them.

## Handle Failures And Cleanup

Inspect failed-run artifacts before changing code when they can explain the
failure. Preserve the task workspace while diagnosing and report its path.
After a successful run, remove only `.tmp/<run>` created for the current task;
never clean another task's workspace.

Report the commands run, pass/fail counts, skipped checks with reasons, and any
remaining risk. Do not claim a check passed when it was not run.
