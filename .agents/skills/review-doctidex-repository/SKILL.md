---
name: review-doctidex-repository
description: Coordinate an evidence-based review of doctidex repository changes through independent protocol, agent-Skill, Requirement, Architecture, Impls, and engineering lenses. Use only when the user explicitly requests a review, audit, compliance check, or review-and-repair cycle; ordinary implementation or documentation work does not authorize this Skill.
---

# Review the doctidex Repository

Review a frozen, user-authorized scope through independent lenses, verify every candidate against its
authority, and enter repair only when the user separately authorizes it.

## Establish Authorization and Scope

Classify the request before reading for findings:

- Review-only is read-only. Do not edit, commit, message externally, or broaden scope.
- Review-and-repair permits only the named repair scope; do not infer repair authority from a review
  request or a discovered defect.
- An ordinary writing, implementation, or validation request is not review authorization.

Unless the user selects another scope, review active `draft` or `implemented` Requirements in the
current task and their affected artifacts. Approved records may support authority but are not default
targets. If no active non-approved Requirement exists, ask the user to select a scope.

For a directory-form Requirement, include `overview.md`, active children, and approved children
needed to verify the aggregate. Record the exact target, comparison base, relevant commits or
worktree state, and excluded unrelated changes.

When "current changes" has no named base, compare all task-attributable staged, unstaged, and
untracked work to `HEAD`. If task changes include commits, use the parent of the first attributable
commit and include later commits plus the worktree. Ask when more than one base remains plausible.

Read raw changed artifacts, nearby callers, tests, public surfaces, and required authorities before
forming conclusions. Preserve unrelated dirty work.

## Run Independent Lenses

Read [review-lenses.md](references/review-lenses.md) to select authorities and
[finding-contract.md](references/finding-contract.md) for output. Run each applicable lens with a
fresh subagent or equivalent isolated pass:

1. Protocol compliance.
2. Agent-facing Skill surface.
3. Requirement fulfillment and lifecycle.
4. Architecture design.
5. Impls realization.
6. General engineering.

Give every reader the same frozen raw scope plus only its required authorities. Do not leak suspected
bugs, expected answers, previous findings, or proposed fixes. Require read-only work and the finding
schema. Mark a lens `not_applicable` with a reason instead of silently skipping it.

If isolated agents are unavailable, perform named sequential passes and report reduced independence.
This fallback cannot satisfy a mandatory fresh cold read. Retry one failed or malformed pass once,
then use the fallback where possible; never count missing evidence as a clean pass.

Architecture cold reads follow `$write-doctidex-architecture-docs`, including its two-round maximum
and materiality threshold. Review orchestration does not define a second cold-read procedure.

## Aggregate and Adjudicate

Treat every reviewer result as candidate evidence:

1. Re-open each cited location and verify it against the named authority.
2. Reject findings based on inferred requirements, preferences presented as rules, protocol silence,
   or evidence outside the frozen scope.
3. Merge duplicate root causes while preserving the strongest evidence and affected surfaces.
4. Resolve conflicts in this order: normative protocol, applicable Requirement, current
   Architecture, applicable Impls, then implementation/tests and local convention.
5. Assign severity, disposition, and confidence independently under the finding contract.
6. Keep organization preferences advisory unless they cause incorrect use or violate an authority.

Report verified findings first by severity, followed by blocking questions, lens coverage, validation,
and residual risk. Say explicitly when no finding survives.

## Repair Only When Authorized

For an authorized repair:

1. Fix verified `must_fix` findings within scope; include `recommended` findings only when authorized
   or required for coherence.
2. Use the applicable authoring Skill before editing Requirement, Architecture, Impls, or agent
   Skills. Those Skills own lifecycle, history, design, realization, and metadata rules.
3. Align other authorized code, tests, and public surfaces when behavior spans them.
4. Run proportionate validation and the validation required by each changed Skill.
5. Re-run only affected lenses as fresh passes and aggregate again.

Stop when no authorized `must_fix` finding remains or user input is genuinely required. Do not cycle
on subjective preferences. A validator failure is evidence, not mutation authority; preserve valid
results and report any validation that could not run.

## Hand Off

Provide a self-contained report with verified findings or repairs, validation, lens coverage,
reduced-independence or missing evidence, and unresolved user decisions. Cite repository authorities;
do not expose raw subagent conversation.
