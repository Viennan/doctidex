---
name: doctidex-prose-standard
description: Use when writing, reviewing, restoring, trimming, or auditing prose in the Doctidex repository, including deciding where documentation or comments are required across Markdown, code comments and source-level documentation, test comments, prompts, descriptions, diagnostics, CLI or UI strings, and scaffolding documentation.
---

# Doctidex Prose Standard

Write enough to preserve the contract, then remove reasoning transcripts, repetition, and decoration. A contract is an obligation, invariant, precondition, postcondition, or compatibility promise that a caller, callee, implementer, producer, or consumer relies on. This skill owns editorial judgment and required prose coverage. It is guidance, not a script.

Treat `contract`, `boundary`, `shape`, `surface`, `seam`, `gate`, and `vocabulary` as terms to check before use, not banned words. First ask whether the exact rule, API, field set, type, validation, timing point, component split, or failure states the fact better. Keep a term when it names the exact technical subject, including caller/callee contracts and security/process boundaries.

Comments describe non-obvious contracts or rationale that code cannot express; they do not restate what code already implies.

## Inputs and exclusions

Require an explicit `scope`. If it is missing, report the required input and stop; do not infer a repository-wide scope or begin an interview.

Accept `mode: automatic | interactive`; default to `automatic`. Enter interactive mode only when the user explicitly requests questions or calibration.

`mode` controls questions, not write authority. Review and audit tasks report findings without editing; explicitly requested write, fix, or trim tasks apply clear changes.

Treat generated catalogs, snapshots, and fixtures as derivative. Edit the owning source or scenario first, then regenerate the artifact. When a generator extracts a summary from owner prose, make the extracted sentence complete for that surface.

## Preserve the complete proposition

Before editing, identify every proposition in the passage. Preserve each relevant:

- actor and action;
- condition, timing, and ordering;
- modality such as must, may, or never;
- negative guarantee and exception;
- ownership, side effect, failure mode, and consequence.

Remove adjectives, repetition, and narration only when every factual clause survives and the result is clearer. A smaller word count alone is not an improvement.

Keep a complete local contract at the point of use: behavior, failure, ownership, and consequence that a caller or maintainer needs there. Aggressively link to the owning document for architecture, rationale, algorithms, history, or extended examples. One explanation has one home; essential contract facts may repeat locally. Use path-plus-fragment links to provide precise reference locations for concepts and local information.

Keep non-obvious rationale when omitting it could plausibly cause misuse or an incorrect simplification. Otherwise state the consequence and link the rationale home.

## Expression modes

Prefer diagrams, tables, code blocks, and similar non-prose forms when they reduce explanatory text and improve comprehension, logical clarity, or brevity. Keep prose as the primary carrier of logic and content organization. Use non-prose forms only when they lower the reader's burden; do not construct complex, HTML-like markup that makes the passage harder to understand.

## Required coverage by prose location

This is not a one-way shortening pass. Add or restore prose when code, types, and structure do not communicate a required contract below. Do not add a comment when those facts are already obvious locally.

- **Public API documentation:** document caller-visible return distinctions, exceptions, side effects, ownership, timing, cancellation, and durability.
- **Internal comments and code-local documentation:** orient non-local structure and obviously complicated local structure, including invariants, ordering, ownership, security boundaries, and surprising failure behavior. Delete control-flow narration and code restatement.
- **Module-level documentation:** state the module's role, dependencies, responsibilities, and non-obvious architecture choices; link architecture choices to their owning explanation.
- **Tests:** explain only non-obvious test design—why a fixture, assertion, platform accommodation, real entry path, or indirect observation is necessary. Delete walkthroughs and inventories.
- **Guides and cookbooks:** include prerequisites, required actions, the real entry path, observable verification, and concise warnings.
- **READMEs:** include the consumer contract: configuration, semantics, failures, limitations, extension points, and model-visible effects. Keep durable gaps and maintainer traps, not ordinary cleanup inventories.
- **Skills and agent instructions:** state behavioral guardrails and explicit scope limitations such as “guidance, not a script/checklist.” Keep the workflow concise and link its source of truth.
- **Examples and configuration comments:** explain access limits, non-obvious wiring or load order, security stance, replay behavior, exceptions, and likely misuse. Do not narrate entries that the configuration already shows.
- **Prompts and visible strings:** treat wording as behavior. Inspect generated output and run behavior validation or state why no snapshot applies.
- **Diagnostics:** name the failing subject or path, violated rule, and correction when it is non-obvious. Remove internal execution narration.

Preserve searchable mechanism names and meaningful modal, temporal, or negative emphasis. Normalize decorative emphasis only.

## Workflow

1. Confirm the scope, mode, current branch or PR base, and applicable `AGENTS.md` files. Do not inspect unrelated branches.
2. Read the applicable `AGENTS.md` guidance and the owning code or document before judging a passage. For calibration or unfamiliar cases, read [the distilled examples](references/examples.md).
3. Inspect the requested scope, not only the largest files. Use searches and word counts to find candidates, then judge passages semantically.
4. Classify each candidate as keep, add, trim, restore, restructure, or defer. Apply clear changes only when the task authorizes edits; do not manufacture edits to satisfy a deletion target.
5. Update the owner before derivative artifacts. Re-check analogous passages after learning a new rule.
6. Run the narrow relevant checks, applicable documentation gates, `git diff --check`, and behavior tests for visible strings.
7. Report the inspected scope, clear changes, deliberate keeps, deferred cases, and checks actually run.

## Borderline decisions

A case is borderline only when at least two versions satisfy the complete-proposition rule but trade accepted principles, and this skill does not already resolve the tradeoff. A rewrite with one proposition-preserving answer is not borderline.

In automatic mode, apply clear edits when authorized and report genuine borderline cases without asking questions. Do not weaken a proposition to make progress.

In interactive mode, group analogous passages under the governing principle. Present two or three viable versions, recommend one, and state the factual or structural difference. Do not offer inferior distractors. Use the user's requested channel; when calibrating a PR through inline comments, place the recommended provisional version in the diff and attach the alternatives to that exact line.

After the user decides, distill the principle and versions into [the examples](references/examples.md), without task history or reviewer narration, and apply the learned rule to every analogous passage in scope.
