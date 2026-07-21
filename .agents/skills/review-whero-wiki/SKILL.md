---
name: review-whero-wiki
description: Perform an explicitly user-authorized, holistic review of Whero Wiki for defects, regressions, protocol and implementation consistency, portable Skill conformance, documentation coherence and translation fidelity, and first-time agent usability. Use only when the user explicitly invokes `$review-whero-wiki` or clearly authorizes use of this Skill; never invoke it implicitly for handoff, commit, push, submission, or another workflow.
---

# Review Whero Wiki

Require explicit user authorization before running this Skill. An explicit
`$review-whero-wiki` invocation or a direct instruction to use this Skill is
sufficient. Do not infer authorization from a generic request to review,
finish work, prepare a handoff, commit, push, submit, or draft a PR or MR, or
from another Skill referring to this one. Without authorization, do not spawn
review subagents or begin the review.

Perform a read-only, findings-first review. Read the repository `AGENTS.md`,
identify the requested base and implementation change scope, and include
tracked, untracked, and deleted files. Review repository-authored documentation
as a complete current system, even when only part of it changed. Do not edit
product files or fixtures, alter root Git state, create review comments, add
labels, or change remote state. Disposable scenario artifacts are allowed only
in a task-specific `.tmp` workspace managed and cleaned through
`$test-whero-wiki`.

## Require Xhigh Subagents

Subagents are mandatory. Spawn one independent subagent for each review lens
below and set every subagent's reasoning effort to `xhigh`, `Extra High`, or the
highest equivalent level exposed by the runtime. When the API exposes a
reasoning parameter, set it explicitly. Otherwise instruct the subagent to use
xhigh in its task and report that the inherited setting cannot be independently
verified. Stop if the runtime explicitly caps or refuses the required level.

Pass each subagent the repository root, review base or worktree scope, this
Skill's full path, and raw artifacts such as the diff and relevant files. Do
not pass suspected findings, expected answers, or another subagent's output.
Run the subagents concurrently when capacity allows.

### Implementation And Portable Skill

Review runtime correctness, regressions, failure behavior, test coverage, and
cross-module contracts. Treat `whero-wiki/` as a portable Skill:

- validate its Skill structure and `agents/openai.yaml`;
- verify bundled paths resolve relative to the Skill root;
- reject dependencies on the repository root, root `AGENTS.md`, `.agents/`,
  `.venv`, `.tmp`, or `asserts/`;
- compare advertised commands, fields, versions, and workflows with scripts,
  protocol documents, references, and tests;
- verify every user-facing script and CLI behavior is documented sufficiently
  for correct use without reading Python source;
- check dependency declarations and read-only use from an unrelated working
  directory when relevant.

### Documentation System And Translation

Review the full repository-authored documentation set as one coherent system,
not as isolated changed paragraphs. Read the root `README.md` and `AGENTS.md`,
the portable `whero-wiki/SKILL.md`, root Wiki framework documents, all active
protocol documents in both languages, every file under `whero-wiki/references/`,
repository-local Skills, and their `agents/openai.yaml` metadata. Account for
the explicitly historical role of any legacy reference instead of treating it
as active guidance. Use the product-layer rules in `AGENTS.md` to assess
placement and authority:

- normative definitions belong in `whero-wiki/spec/`, with synchronized
  English and Chinese files;
- task workflow detail belongs in references, while `SKILL.md` remains the
  concise user and agent interface;
- implementation and tests enforce rather than silently redefine the protocol;
- self-hosted Wiki framework files remain root-only;
- collected fixtures stay unchanged and product navigation remains coherent.

Build a cross-document view of terminology, versions, active versus draft
status, metadata fields, path and ownership rules, boundary behavior, workflow
ordering, script names and options, expected outputs, and recovery guidance.
Flag stale iteration remnants, contradictory or duplicated definitions,
misplaced content, broken reasoning sequences, terminology drift, wrong links,
and locally correct passages that become inconsistent or illogical in the
larger document set. Do not limit findings to newly edited lines when an edit
exposes an existing whole-system contradiction.

Compare every English normative protocol file with its Chinese counterpart at
the same relative path. Check section structure and meaning, not literal word
choice. Treat differences in normative force, negation, scope, conditions,
exceptions, path semantics, ownership, state transitions, examples, or version
status as significant semantic drift. Flag missing content or material meaning
that exists in only one language. Preserve English as normative while requiring
the Chinese text to communicate the same contract without significant semantic
deviation.

### First-Time Agent Usability

Act as an agent seeing the `whero-wiki` Skill for the first time. Follow only
the guidance intentionally exposed by that Skill and its routed references.
Do not read script source to learn how to invoke a supported workflow. Before
execution, confirm the Skill and routed documentation state each exposed
script's purpose, prerequisites, working-directory and path expectations,
required and important optional arguments, defaults, dry-run versus mutating
behavior, outputs or created artifacts, success criteria, common failures, and
recovery or next steps. Needing to inspect implementation code to discover any
of this information is a documentation defect. Source may be inspected later
to verify a suspected mismatch, but not to compensate for missing guidance.

Exercise representative raw scenarios relevant to the change, including query,
safe maintenance or dry-run, and View creation or expansion. Include boundary
or recovery cases when affected.

Report missing prerequisites, ambiguous source selection, dead-end commands,
unnecessary protocol loading, unclear authorization boundaries, weak error
recovery, or functionality that is advertised but cannot be discovered and
used correctly. Do not treat unavailable View content as a defect unless the
contract says it should be available.

## Verify And Report

The lead reviewer must verify each reported issue against the actual files or
command output. Return every substantiated subagent finding; omit only exact
duplicates or demonstrably false findings, and note any disputed conclusion.
Use the testing Skill for read-only validation when it materially confirms a
finding. Synthesize documentation findings across the entire document system;
do not downgrade a contradiction merely because each individual passage reads
plausibly in isolation.

Return raw Markdown with findings first, ordered by severity. Number every
finding and include:

- severity;
- file path and line number, or the failing command;
- observed evidence and violated contract;
- user, agent, or runtime impact;
- the smallest coherent correction.

Then list open questions, checks performed, skipped coverage with reasons, and
residual risk. If there are no findings, state that explicitly and still name
remaining test or scenario gaps.
