# Implementation Document Types

## Contents

- [Minimal implementation tree](#minimal-implementation-tree)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Details](#details)
- [Cross-layer links](#cross-layer-links)

## Minimal Implementation Tree

After the user explicitly authorizes recording an ordinary proposal, start in the project-wide
Requirement layer:

```text
docs/
`-- requirements/
    |-- index.md
    `-- <NNNN>-<kebab-case-title>.md
```

Expand the tree only as authority and implementation mature:

```text
docs/<implementation>/
|-- architecture/                 # Add when the design becomes current
|   `-- index.md
`-- details/                      # Add after an implementation exists
    |-- index.md
    `-- <language-or-runtime>/
        `-- index.md
```

Use a single numbered file for an ordinary Requirement. When the user selects a directory for a
large Requirement, use one project-wide number for the whole directory:

```text
docs/requirements/
`-- <NNNN>-<kebab-case-title>/
    |-- overview.md
    |-- <NN>-<kebab-case-subrequirement>.md
    `-- ...
```

`overview.md` owns the overall stable ID, description, scope, aggregate status, and child
navigation. Each child owns a stable ID derived from the overall ID and an independent lifecycle
status; children do not consume project-wide numbers. Keep filenames stable, link every child from
the overview, and link the overview from `docs/requirements/index.md`. Do not convert an existing
single-file record without user direction.

Do not create empty topic pages merely to complete the skeleton. Number Requirement records across
the project in historical order using the next unused zero-padded number; re-read
`docs/requirements/` before writing so concurrent work does not reuse an existing number. Keep
existing stable IDs when moving records into the shared directory. Name Architecture pages after
stable workflows, interfaces, or domain concepts; name Details pages after concrete implementation
responsibilities rather than copying source filenames mechanically.

## Architecture

Purpose: describe what the current implementation design is, beginning with the user surface and
then exposing the language-neutral model beneath it.

Recommended structure:

1. Scope, audience, authority, and non-goals.
2. Concrete scenario/problem matrix.
3. Human, agent, and program mental models.
4. Public interfaces and exact observable contracts.
5. Workflow-by-workflow behavior, results, and failures.
6. Public/internal information boundary.
7. Domain concepts with every property and visibility.
8. Subsystem responsibilities and non-responsibilities.
9. Lifecycles, invariants, concurrency, and partial success.
10. Links to Requirements history and implementation Details.

Keep programming language details out unless explicitly authorized. CLI syntax and schemas may be
language-neutral public interfaces; source filenames, classes, state paths, caches, and library
mechanics belong in Details.

## Requirements

Purpose: preserve why and how the design evolved. A record is historical evidence, not current
interface authority.

Include:

- stable ID, title, date, affected surfaces, provenance, and one of the exact lowercase statuses
  `draft`, `implemented`, or `approved`;
- user-reviewed requirement intent, clarified and completed with agent assistance rather than
  copied verbatim from raw input;
- scenario and design intent;
- constraints and rejected alternatives when known;
- accepted or rejected outcome;
- implementation and documentation impact;
- links to resulting Architecture and Details;
- reciprocal links for dependencies, refinements, supersession, and follow-up records.

Before drafting the requirement statement, inspect relevant current Architecture, Details,
implementation, tests, and public surfaces. Check explicit and implicit assumptions against actual
behavior. If an assumption differs, explain the concrete difference and design impact to the user;
use the corrected or intentionally changed premise only after review.

Keep provenance for the source request, but do not treat its exact wording as the requirement
authority. If only source material is known, draft a clearly proposed interpretation and label
unknown decision/outcome fields rather than inventing them or attributing unreviewed additions to
the user.

For a new proposal, create the Requirement first with status `draft` and keep alternatives and
target-design reasoning there until implementation. A hypothetical task or forward-test scenario is
not repository provenance unless the user designates it as a Requirement; without that
authorization, propose content in the response and create no documentation tree. Any clear intent
equivalent to "create a requirement" or "record this requirement" is sufficient authorization and
requires creating the next numbered `draft` record from the user's initial intent. "Brainstorm,"
"propose," or "forward-test this example" alone is not.

While a record is `draft`, improve it from the user's stated intent without adding unrequested scope.
Use temporary `<question>...</question>` blocks for unresolved decisions; place a document-supplied
`<answer>...</answer>` immediately after its question. The user may answer in conversation instead.
After incorporating the decision, remove both blocks unless the user explicitly preserves them.

The user may place `<comment>...</comment>` beside the text it addresses. Only the user may author
or explicitly authorize a comment block; an agent uses `<question>` rather than fabricating user
feedback. A comment must not split an adjacent question/answer pair. Treat every live comment as
unresolved: verify and incorporate direct feedback, or use question/answer when a decision,
ambiguity, or conflict remains. Acknowledgement or deletion alone is not resolution. Remove the
comment only after substantive text and all resulting impacts reflect the outcome; preserve needed
history as ordinary provenance or decision text instead of a live comment block.

A non-approved record with a live comment remains `draft`. A comment added to an `implemented`
record returns it to `draft`. A comment in an `approved` record does not itself authorize rewriting
or downgrading history; preserve the record and ask the user whether to reopen it or create a
reciprocally linked follow-up Requirement.

Mark the record `implemented` after the agent completes and validates it. User feedback may move it
back to `draft` for revision and later to `implemented` again. Set `approved` only when the user
explicitly accepts the current implementation as PR/MR-ready. Do not downgrade or rewrite an
`approved` record without explicit user direction; a later change normally gets a new Requirement
with reciprocal links.

For a large Requirement, apply that lifecycle independently to every child. Keep the overview
`draft` while any child is `draft`; allow it to become `implemented` only when every child is
`implemented` or `approved`; and allow it to become `approved` only when every child is `approved`
and the user explicitly approves the overall Requirement. Child transitions never automatically
change other children. If a child moves backward, the overview must return to a status whose gate
is still satisfied, while any rollback from `approved` continues to require explicit user direction.
Apply comment handling to the document that contains the block: a child comment affects that
child's status and therefore the overview gate, while an overview comment does not rewrite child
statuses.

## Details

Purpose: explain how a concrete language/runtime implementation realizes Architecture and provide
a durable code-reading map.

For each module or subsystem include:

| Topic | Required explanation |
|---|---|
| Responsibility | What it owns and explicitly does not own. |
| Callers | Which modules/workflows should use it and when. |
| Dependencies | Direction and reasons; forbidden reverse dependencies where relevant. |
| Types/functions | Main entry points and all attributes or fields. |
| Effects | Files, processes, network, state, destructive or recoverable behavior. |
| Failures | Error types, preserved results, retry and escalation boundary. |
| Concurrency | Locks, atomic publication, races, partial success and cleanup. |
| Usage | Small realistic code example or call sequence. |
| Evidence | Tests and known gaps. |

Separate current limitation lists from target design. Do not duplicate published Skill tutorials;
link public command contracts back to Architecture.

Do not create implementation claims before code exists. It is acceptable for `details/index.md` to
state that no concrete variant is implemented yet and link to the current Architecture that future
Details must realize.

## Cross-Layer Links

Use links to answer useful maintainer questions:

- Architecture to Requirement: why does this constraint exist?
- Requirement to Architecture: what current design resulted?
- Architecture to Details: where is this model realized?
- Details to Architecture: which contract constrains this code?
- Details to Requirement: which exceptional implementation choice was explicitly requested?
- Requirement to Requirement: what does this record depend on, refine, supersede, or trigger next?

For every Requirement-to-Requirement relationship, add a navigable link in both records and name
the direction from each side. Links should create insight, not merely satisfy navigation. Avoid
circular prose duplication.
