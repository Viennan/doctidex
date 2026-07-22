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
- `whero-wiki/spec/` contains the normative English protocol and synchronized
  Chinese translations under `whero-wiki/spec/CN/`.
- `whero-wiki/references/` contains non-normative workflow guidance and
  historical background loaded by the skill as needed.
- `asserts/` contains collected documents used as test fixtures. The spelling
  `asserts` is intentional and canonical for this repository.
- `.tmp/` contains disposable, task-specific test workspaces and copied fixture
  material.
- `.venv/` is the repository Python environment used for development,
  validation, scripts, and tests.
- `.agents/skills/` contains repository-local development workflows for
  testing, review, and remote submission.
- `.codex/config.toml` contains trusted project-level Codex settings, including
  the repository subagent concurrency limit.

## Repository Skills

Use the repository-local Skills instead of duplicating their workflows in task
prompts or ad hoc commands:

- `$test-whero-wiki` runs isolated tests and validation while protecting
  collected fixtures.
- `$review-whero-wiki`, only when explicitly authorized by the user, performs
  the xhigh subagent review of code, the complete documentation system,
  English/Chinese protocol alignment, portable Skill quality, and first-use
  usability. Do not infer review authorization from another workflow.
- `$submit-whero-wiki-change` prepares a development branch, validation,
  commit, push, and copyable PR or MR text, plus review only when the user
  separately authorizes it.

These Skills complement this file. The ownership, language, change-discipline,
and Git rules in `AGENTS.md` remain authoritative.

## Whero Wiki Product Boundary

- Treat files under `whero-wiki/` as product specifications, code, tests, and
  maintained references rather than immutable collected sources. Edit them
  normally when the requested work authorizes it.
- Keep `whero-wiki/` self-contained and portable as a skill. It must not depend
  on this root `AGENTS.md`, assume installation under `.agents/`, or use paths
  that only work in this repository. Resolve bundled resources relative to the
  skill root.
- Keep `whero-wiki/SKILL.md`, protocol documents, references, scripts, tests,
  and `whero-wiki/agents/openai.yaml` aligned when a contract or workflow
  changes. Do not describe a draft protocol feature as implemented behavior.
- Use `whero-wiki/requirements.txt` for the skill's Python dependencies.

## Protocol, Skill, And Tooling Layers

Treat the protocol, Skill, workflow references, and tooling as distinct product
layers. Keep them aligned, but do not turn one layer into a restatement of
another.

### Protocol Specification

Files under `whero-wiki/spec/` are the normative design and implementation
contract. Use them to define the complete model precisely, including canonical
terminology, identities, metadata schemas, invariants, ownership rules, state
transitions, boundary behavior, edge cases, recovery, compatibility, and
conformance requirements.

- Make the protocol complete enough for an independent implementation and for
  resolving behavior outside the supported workflows.
- State observable behavior and correctness requirements independently of the
  current Python module layout or CLI syntax. Specify an algorithm only when
  its exact behavior is part of interoperability or safety.
- Keep normative definitions, valid and invalid states, and difficult boundary
  cases in the protocol even when scripts currently enforce them automatically.
- Do not put repository-maintenance instructions, agent prompting, routine CLI
  recipes, or implementation convenience details in the protocol.
- Keep draft behavior visibly separate from the active runtime contract and
  maintain the English and Chinese protocol trees together.

### Skill Interface

`whero-wiki/SKILL.md` is the user and agent interface built on the protocol. It
should help a capable agent complete supported tasks with the smallest useful
context, not teach the complete protocol.

- Include the minimum protocol mental model needed to choose and safely perform
  a workflow, plus operation routing, user-visible constraints, common command
  forms, expected outcomes, and handling for actionable failures.
- Optimize the common path so most tasks do not require loading protocol files.
  Link directly to the relevant protocol document or section for unusual cases,
  protocol work, migrations, or questions beyond supported workflows.
- Do not duplicate full schemas, recursive rules, validation algorithms, Git
  comparison details, or other behavior already enforced by scripts. State the
  user-visible effect and let the tool perform the mechanical work.
- Describe only implemented workflows as available behavior. Route draft
  features to the draft specification without implying that the CLI supports
  them.
- Do not compensate for a missing or awkward tool capability by requiring the
  agent to perform fragile path normalization, metadata discovery, or other
  deterministic preprocessing in context.

### References And Tooling

Files under `whero-wiki/references/` are non-normative, task-specific workflow
and scenario guides. Put detailed CLI usage, current runtime limitations,
examples, review prompts, and recommended project layouts there when they would
make `SKILL.md` too large or too specialized.

Prefer scripts for stable, repeated, validation-sensitive workflows. Design
public CLI inputs for human and agent convenience: accept broadly useful path
forms, infer owning Wiki and ancestor metadata when unambiguous, validate and
normalize internally, and expose explicit overrides for genuine ambiguity.
Internal module APIs may use canonical protocol forms. Tool diagnostics should
carry the missing context and direct the caller to protocol details only when
the normal workflow cannot resolve the issue.

### Change Routing

Use the layer affected by a change to determine the required synchronization:

- A protocol-semantic change updates the English and Chinese specification and
  conformance coverage. Update implementation and tests when activating the
  behavior; update the Skill only when the user-visible mental model or workflow
  changes.
- A CLI or workflow change updates scripts, focused tests, relevant workflow
  references, and the Skill entry point. Update the protocol only when the
  underlying semantic contract changes.
- An internal refactor with unchanged observable behavior updates code and
  tests without causing protocol or Skill wording churn.
- A Skill-only usability edit must not silently redefine the protocol. An
  implementation must not establish an undocumented protocol merely because
  tests currently encode its behavior.

