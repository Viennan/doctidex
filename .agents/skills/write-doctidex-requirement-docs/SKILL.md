---
name: write-doctidex-requirement-docs
description: Create, refine, implement, or maintain project Requirement records under docs/requirements, including numbered files, user-selected large Requirement directories, lifecycle status, user questions and comments, authorization boundaries, dependencies, historical intent, and cross-layer implementation tracking. Use when the user asks to create or record a requirement, comments on an active Requirement, changes an artifact governed by an active Requirement, or asks to implement or approve recorded work; do not create historical records for ordinary documentation of already-current behavior without such intent or an active record.
---

# Write doctidex Requirement Docs

Preserve reviewed intent and user-agent decisions while keeping proposals, current design, concrete
implementation, and approved history visibly distinct.

## Decide Whether a Requirement Exists

Treat intent equivalent to "create a requirement" or "record this requirement" as authorization to
create the next project-wide numbered `draft` record immediately. Re-read `docs/requirements/`
before allocating its zero-padded number, identify affected artifact and repository surfaces, and
link it from the shared index.

Give each record a stable ID, title, date, one status, source/provenance, affected surfaces, reviewed
intent, design decisions, implementation impact, acceptance criteria, and relevant current-artifact
links. Keep protocol relationships explicit without presenting non-normative intent as protocol.

Do not create a Requirement solely because the user asks to document already-current behavior,
provides a hypothetical example, or requests a forward test. If a corresponding active Requirement
already governs a requested Architecture, Impls, Skill, code, or other artifact change, update that
record before modifying the artifact. When none exists, continue without inventing history unless
the user expresses requirement-recording intent.

## Verify the Premise

Before refining a draft, inspect the relevant current Architecture, Impls, implementation, tests,
and public surfaces. Test explicit and implicit premises against actual behavior. If a premise is
wrong, explain the concrete difference and design impact to the user before recording a corrected
premise or intentional change. Read `spec/overview.md` completely before making a protocol claim.

Keep the record focused on the user's scope. Preserve reviewed intent, design intent, decisions,
implementation impact, provenance, and outcome without copying raw conversation or attributing
unreviewed inference to the user.

For records under `docs/`, Chinese must carry the heading, prose, and table logic. Preserve exact
identifiers, commands, paths, schemas, code symbols, established technical terms, and quotations in
English when needed, but do not leave a long English-only explanatory passage behind Chinese
headings or a Chinese lead-in.

## Maintain Status

Give every standalone Requirement, large-Requirement `overview.md`, and sub-requirement exactly one
visible lowercase status:

- `draft`: user-agent discussion, design, implementation, or unresolved feedback remains.
- `implemented`: the agent completed and validated the record, but the user has not accepted it for
  a PR or MR.
- `approved`: the user explicitly accepts the current implementation as PR/MR-ready.

Move repeatedly between `draft` and `implemented` as feedback changes pre-approval work. Only an
explicit user instruction may set `approved` or move approved history backward. Never infer approval
from implementation, tests, review results, praise, silence, or continuation to another task.

## Collaborate with the User

During `draft`, complete and organize the user's intent without adding unrequested features. Use a
temporary block only for a decision that genuinely requires the user:

```text
<question>
What decision is needed?
</question>
<answer>
The user's adjacent in-document answer, when supplied.
</answer>
```

The user may answer in conversation. Incorporate the decision and remove the resolved pair unless
the user explicitly asks to preserve it.

The user may place feedback beside Requirement text:

```text
<comment>
The user's feedback.
</comment>
```

Only the user may author or explicitly authorize a comment. Never fabricate one, rewrite inference
as user wording, or split an adjacent question/answer pair. A live comment is unresolved: verify and
incorporate direct feedback, ask for a needed decision, or record the user's explicit choice not to
change the design. Deletion or acknowledgement alone is not resolution. Remove the block only after
substantive text, implementation impact, dependencies, questions, and acceptance criteria reflect
the outcome; preserve needed provenance as ordinary prose.

A live comment keeps a non-approved record `draft` and returns an `implemented` record to `draft`.
For an approved record, preserve status and content until the user explicitly chooses to reopen it
or create a reciprocally linked follow-up.

## Structure Records and Dependencies

Use one numbered Markdown file by default. When the user selects a large Requirement, allocate one
project-wide number to a directory containing `overview.md` and independently statused child files.
The overview owns overall ID, scope, aggregate status, and navigation; each child owns a derived
stable ID, intent, decisions, impact, acceptance criteria, and status.

Children do not consume project-wide numbers. Do not convert an existing standalone record to a
directory without user direction, and keep every child reachable from the overview.

Keep the overview `draft` while any child is `draft`. It may be `implemented` only when all children
are `implemented` or `approved`, and `approved` only when all children are approved and the user
explicitly approves the overview. Changing the overview never changes child statuses. Apply comment
handling to the document containing the comment, then update the aggregate gate.

Record dependencies, refinements, supersession, and follow-ups with navigable links in both
participating Requirements. Link the large overview by default and a child when the relationship is
narrower. Describe the direction from each side.

Do not add even a backlink to an approved Requirement without explicit user authority to edit that
history. Record the outbound relationship and exact pending reciprocal edit in the active draft,
report the authorization gap, and keep the relationship incomplete until the user permits the
approved-history change or chooses another linked follow-up structure.

## Coordinate Artifact Work

For direct feedback on an artifact governed by an active Requirement:

1. Record the feedback, resulting intent, impact, and acceptance criteria here first.
2. Return `implemented` to `draft` when the solution changes.
3. Use `$write-doctidex-architecture-docs` for common current design and
   `$write-doctidex-impls-docs` for condition-specific realization; use both in that order when the
   change spans them. Load only a Skill not already read, and resume this workflow without reopening
   an earlier Skill.
4. Align code, tests, public Skills, and other authorized layers when behavior spans them.
5. Validate the complete authorized result, record evidence, then set the Requirement to
   `implemented`. Never set it to `approved` without explicit user direction.

Keep undecided target design in the draft Requirement. Update current Architecture and Impls only
after factual evidence supports an observable current artifact; evidence may be non-code, but a
reviewed target alone is not current design.

Prioritize current Architecture and Impls quality over historical link compatibility. Do not
rewrite approved Requirements or archive prose to match current organization. Repair a historical
link only with user authority and only mechanically when one unique successor preserves its
meaning; otherwise report the exact pending authorization and keep the active Requirement `draft`.

## Validate and Hand Off

Check status and approval provenance, all live comments and question/answer pairs, large-Requirement
aggregate gates, reciprocal dependencies, affected-surface links, acceptance criteria, navigation,
whitespace, and whether Chinese actually organizes explanatory logic. Treat English-only prose as a
validation failure unless it is an exact identifier, command, path, schema, code symbol, established
technical term, or quotation. Record completed validation and any out-of-scope gap without silently
expanding the Requirement. Mark `implemented` only when all authorized work is complete and no live
comment or blocking decision remains.
