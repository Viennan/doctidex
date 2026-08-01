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

Every standalone Requirement, large-Requirement overview, and sub-requirement displays exactly one
lowercase status:

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

Treat `draft` and `implemented` records as active. When the user directly requests a change to an
Architecture, Details, or another non-Requirement document produced by a corresponding active
Requirement, update the Requirement before editing that artifact:

1. Identify the narrowest corresponding Requirement or sub-requirement.
2. Record the feedback, resulting design intent, implementation impact, and acceptance criteria;
   move `implemented -> draft` when the request changes the requirement or solution, and synchronize
   a large-Requirement overview.
3. Only then modify the requested artifact and any other affected layers.
4. Validate the completed work before returning the Requirement to `implemented`.

Do not bypass Requirement history because the user names an artifact directly. If no corresponding
active Requirement exists, do not create one solely from artifact feedback; follow the normal
requirement-creation rule only when the user expresses that intent.

## Structure Large Requirements

Use a single numbered Markdown file by default. When the user selects a directory for a large
Requirement, allocate the next project-wide number once and create
`docs/requirements/<NNNN>-<kebab-case-title>/` with:

- `overview.md`, which owns the overall stable ID, overall description and scope, aggregate status,
  and a link, derived stable ID, summary, and current status for every sub-requirement;
- one Markdown document per sub-requirement, each with its own derived stable ID, lifecycle status,
  reviewed intent, decisions, implementation impact, and acceptance criteria.

Do not allocate another project-wide number to a sub-requirement. Keep filenames stable and make
every sub-requirement reachable from `overview.md`. Link the overview from
`docs/requirements/index.md`. Do not convert an existing standalone record to a directory unless
the user directs it.

Treat the overview status as an aggregate gate, not as a command that changes children:

- keep it `draft` while any sub-requirement is `draft`;
- allow `implemented` only when every sub-requirement is `implemented` or `approved`;
- allow `approved` only when every sub-requirement is `approved` and the user explicitly approves
  the overall Requirement.

An overview may remain `implemented` while sub-requirements mix `implemented` and `approved`.
Approval of all children does not automatically approve the overview. If a child moves backward,
move the overview to a status whose gate remains satisfied; preserve the explicit-user-authority
rule for any rollback from `approved`. Update child documents and the overview navigation before
changing the aggregate status.

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

Organize prose under `docs/` primarily in Chinese. Preserve exact identifiers, CLI syntax, schemas,
and code, and use English for established technical terms or other content that cannot be translated
accurately. Do not force translations that reduce precision. This language rule does not apply to
`AGENTS.md`, Skill documents, or other files outside `docs/`.

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

The user may also insert feedback next to the affected text with this exact form:

```text
<comment>
The user's feedback on the Requirement.
</comment>
```

Only the user may author or explicitly authorize a `<comment>` block. Never create one on the
user's behalf, rewrite agent inference as a user comment, or place a comment between an adjacent
`<question>` and `<answer>` pair. Treat every live comment as unresolved feedback and keep its
non-approved record `draft`.

Before refining the solution, read every comment and resolve each one through one of these paths:

- verify and incorporate direct feedback into the requirement, design, impact, and acceptance
  criteria;
- turn a decision or missing input into a `<question>`, then incorporate the user's adjacent
  `<answer>` or conversational answer;
- surface conflicts between comments, prior decisions, or current facts and obtain the user's
  decision instead of guessing;
- when the user rejects the proposed change, record the resulting decision without presenting the
  rejected content as an implemented requirement.

Acknowledging, moving, or deleting a comment is not resolution. Remove its block only after the
substantive record reflects the result and all resulting questions and impacts are settled. If the
user asks to preserve the feedback, rewrite it as ordinary provenance or decision text rather than
leaving a live comment. A comment added to an `implemented` record moves it to `draft`. For an
`approved` record, do not infer rewrite or rollback authority from the comment alone; ask whether to
reopen the record or create a reciprocally linked follow-up Requirement.

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
in both documents. For a large Requirement, target the overview unless the relationship applies to
one sub-requirement, in which case target that document. Name the relationship direction on each
side; a one-way mention or index-only entry does not satisfy dependency traceability.

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
- every large-Requirement overview reaches all child documents, reports their statuses accurately,
  and satisfies the aggregate gate for its own status;
- Requirement dependencies are navigable in both directions;
- resolved question and answer blocks are removed unless explicitly retained;
- no Requirement transitions to `implemented` or `approved` with a live `<comment>` block; any
  comment found in approved history is left unchanged until the user chooses reopening or a linked
  follow-up, and every removed comment is reflected in substantive text or an explicit decision;
- Details cover every relevant module and match code/tests;
- links form a useful network without duplicate authorities;
- changed public behavior is aligned across Architecture, Details, Skills, code, and tests;
- Markdown links, anchors, diagrams, indexes, and whitespace are valid.

Report any intentionally deferred layer update instead of silently leaving contradictory documents.