## Product Versioning

Every completed product change that adds, modifies, moves, or removes repository
content under `whero-wiki/` must increment the active Whero Wiki version. Use a
three-part `MAJOR.MINOR.PATCH` version and select the highest-impact change in
the product change:

- Increment `MAJOR` for an incompatible protocol or runtime change, including an
  identity, metadata, state-transition, or CLI contract change that requires
  consumers to migrate. Reset `MINOR` and `PATCH` to zero.
- Increment `MINOR` for a backward-compatible protocol addition or a new
  supported user-visible capability or workflow. Reset `PATCH` to zero.
- Increment `PATCH` for backward-compatible corrections and refinements,
  including fixes, internal refactors, tests, translations, references, Skill
  guidance, and framework-document updates that do not add a supported
  capability.

Apply one version increment per coherent product change, regardless of the
number of affected files or commits. The version update itself does not trigger
an additional increment. Changes confined outside `whero-wiki/` do not change
the product version.

Until the protocol defines separate product and format versions, treat the
three-part active version as the bundle's single version identity. Synchronize
all active version declarations in the same product change, including runtime
constants, Wiki and View metadata, English and Chinese protocol status and
examples, `SKILL.md`, maintained references and templates, tests, the repository
`README.md`, and root-level framework documents. Add a root `whero-wiki/log.md`
entry that records the new version and why its component changed. Preserve
historical documents that intentionally identify an older version.

## Minimal Self-Hosted Wiki Structure

`whero-wiki/` is itself a Whero Wiki, but its Wiki framework must remain
minimally invasive:

- Create and maintain framework documents only at the `whero-wiki/` root, such
  as `whero-wiki-meta.md`, `index.md`, and `log.md`.
- Do not create nested `index.md`, `log.md`, curated-knowledge scaffolding, or
  other Wiki framework files inside `spec/`, `references/`, `scripts/`,
  `tests/`, `agents/`, or other descendants.
- Do not inject Whero frontmatter into `SKILL.md`, source code, tests, or
  reference documents merely because they reside inside the Wiki root.
- Update the root-level index or log when appropriate for an authorized product
  change, but do not expand this root-only policy unless the user explicitly
  requests it.

This exception defines how this repository hosts the Whero Wiki product. It
must not be generalized into a restriction on Whero Wikis created elsewhere.

## Testing And Validation

Use `$test-whero-wiki` before every test or validation run. It defines fixture
copying, unique `.tmp` workspaces, `TMPDIR`, `.venv` setup, focused and full
tests, compilation, self-hosted Wiki validation, Skill validation, failure
artifact handling, and cleanup.

The following boundaries remain mandatory even when the Skill is unavailable:

- Treat everything under `asserts/` as immutable collected material. Never edit
  it or run a mutating command against it.
- Copy only the required fixture scope into a task-specific `.tmp/` workspace
  before transformation or testing.
- Run repository Python through `.venv/bin/python`, with dependencies declared
  by `whero-wiki/requirements.txt`.
- Add or update focused tests under `whero-wiki/tests/` for behavior changes.
- Keep generated environments, caches, coverage data, and `.tmp/` content out
  of version control.

## Git Workflow

- Do not develop on `main`. Before starting new work, require a clean worktree,
  switch to `main`, fetch and fast-forward it from its configured remote, then
  verify local `main` exactly matches the fetched remote branch and create a
  development branch. Stop if local `main` is ahead or divergent.
- Name development branches with a meaningful prefix such as `feat/`,
  `bugfix/`, `refactor/`, `docs/`, `test/`, or `chore/`.
- Never merge a local development branch into local `main`. PR or MR integration
  happens on the remote hosting service.
- The only routine local update to `main` is a fast-forward from its remote
  tracking branch. Stop on divergence instead of creating a merge commit.
- If uncommitted work is discovered on `main`, do not synchronize, stage,
  commit, or push it there. Move it to an explicitly approved prefixed branch
  before any remote operation, then assess whether that branch needs a reviewed
  rebase onto the remote baseline.
- Use `$submit-whero-wiki-change` for commit, push, and PR or MR preparation.

## Language

- Write repository-authored skill instructions, framework documents, logs,
  code comments, tests, and non-protocol references in English.
- Maintain every normative English protocol file under `whero-wiki/spec/` with
  a Chinese counterpart at the same relative filename under
  `whero-wiki/spec/CN/`. English is normative; Chinese is a
  synchronized translation. Update both in the same product change.
- Preserve the original language and terminology of fixture documents under
  `asserts/`.
- Do not translate fixture text as part of test preparation. Tests may generate
  English maintained output from copied fixtures when that behavior is what the
  test is designed to exercise.

## Change Discipline

1. Identify which product layer owns the requested change and whether it alters
   normative semantics, a supported workflow, or only internal implementation.
2. For a contract change, read the relevant protocol first, then the Skill,
   workflow reference, implementation, and tests that expose or enforce it.
3. Preserve unrelated user changes, especially during repository restructuring;
   do not revert or reclassify files outside the requested scope.
4. Make the smallest coherent change and keep specification, agent guidance,
   implementation, and tests consistent where the behavior spans them.
5. Keep draft protocol and active runtime behavior visibly distinct. Add
   compatibility guidance before renaming an active metadata field, status
   file, CLI command, or validation mode.
6. Use isolated copies of selected `asserts/` material for any fixture-backed
   validation, and never promote test mutations back into the fixture source.
7. Maintain only the root-level framework documents for the self-hosted
   `whero-wiki/`; do not introduce framework files deeper in the product tree.
8. Run `$test-whero-wiki` with checks proportional to the change before handoff.
