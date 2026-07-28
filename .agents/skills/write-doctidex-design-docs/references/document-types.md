# Implementation Document Types

## Contents

- [Minimal implementation tree](#minimal-implementation-tree)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Details](#details)
- [Cross-layer links](#cross-layer-links)

## Minimal Implementation Tree

After the user explicitly authorizes recording a proposal, start with only the Requirement layer:

```text
impls/docs/<implementation>/
|-- index.md
`-- requirements/
    |-- index.md
    `-- <NNNN>-<kebab-case-title>.md
```

Expand the tree only as authority and implementation mature:

```text
impls/docs/<implementation>/
|-- architecture/                 # Add after design acceptance
|   `-- index.md
`-- details/                      # Add after an implementation exists
    |-- index.md
    `-- <language-or-runtime>/
        `-- index.md
```

Do not create empty topic pages merely to complete the skeleton. Number Requirement records in
historical order using the next unused zero-padded number; re-read the directory before writing so
concurrent work does not reuse an existing number. Name Architecture pages after stable workflows,
interfaces, or domain concepts; name Details pages after concrete implementation responsibilities
rather than copying source filenames mechanically.

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

- stable ID, title, date/status, and provenance;
- user-reviewed requirement intent, clarified and completed with agent assistance rather than
  copied verbatim from raw input;
- scenario and design intent;
- constraints and rejected alternatives when known;
- accepted or rejected outcome;
- implementation and documentation impact;
- links to resulting Architecture and Details;
- superseding or follow-up records.

Before drafting the requirement statement, inspect relevant current Architecture, Details,
implementation, tests, and public surfaces. Check explicit and implicit assumptions against actual
behavior. If an assumption differs, explain the concrete difference and design impact to the user;
use the corrected or intentionally changed premise only after review.

Keep provenance for the source request, but do not treat its exact wording as the requirement
authority. If only source material is known, draft a clearly proposed interpretation and label
unknown decision/outcome fields rather than inventing them or attributing unreviewed additions to
the user.

For a new proposal, create the Requirement first and keep proposed alternatives and target-design
reasoning in that record until a decision is accepted. A hypothetical task or forward-test scenario
is not accepted provenance unless the user explicitly designates it as a repository requirement;
without that authorization, propose content in the response and create no documentation tree.
“Record the following as a Requirement” is sufficient authorization; “brainstorm,” “propose,” or
“forward-test this example” is not.

When the proposal receives its first decision, update the same record's status, decision, outcome,
and impact sections without changing the reviewed requirement intent. A later change, reversal, or
supersession gets a new Requirement record linked to the earlier decision.

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
state that no concrete variant is implemented yet and link to the accepted Architecture that future
Details must realize.

## Cross-Layer Links

Use links to answer useful maintainer questions:

- Architecture to Requirement: why does this constraint exist?
- Requirement to Architecture: what current design resulted?
- Architecture to Details: where is this model realized?
- Details to Architecture: which contract constrains this code?
- Details to Requirement: which exceptional implementation choice was explicitly requested?

Links should create insight, not merely satisfy navigation. Avoid circular prose duplication.
