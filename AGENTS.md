# Repository Guide

## Project Scope

`doctidex` is an emerging directory-tree structure standard for use by both
agents and humans. Its current design goals are interoperability, extensibility,
and minimal format constraints.

## Repository Layout

- `spec/overview.md` contains the draft `doctidex` protocol.
- `spec/refs/` contains background reference material.
- `docs/` contains non-normative implementation design documents and the
  project-wide requirement history.
- `docs/requirements/` contains requirements shared across the project. A
  record may be a numbered Markdown file or, for a user-selected large
  requirement, a numbered directory whose `overview.md` navigates separately
  statused sub-requirements. Every record names its affected implementation or
  repository surface and links its dependencies in both directions.
- `docs/doctidex-git/` documents the Git plugin. `architecture/` contains the
  current language-neutral design, and `details/` contains language-specific
  implementation maps such as `details/python/`.
- `impls/` contains the non-normative implementations of the standard,
  including shared libraries and public surfaces used by agents.
- `impls/libs/` contains shared implementation libraries.
- `impls/libs/python/` contains the Python implementation.
- `impls/agent-plugins/` contains agent plugins and their agent-facing
  surfaces. `doctidex-git/` provides the plugin for Git repositories.
- `.agents/skills/` contains repository-local maintenance Skills. These Skills
  may use repository source, tests, and design documents and are not part of a
  published plugin user surface.
- `.asserts/` contains read-only source material used to construct tests.
- `.tmp/` contains disposable test workspaces and is ignored by Git.

## Repository Doctidex Organization

- Organize and maintain this repository itself as a doctidex directory tree.
  Repository indexes must follow `spec/overview.md` and should describe the
  repository as a working source and documentation tree rather than recreate a
  second documentation system.
- Keep source-code directories atomic. Their responsible parent index should
  explain the directory's purpose and may point to authoritative design or
  usage documentation, but it should not recursively enumerate source files or
  add indexing documents inside the source tree.
- Reuse the repository's existing documentation hierarchy. When a directory is
  already explained and navigated by documents such as those under
  `docs/`, higher-level indexes should provide a concise entry into that
  authority instead of repeating its detailed structure or prose.
- Keep included tool and configuration directories such as `.agents/` and
  `.codex/` atomic and describe only their repository-level purpose. Apply the
  same treatment to generated, vendored, fixture, asset, collected-source, or
  other directories where intrusive indexing would be inappropriate.
- A directory whose contents are already explained by authoritative internal
  documentation may be atomic even when it is not source or configuration.
  Link or name the authoritative explanation from the responsible parent when
  that improves discovery; do not duplicate it in the index.
- Use atomic entries to reduce index depth, not to hide useful content or avoid
  stating a directory's purpose. Atomic content remains available for native
  file and search exploration.
- Apply atomic only where the protocol permits it: an atomic directory cannot
  contain `index.md` or `log.md`. Preserve an existing doctidex index hierarchy
  instead of marking its directory atomic. Content already excluded by protocol
  or repository policy remains excluded rather than being reclassified merely
  to simplify indexing.

## Sources of Context

- `docs/` may define stricter implementation conventions, but those
  conventions are not protocol requirements.
- `spec/refs/` contains background references, not `doctidex` requirements.
- `.asserts/` contains collected source material. Treat it as read-only.

## Working Rules

- Keep proposals, accepted specification, and implemented behavior visibly
  distinct.
- Keep `spec/` focused on standard definitions, `docs/` focused on
  non-normative implementation design and requirement history, and `impls/`
  focused on code and agent-facing surfaces.
- Keep the protocol focused on observable structure, semantics, and
  conformance. Implementation, construction, and maintenance workflows belong
  to implementation variants.
- Do not turn placeholders such as "refer to OKF" into detailed requirements
  without an explicit design decision.
- Make small, coherent changes and preserve unrelated user work.
- Keep implementation design documents, shared libraries, agent-facing
  surfaces, and tests aligned once a behavior spans those layers.
- For local development, use the project-root `.venv` and install the Python
  implementation in editable mode with
  `.venv/bin/python -m pip install -e impls/libs/python` before running its CLI
  or tests. This repository-specific setup belongs here, not in published
  Skills.
- Validate changes in proportion to their scope using the tooling that exists
  at the time of the change.

## Implementation Documentation Design

- Lead architecture documentation with the user surface. For every supported
  workflow, state the concrete problem and scenario, why the design exists, how
  a human, agent, or program uses the interface, what remains observable after
  the operation, and how failures affect the next decision.
- Keep current design, requirement history, and implementation detail separate.
  Under `docs/<implementation>/`, `architecture/` says what the current design
  is and `details/` explains how a concrete implementation realizes it.
  `docs/requirements/` preserves the project-wide requirement history and links
  each record to the implementations and repository surfaces it affects.
- Keep architecture language-neutral unless a user explicitly authorizes a
  language-specific design. Public CLI syntax and schemas may appear there
  because they are user interfaces; source files, classes, functions, storage
  paths, and library mechanics belong in implementation details.
