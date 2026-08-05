---
name: write-doctidex-issue-docs
description: Create or maintain user-authorized repository Issue records under docs/issues, including detailed problem evidence, scope, source, disposition, and review associations. Use when the user explicitly authorizes creating a particular Issue from a report or review, revising that Issue, or setting its confirmed, resolved, ignored, or reopened status; do not use review authorization as Issue-record authorization.
---

# Write Doctidex Issue Docs

Record a reported or reviewed problem precisely while preserving the user's authority over whether it
becomes an Issue and how it is disposed. An Issue is project-governance evidence, not a Requirement,
Architecture, Impls, protocol, or implementation authority.

## Establish Authority

1. Read `AGENTS.md`, `docs/issues/index.md`, and the Issue's cited authorities and evidence. Read
   `spec/overview.md` completely before making any protocol claim.
2. Use this Skill only for an individual Issue that the user has explicitly authorized to create,
   revise, or move to a named status. A user report, a review request, a review finding, test
   evidence, validation, repair authorization, silence, or general approval does not grant that
   authority.
3. Do not create a Requirement, alter Architecture or Impls, modify code or tests, or change a
   Published Skill merely because an Issue describes a problem. Obtain the separately applicable
   authorization and use its authoring Skill.

## Create and Describe an Issue

Create only the next unused `docs/issues/<NNNN>-<title>.md` after the user authorizes that concrete
record. Use the initial lowercase status `open`; do not infer `confirmed` from strong evidence. Keep
the navigation table in `docs/issues/index.md` current.

Give every Issue its filename-matched stable ID `DX-ISSUE-<NNNN>`, one visible status, creation date,
source/provenance, affected surfaces, and links to the authorities and evidence used to establish it.
In Chinese-organized prose, describe the observed or reported behavior, triggering conditions,
impact, reproduction or other evidence, expected authority or invariant, uncertainty, and bounded
next decision. For `resolved` or `ignored`, additionally record the user's authorization, rationale,
residual risk, and relevant verification or follow-up links. Do not turn a vague concern into a
factual conclusion.

For a behavior, contract, or conformance Issue, make the evidence independently reconstructible:

- State one concrete scenario with the relevant files, inputs, actors, state transition, or invocation
  order. A reader must not need to infer the failing case from an abstract summary.
- Show the observable erroneous state: a minimal JSON/result fragment, path or record mismatch,
  validator finding, or before/after document value. Distinguish exact observed output from a
  source-derived reachable state.
- State the expected observable behavior under the cited authority, rather than only naming a
  prospective fix.
- When concurrency, interruption, unavailable infrastructure, or an unimplemented contract state
  prevents a one-command reproduction, describe the smallest verified interleaving or setup and
  name that limitation. Do not invent a command transcript, field value, or production incident.

Use short headings such as `具体场景`、`当前错误状态` and `正确行为` when writing Chinese Issue
records. Keep exact identifiers, commands, paths, JSON, and code symbols in their authoritative
form.

## Maintain Status and Associations

Only a clear user instruction naming the Issue and destination state may move it to `confirmed`,
`resolved`, or `ignored`. Require an equally explicit instruction to reopen or otherwise move an
existing record. Preserve the status history and authorization as ordinary prose; do not fabricate a
user quote.

When an Issue originates from or is revisited by review, link to the reviewed scope or finding where
available. `confirmed` and `ignored` records are review correlation inputs: a matching `confirmed`
Issue is reported once with its ID, while a matching `ignored` Issue is suppressed unless the user
asks to include ignored Issues. Matching does not authorize edits to either the Issue or the review
scope.

## Validate and Hand Off

Check that the requested authorization is present, the ID is unique, exactly one allowed lowercase
status is visible, the index link and table agree, all cited paths resolve, and Chinese carries the
explanatory logic. Confirm that status changes have the required explicit user authorization, that
the document preserves a concrete scenario, observable erroneous state, expected behavior, detailed
evidence and disposition, and that no unrelated implementation work was inferred from the Issue.
