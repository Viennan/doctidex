---
name: write-doctidex-design-docs
description: Design, create, reorganize, or revise implementation documentation under impls/docs using the repository-wide Architecture, Requirements, and Details model. Use when documentation must explain a user surface, preserve requirement history, map current code, or connect those layers for any doctidex implementation; do not use for protocol wording or ordinary end-user content.
---

# Write doctidex Implementation Design Documents

Build implementation documentation as a navigable design system: Architecture explains the
current design, Requirements preserve how it evolved, and Details map that design to concrete code.
Apply this model to every implementation, not only `doctidex-git`.

## Establish Authority and Scope

1. Read `AGENTS.md`, especially `Implementation Documentation Design`.
2. Identify the implementation directory and the user-authorized change.
3. Read the relevant current Architecture, Requirements records, Details, code, tests, public CLI,
   and Skills according to the document being changed.
4. Read `spec/overview.md` completely before making or evaluating a protocol claim. Do not promote
   implementation conventions or `spec/refs/` material into protocol requirements.
5. Preserve unrelated documentation and existing historical records.

Read [document-types.md](references/document-types.md) before selecting a document owner or
creating an outline.

## Stage New Implementations Honestly

For a new implementation, preserve the order of authority:

1. Record a new request as a proposed or undecided Requirement.
2. Treat Architecture as current design only after the relevant decision is accepted. Keep target
   design alternatives in the proposed Requirement while approval is pending; do not create a
   current Architecture page for them.
3. Create Details only for code and tests that exist. A layer index may state that implementation
   mapping is deferred; do not invent modules, types, or behavior.

A hypothetical example, forward-test prompt, or agent inference is test input, not repository
history. Do not create an implementation documentation tree or designate a Requirement baseline
until the user explicitly authorizes repository provenance. A design-only response may propose the
future layout without creating it.

## Classify Before Writing

Place each fact in exactly one primary layer:

- Put current language-neutral problems, user workflows, public interfaces, models, constraints,
  and failure semantics in `architecture/`.
- Put the user-reviewed requirement intent, considered/accepted outcome, implementation impact,
  provenance, and status in `requirements/`.
- Put language/runtime-specific modules, files, classes, functions, storage, algorithms, tests,
  limitations, and code examples in `details/<variant>/`.

Do not use Requirements as a backlog, Architecture as a source listing, or Details as a second
agent-facing Skill manual. If one statement relates all three layers, choose one authoritative home
and link to it from the others.

## Write User Surface Before Mechanism

For every supported workflow, state:

1. The concrete problem and scenario.
2. Why the design exists and which failure it prevents.
3. How a human, agent, or program uses the interface.
4. Preconditions, inputs, defaults, and permissions.
5. Observable results and the resulting working state.
6. Failures, preserved results, and actionable next decisions.
7. The rationale and non-goals.

Only then introduce the language-neutral model that supports the surface. Define each concept,
every property, visibility, responsibility, non-responsibility, invariant, lifecycle, concurrency
boundary, and non-atomic boundary. Familiar fields may be concise but cannot be omitted.

## Preserve Historical Requirements

Before formulating a Requirement, inspect the relevant current Architecture, Details, code, tests,
and public surfaces. Test both explicit statements and implicit premises against actual behavior. If
a premise differs, explain the concrete difference and design impact to the user before using it as
the Requirement basis.

Record the clarified and completed intent after user review; do not copy raw input merely to preserve
its wording. Keep provenance visible and separate the reviewed requirement, design intent, decision,
final outcome, implementation impact, and later supersession. Do not attribute unreviewed inference
to the user. Never rewrite an accepted record to make it agree with current Architecture. Add a new
record or explicit cross-link for a later change, and do not reconstruct unrecorded history from
current code.

## Map Concrete Implementations

For every module or equivalent ownership unit, explain its purpose and non-purpose, intended
callers, dependencies, main types/functions, all data attributes, side effects, errors, concurrency,
typical use, and tests. Include a compact code example where it reduces rediscovery. Record current
limitations as facts, not desired Architecture.

Prefer a code design map over line-by-line narration. Verify Details against source and tests rather
than copying stale comments.

## Build the Knowledge Network

Cross-link Architecture, Requirements, and Details whenever the relationship helps a maintainer
move between current behavior, historical intent, and implementation. Keep one authoritative
explanation per fact. Maintain indexes, reciprocal links where useful, valid relative targets and
anchors, and no orphan pages.

Use tables, timelines, flowcharts, sequence diagrams, and state diagrams when they materially lower
comprehension cost. Avoid UML unless the user explicitly requests it.

## Validate the Result

Check that:

- the document type and authority are explicit;
- user-visible and internal information are visibly separated;
- Architecture contains no accidental language/file/storage coupling;
- every exposed field and every internal concept property is explained;
- Requirements preserve reviewed intent and provenance without treating raw wording as authority;
- Details cover every relevant module and match code/tests;
- links form a useful network without duplicate authorities;
- changed public behavior is aligned across Architecture, Details, Skills, code, and tests;
- Markdown links, anchors, diagrams, indexes, and whitespace are valid.

Report any intentionally deferred layer update instead of silently leaving contradictory documents.