- Distinguish user-visible information from internal support information in
  headings, tables, and diagrams. Cross-link the two layers so an observable
  behavior can be traced to its design support without requiring users to learn
  the internal mechanism.
- Define responsibilities, non-responsibilities, invariants, and design
  constraints for every subsystem. Document every property of each domain
  concept and interface object; familiar properties may be concise, but none
  may be left implicit or ambiguous.
- Make implementation details a code design map rather than a source listing.
  For every module, explain intended callers, dependencies, main types and
  functions, all data attributes, side effects, failure and concurrency
  boundaries, expected use cases, and a small usage example where useful.
- Every standalone Requirement, large-Requirement `overview.md`, and
  sub-requirement document has exactly one visible lowercase status: `draft`,
  `implemented`, or `approved`. `draft` covers user-agent discussion and design;
  `implemented` means the agent has implemented the record but the user has not
  confirmed the result; `approved` means the user explicitly accepts the current
  implementation as ready for a PR or MR. Only an explicit user instruction may
  set `approved` or move an `approved` record back to another status.
- When the user expresses an intent equivalent to "create a requirement" or
  "record this requirement", create a new `draft` record in
  `docs/requirements/` from the user's initial intent. Do not stop at a chat-only
  proposal or wait for separately worded authorization to create the record.
  Re-read the shared directory first, allocate the next project-wide number, and
  identify the affected implementation or repository surface.
- When the user selects the large-Requirement form, allocate one project-wide
  number to a `<NNNN>-<kebab-case-title>/` directory. Put the overall stable ID,
  description, scope, aggregate status, and sub-requirement navigation in
  `overview.md`. Give each sub-requirement document a stable ID derived from the
  overall ID and its own status, intent, decisions, impact, and acceptance
  criteria. Sub-requirements do not consume additional project-wide numbers.
  Keep the single-file form as the default and do not convert an existing record
  to a directory without user direction.
- Treat a large-Requirement overview status as a gated aggregate. It may be
  `implemented` only when every sub-requirement is `implemented` or `approved`,
  and it may be `approved` only when every sub-requirement is `approved` and the
  user explicitly approves the overall Requirement. An overview status never
  changes sub-requirement statuses. If a sub-requirement returns to an earlier
  state, return the overview to a state whose gate remains satisfied; an
  `approved` rollback still requires explicit user direction.
- A Requirement may move repeatedly between `draft` and `implemented` before
  approval. Mark it `implemented` after completing and validating the work. If
  the user then changes the requirement or solution, move it back to `draft`,
  incorporate the reviewed change, and implement again. Do not create false
  historical finality around normal pre-approval iteration.
- During `draft`, improve the record from the user's intent without adding
  unrequested features or requirements. Use `<question>...</question>` blocks
  only for decisions that genuinely need discussion. A user may answer in an
  immediately adjacent `<answer>...</answer>` block or in conversation. Once the
  decision is incorporated, remove the question and answer blocks unless the
  user explicitly asks to preserve them.
- A user may insert `<comment>...</comment>` next to Requirement content to
  provide feedback. Only the user may author or explicitly authorize such a
  block; an agent must not create one or attribute inferred wording to the user.
  Read and resolve every live comment while refining the record. Incorporate
  direct feedback into the substantive text; when a comment requires a user
  decision, use `<question>` with an immediately adjacent `<answer>` or obtain
  the answer in conversation. A comment must not split a question/answer pair.
- Do not treat acknowledgement, relocation, or deletion alone as comment
  resolution. A comment is resolved only after the record reflects the requested
  change or the user's explicit decision not to change it, and all resulting
  questions, implementation impact, dependencies, and acceptance criteria are
  settled. Then remove the `<comment>` block; if its content must be preserved,
  rewrite it as ordinary provenance or decision text. Any live comment keeps a
  non-approved record `draft`. A comment added to an `implemented` record moves
  it back to `draft`; for an `approved` record, preserve its status and content
  until the user authorizes reopening it or creating a linked follow-up instead
  of inferring permission to rewrite approved history.
- Requirements records preserve the user's reviewed intent, design intent,
  decisions, implementation impact, and status without needing to reproduce raw
  input verbatim. Do not attribute unreviewed inference to the user or
  reconstruct unrecorded history. An `approved` record is not rewritten or
  downgraded without explicit user direction; later changes normally use a new
  linked record.
- Record dependency and follow-up relationships with navigable links in both
  participating Requirement documents. For a large Requirement, link the
  overview by default and the specific sub-requirement when the relationship is
  narrower. Keep stable IDs and describe the relationship so direction is
  discoverable from either record.
- Before processing `draft` Requirements, inspect the relevant current
  Architecture, Details, implementation, tests, and public surfaces to test the
  request's explicit and implicit assumptions against actual behavior. When an
  assumption differs from the current implementation, explain the concrete
  difference and its design impact to the user before basing a Requirement on
  it; record the corrected or intentionally changed premise only after user
  review.
