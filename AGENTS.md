# Repository Agent Guide

## Purpose

This repository develops Whero Wiki, an AI-oriented knowledge-organization
model. Its work includes the format specification, maintenance and query
workflows, selective-disclosure behavior, reusable agent instructions, and the
tools and tests that support those contracts.

The repository is a product-development workspace, not a collected reference
corpus. Treat changes to the Whero Wiki model as specification and software
changes that require coherent documentation, implementation, and tests.

## Repository Layout

- `whero-wiki/` is the canonical specification, implementation, reference set,
  test suite, and portable agent skill. It is also a Whero Wiki root.
- `asserts/` contains collected documents used as test fixtures. The spelling
  `asserts` is intentional and canonical for this repository.
- `.tmp/` contains disposable, task-specific test workspaces and copied fixture
  material.
- `.venv/` is the repository Python environment used for development,
  validation, scripts, and tests.

## Whero Wiki Product Boundary

- Treat files under `whero-wiki/` as product specifications, code, tests, and
  maintained references rather than immutable collected sources. Edit them
  normally when the requested work authorizes it.
- Keep `whero-wiki/` self-contained and portable as a skill. It must not depend
  on this root `AGENTS.md`, assume installation under `.agents/`, or use paths
  that only work in this repository. Resolve bundled resources relative to the
  skill root.
- Keep `whero-wiki/SKILL.md`, its references, scripts, tests, and
  `whero-wiki/agents/openai.yaml` aligned when a contract or workflow changes.
- Use `whero-wiki/requirements.txt` for the skill's Python dependencies.

## Minimal Self-Hosted Wiki Structure

`whero-wiki/` is itself a Whero Wiki, but its Wiki framework must remain
minimally invasive:

- Create and maintain framework documents only at the `whero-wiki/` root, such
  as `whero-wiki-meta.md`, `index.md`, and `log.md`.
- Do not create nested `index.md`, `log.md`, curated-knowledge scaffolding, or
  other Wiki framework files inside `references/`, `scripts/`, `tests/`,
  `agents/`, or other descendants.
- Do not inject Whero frontmatter into `SKILL.md`, source code, tests, or
  reference documents merely because they reside inside the Wiki root.
- Update the root-level index or log when appropriate for an authorized product
  change, but do not expand this root-only policy unless the user explicitly
  requests it.

This exception defines how this repository hosts the Whero Wiki product. It
must not be generalized into a restriction on Whero Wikis created elsewhere.

## Fixture Preservation

Treat everything under `asserts/` as immutable collected test material:

- Never edit, normalize, translate, reformat, repair links, add unresolved-link
  markers, or add Whero metadata, indexes, or logs inside `asserts/`.
- Never run a mutating script or test directly against `asserts/`.
- Preserve filenames, directory structure, languages, and file contents when
  selecting fixtures.
- If a test needs modified, migrated, indexed, disclosed, or otherwise
  transformed input, perform that work only on a copy under `.tmp/`.

## Test Isolation Workflow

Before every test run, create a task-specific workspace below `.tmp/`. Copy only
the fixture scope needed by that run; do not copy all of `asserts/` by default.
Use the copied path as test input and direct generated output and temporary
files into the same run workspace.

For a fixture-backed run, use this shape:

```bash
mkdir -p .tmp/<run>/fixtures .tmp/<run>/tmp
cp -a asserts/<selected-scope> .tmp/<run>/fixtures/
TMPDIR="$PWD/.tmp/<run>/tmp" .venv/bin/python -m unittest discover -s whero-wiki/tests -v
```

For tests that do not consume collected fixtures, still create
`.tmp/<run>/tmp` and set `TMPDIR` so Python temporary files remain inside the
isolated workspace.

- Use a unique, descriptive `<run>` name so concurrent or repeated work does
  not share mutable state.
- Inspect failed-run artifacts before cleanup when they may help diagnosis.
- Remove only `.tmp/` paths created by the current task. Do not assume other
  entries belong to the current agent.
- Treat `.tmp/` as disposable and never commit its contents.

## Python Development

- If `.venv/` does not exist, create it with `python3 -m venv .venv`.
- Run all repository Python development, scripts, validation, and tests through
  `.venv/bin/python` or executables installed in `.venv/bin/`.
- Install the skill dependencies with:

```bash
.venv/bin/python -m pip install -r whero-wiki/requirements.txt
```

- Add or update focused tests under `whero-wiki/tests/` for Python behavior
  changes.
- Keep virtual environments, bytecode, caches, coverage output, temporary test
  workspaces, and other generated artifacts out of version control.

## Validation

Choose validation proportional to the change. For Python or behavioral changes,
run the test suite from an isolated workspace:

```bash
mkdir -p .tmp/<run>/tmp
TMPDIR="$PWD/.tmp/<run>/tmp" .venv/bin/python -m unittest discover -s whero-wiki/tests -v
```

Useful additional checks include:

```bash
.venv/bin/python -m py_compile whero-wiki/scripts/*.py whero-wiki/scripts/whero_wiki_tools/*.py whero-wiki/tests/*.py
git diff --check
```

When root Wiki framework files exist and the change affects their contract,
validate the self-hosted Wiki with the bundled CLI. When a skill-validation
helper is available, validate `whero-wiki/` as the skill root rather than an
obsolete `.agents/skills/` path.

## Language

- Write repository-authored specifications, skill instructions, framework
  documents, logs, code comments, and test guidance in English.
- Preserve the original language and terminology of fixture documents under
  `asserts/`.
- Do not translate fixture text as part of test preparation. Tests may generate
  English maintained output from copied fixtures when that behavior is what the
  test is designed to exercise.

## Change Discipline

1. Read the relevant `whero-wiki/SKILL.md`, reference, implementation, and tests
   before changing a Whero Wiki contract.
2. Preserve unrelated user changes, especially during repository restructuring;
   do not revert or reclassify files outside the requested scope.
3. Make the smallest coherent change and keep specification, agent guidance,
   implementation, and tests consistent where the behavior spans them.
4. Use isolated copies of selected `asserts/` material for any fixture-backed
   validation, and never promote test mutations back into the fixture source.
5. Maintain only the root-level framework documents for the self-hosted
   `whero-wiki/`; do not introduce framework files deeper in the product tree.
6. Run relevant isolated tests and `git diff --check` before handing off a
   change.
