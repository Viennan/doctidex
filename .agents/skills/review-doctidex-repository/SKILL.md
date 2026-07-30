---
name: review-doctidex-repository
description: Coordinate an evidence-based review of doctidex repository changes through independent protocol, Skill-surface, requirement/architecture, design-document, and general-engineering lenses. Use only when the user explicitly asks for a review, audit, compliance check, or review-and-repair cycle; do not infer review authorization from ordinary implementation or documentation requests.
---

# Review the doctidex Repository

Run review as an explicitly authorized, evidence-first workflow. Keep independent review passes
separate until aggregation, distinguish impact from requiredness, and never turn a review-only
request into file changes.

## Establish Authorization

Interpret authorization narrowly:

- A request to review, audit, or check compliance authorizes read-only inspection and reporting.
- A request that explicitly includes repair authorizes the review-to-repair loop within the stated
  scope.
- A review-only request does not authorize edits, formatting, generated files, or cleanup.
- An ordinary request to implement, explain, or document something does not trigger this Skill.
- If repair authorization is absent, return findings and stop. Do not ask merely to make optional
  improvements unless a decision is genuinely required.

Preserve unrelated work in the repository in all modes.

## Freeze the Review Scope

1. Read the repository `AGENTS.md` and any closer applicable instructions.
2. Determine whether the user explicitly selected bounded files, commits, Requirements, or another
   scope that overrides the default. A generic request to review the repository or current changes
   does not by itself override the Requirement-based default.
3. If no overriding scope was selected, identify Requirement records active in the current task:
   records created, revised, or implemented for the user's current work, plus records the task
   explicitly names as dependencies. Keep only records whose visible status is `draft` or
   `implemented`. An `approved` record may be supporting authority but is not a default review
   target. If no active non-approved Requirement exists, stop and ask the user to select the review
   scope. For a directory-form Requirement, include its `overview.md` and active child records;
   retain approved children as supporting authority needed to verify the overview aggregate.
4. Record the resulting target, comparison base, relevant commits or worktree diff, and any files
   explicitly excluded from review.
5. Read raw artifacts before forming conclusions: changed files, nearby callers, tests, public
   documentation, and authoritative requirements.
6. Identify which review lenses apply. Mark a lens `not_applicable` with a reason instead of
   silently skipping it.
7. Do not treat uncommitted unrelated files as part of the target merely because they are visible.

## Run Independent Review Passes

Read [review-lenses.md](references/review-lenses.md) before dispatching reviewers. Use a separate
subagent or equivalent isolated pass for every applicable lens:

1. Protocol compliance.
2. Agent-facing Skill content and organization.
3. Requirement fulfillment and Architecture alignment when a new or changed requirement exists.
4. Implementation design-document compliance.
5. General engineering correctness and risk.

Give every reviewer the same frozen raw scope plus only the authorities required for its lens. Do
not give it suspected bugs, expected answers, prior reviewer findings, or proposed fixes. Require
read-only work and the finding schema from
[finding-contract.md](references/finding-contract.md).

Use a prompt equivalent to:

```text
Review the supplied repository scope only through <LENS>. Read <AUTHORITIES> completely where
required. Do not modify files. Report evidence-backed findings using the requested schema, or say
that no finding was established and state residual coverage gaps.
```

If true subagents are unavailable, perform named sequential passes with separate evidence notes and
defer cross-lens reasoning until aggregation. State that independence was reduced; do not pretend
the passes were isolated.

## Aggregate and Adjudicate

Treat subagent output as candidate evidence, not accepted truth.

1. Re-open every cited location and verify the claim against its stated authority.
2. Reject findings based on inferred requirements, implementation preferences presented as
   protocol rules, unspecified protocol behavior presented as nonconformance, or evidence outside
   the frozen scope.
3. Merge duplicates by root cause while retaining the strongest evidence and affected surfaces.
4. Resolve disagreements explicitly. Prefer normative protocol, then the applicable requirement,
   then current Architecture, then implementation Details and local conventions.
5. Assign severity, disposition, and confidence independently according to the finding contract.
6. Keep subjective organization suggestions as `low` or `advisory` and `recommended` unless they
   demonstrably cause incorrect use, missing behavior, or an authoritative-rule violation.
7. When the protocol leaves an implementation feature unspecified, do not issue a protocol finding
   merely because the feature exists. If adding a protocol rule would have unusually high value,
   report it only as an `advisory`/`recommended` specification suggestion and state that current
   conformance is unaffected.

Report findings first, ordered by severity. Then report open questions or assumptions, lens
coverage, and residual test risk. If no finding survives verification, say so clearly.

## Enter the Repair Loop Only When Authorized

When repair was explicitly authorized:

1. Fix verified `must_fix` findings within the user-approved scope.
2. Fix `recommended` findings only when the user included them or the change is necessary to keep
   the repaired surface coherent.
3. Update code, tests, Architecture, Details, Requirements, and Skills together only where the
   behavior spans those layers. Never rewrite historical requirement text to match a repair.
   After completing a Requirement implementation, set it to `implemented`, never `approved`, unless
   the user explicitly directs the approval transition. For a large Requirement, update each child
   independently and change the overview only after its aggregate status gate is satisfied. Resolve
   every user `<comment>` in the authorized record through substantive changes or an explicit user
   decision before removing the block or completing the Requirement. Do not infer authority to
   rewrite an `approved` record from a comment alone.
4. Run proportionate validation.
5. Re-run each affected lens as a fresh independent pass over the repaired artifacts.
6. Aggregate again and repeat until no authorized `must_fix` finding remains or a genuine blocker
   requires user input.

Do not broaden repair authority, discard user work, or continue cycling on subjective preferences.

## Handoff

Make the final response self-contained. Include verified findings or repaired outcomes, validation
performed, lenses not run and why, and unresolved user decisions. Do not expose internal subagent
conversation as evidence; cite repository artifacts and authorities.