- Stage new implementation documentation according to established authority:
  record undecided work as a `draft` Requirement, keep target design there until
  it is implemented, update Architecture and Details when code exists, and then
  mark the Requirement `implemented`. Approval is a later user decision, not a
  prerequisite for documenting current code. Examples, forward-test prompts,
  and agent inferences are not historical requirements unless the user
  explicitly designates them as such.
- Architecture must include the agent-facing Skill design principles below:
  installed-product wording, user-only information, a sufficient and acyclic
  reading chain, complete command contracts, native-tool freedom,
  deterministic non-AI helpers, bounded output, and actionable failures.
  Language-specific details must not duplicate self-explanatory Skill usage.
- Prefer Markdown tables, timelines, state diagrams, flowcharts, and sequence
  diagrams when they reduce explanation cost. Avoid UML unless a user
  explicitly asks for it.
- Keep one authoritative explanation for each fact and link to it elsewhere.
  Maintain navigation indexes, update links when moving files, and validate
  that no document is orphaned after a reorganization.
- Cross-link `architecture/`, `details/`, and `requirements/` documents as
  needed to form a complete, navigable, and insight-building knowledge network
  across current design, historical intent, and concrete implementation.

## Repository Maintenance Skills

- Use `.agents/skills/review-doctidex-repository/` only after the user
  explicitly authorizes a review, audit, compliance check, or review-and-repair
  cycle. A review-only request is read-only; enter repair and targeted re-review
  only when the user explicitly authorizes repair.
- Unless the user explicitly selects a review scope, review only Requirement
  records that are active in the current task and have status `draft` or
  `implemented`. An `approved` record may be read as supporting authority but is
  not a default review target. If there is no active non-approved Requirement,
  ask the user to select the review scope before proceeding.
- When an active Requirement uses a directory, include its `overview.md` and the
  active sub-requirements in the scope. Verify that overview navigation matches
  sub-requirement statuses and that the aggregate status gates are satisfied.
- Protocol review must trace every violation to an actual protocol requirement.
  An implementation feature is not nonconforming merely because the protocol
  leaves it unspecified. A potentially valuable new protocol rule is an
  advisory recommendation, not a high-severity `must_fix`, unless current
  observable behavior violates an existing normative rule.
- Use `.agents/skills/write-doctidex-design-docs/` when creating or revising
  implementation Architecture, Requirements, or Details for any implementation,
  not only `doctidex-git`.
- Use `.agents/skills/write-doctidex-agent-skills/` when creating or revising
  published or repository-local Skills. Preserve the audience boundary: local
  maintenance Skills may read repository authorities, while published Skills
  must remain usable as installed-product guidance.
- Validate every changed local Skill and its `agents/openai.yaml`. Forward-test
  complex workflow changes with independent agents using raw artifacts rather
  than leaked expected findings or fixes.

## Agent-Facing Skill Design

- Write published Skills for an installed product. They must not require the
  agent to read source code, implementation documentation, repository-local
  paths, test commands, or debugging notes in order to use the public surface.
- Separate shared and specialized guidance. Use one foundational or
  orchestrator Skill for the user mental model, shared terminology, common CLI
  grammar, output conventions, safety rules, and routing; keep task-specific
  workflows in specialized Skills.
- Give Skills an explicit, acyclic reading chain. A specialized Skill may
  conditionally direct an unfamiliar agent to the foundational Skill and may
  route to another specialized workflow, but common reference material should
  not be copied into every Skill. Define the runtime order so already-loaded
  Skills are not reopened when a routing table and specialist reference each
  other.
- Define specialized terms before using them in a workflow. For every CLI
  command introduced by a Skill, document its exact invocation, argument form
  and constraints, required and optional inputs, omission/default behavior,
  root-selection behavior, read/write and network effects, dry-run/apply and
  batch behavior where applicable, decision-relevant output fields, and
  actionable failure handling.
- Keep parameter and output descriptions user-facing: explain what the agent
  supplies, observes, and can do next, not how the implementation stores or
  computes the result. Internal architecture, repository development, and
  debugging guidance belong in `docs/` or this file.
- A foundational Skill plus the relevant specialized Skill must be sufficient
  to complete the supported workflow without guessing command syntax or
  consulting implementation documentation.
- Preserve the agent's use of native file, search, shell, editing, and Git
  tools. CLI helpers should add doctidex-specific objective facts rather than
  replace mature general-purpose tools.
- Keep CLI behavior deterministic and non-AI. Agents author and judge semantic
  content; CLIs may validate, format, or report objective structure and state.
- Keep default output bounded and explain pagination, collapse, summary, and
  filtering controls wherever a command can return a collection.
- For watch, subscription, polling, follow, or streaming commands, define event
  ordering and replay, duplicate and gap behavior, cursor lifetime, schema
  compatibility, waiting and cancellation, interruption and backpressure, and
  a bounded non-following default for agents.
- Validate every changed Skill and its agent metadata, then validate the
  containing plugin.
