---
name: write-doctidex-design-docs
description: Design, create, reorganize, or revise implementation documentation under docs using per-implementation Architecture and Details plus the project-wide Requirements history. Use when the user asks or expresses intent to create or record a Requirement, or when documentation must explain a user surface, preserve requirement status and dependencies, map current code, or connect those layers for any doctidex implementation; do not use for protocol wording or ordinary end-user content.
---

# Write doctidex Implementation Design Documents

Build implementation documentation as a navigable design system: Architecture explains the
current design, Requirements preserve how it evolved, and Details map that design to concrete code.
Apply this model to every implementation, not only `doctidex-git`.

## Establish Authority and Scope

1. Read `AGENTS.md`, especially `Implementation Documentation Design`.
2. Identify the implementation directory under `docs/`, the project-wide Requirement records under
   `docs/requirements/`, and the user-authorized change.
3. Read the relevant current Architecture, Requirements records, Details, code, tests, public CLI,
   and Skills according to the document being changed.
4. Read `spec/overview.md` completely before making or evaluating a protocol claim. Do not promote
   implementation conventions or `spec/refs/` material into protocol requirements.
5. Preserve unrelated documentation and existing historical records.

Read [document-types.md](references/document-types.md) before selecting a document owner or
creating an outline.

## Maintain the Requirement Lifecycle

Every Requirement displays exactly one lowercase status:

- `draft`: the user and agent are refining the requirement and solution.
- `implemented`: the agent has implemented and validated the current record, but the user has not
  confirmed the result.
- `approved`: the user explicitly accepts the current implementation as ready for a PR or MR.

Move `draft -> implemented` after implementation. Move `implemented -> draft` when user feedback
changes the requirement or solution, then revise and implement again. This cycle may repeat. Set
`approved`, or move an `approved` record back to either earlier state, only on explicit user
instruction. Never infer approval from implementation, tests, praise, silence, or a review result.

Treat user intent equivalent to "create a requirement" or "record this requirement" as direct
authorization to create the next numbered `draft` record in `docs/requirements/`. Build it from the
initial intent during the same task; do not return only a proposed outline or require a second,
formulaic authorization message.

For a new implementation, preserve the order of authority:

1. Record the authorized request as a `draft` Requirement in `docs/requirements/`.
2. Keep alternatives and target-design reasoning in that record while work remains `draft`; do not
   present unimplemented target behavior as current Architecture.
3. When code and tests exist, update Architecture and Details to describe the current result, then
   mark the Requirement `implemented`.
4. Treat `approved` as the user's readiness decision, not as a prerequisite for documenting current
   implemented behavior.

A layer index may state that implementation mapping is deferred; do not invent modules, types, or
behavior.

A hypothetical example, forward-test prompt, or agent inference is test input, not repository
history. Do not create an implementation documentation tree or designate a Requirement baseline
unless the user expresses intent to create or record one. A design-only response may propose the
future layout without creating it.

## Classify Before Writing

Place each fact in exactly one primary layer:

- Put current language-neutral problems, user workflows, public interfaces, models, constraints,
  and failure semantics in `architecture/`.
- Put the user-reviewed requirement intent, considered outcome, implementation impact, provenance,
  lifecycle status, and reciprocal dependency links in `docs/requirements/`.
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

During `draft`, complete and organize the user's intent without adding features, requirements, or
scope the user did not request. For a genuinely unresolved decision, use this exact temporary form:

```text
<question>
What needs the user's decision?
</question>
<answer>
The user's adjacent answer, when supplied in the document.
</answer>
```

The user may instead answer in conversation. Incorporate that answer into the Requirement and remove
all resolved `<question>` and `<answer>` blocks unless the user explicitly asks to preserve them.

Keep provenance visible and separate the reviewed requirement, design intent, decision, outcome,
implementation impact, and later supersession. Before approval, revise the same record as it moves
between `draft` and `implemented`; do not preserve obsolete question/answer scaffolding as history.
Do not attribute unreviewed inference to the user. Do not rewrite or downgrade an `approved` record
without explicit user direction; normally add a new linked record for a later change. Never rewrite
history merely to agree with current Architecture or reconstruct unrecorded history from current code.

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

Every dependency, refinement, supersession, or follow-up between Requirement records must be linked
in both documents. Name the relationship direction on each side; a one-way mention or index-only
entry does not satisfy dependency traceability.

Use tables, timelines, flowcharts, sequence diagrams, and state diagrams when they materially lower
comprehension cost. Avoid UML unless the user explicitly requests it.

## Validate the Result

Check that:

- the document type and authority are explicit;
- user-visible and internal information are visibly separated;
- Architecture contains no accidental language/file/storage coupling;
- every exposed field and every internal concept property is explained;
- Requirements preserve reviewed intent and provenance without treating raw wording as authority;
- every Requirement uses only `draft`, `implemented`, or `approved`, and approval transitions have
  explicit user provenance;
- Requirement dependencies are navigable in both directions;
- resolved question and answer blocks are removed unless explicitly retained;
- Details cover every relevant module and match code/tests;
- links form a useful network without duplicate authorities;
- changed public behavior is aligned across Architecture, Details, Skills, code, and tests;
- Markdown links, anchors, diagrams, indexes, and whitespace are valid.

Report any intentionally deferred layer update instead of silently leaving contradictory documents.
