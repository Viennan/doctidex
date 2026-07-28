# Agent Skill Content Checklist

## Trigger and Metadata

- Frontmatter contains only `name` and a comprehensive `description`.
- Description says what the Skill does and all contexts that trigger it.
- Non-trigger boundaries prevent accidental mutation or review.
- Folder name, frontmatter name, display metadata, and `$skill-name` prompt agree.
- UI short description is 25–64 characters and all YAML strings are quoted.

## Audience and Information Boundary

- Published Skill assumes an installed product, not this source repository.
- Repository-maintenance Skill explicitly uses repository authorities where necessary.
- User concepts are sufficient to complete the workflow without source or implementation docs.
- Internal cache, state, lock, worktree management, test, and debug details are absent from published
  Skills.
- Public maintenance paths and other task-essential outputs are not hidden merely because their
  implementation is internal.

## Structure and Progressive Disclosure

- One foundation owns shared mental model, terms, grammar, outputs, and safety.
- Specialized Skills own only their workflow additions.
- Runtime reading order is explicit, conditional, shallow, and acyclic; “if not already read” links
  never cause the foundation or a specialist to be reopened in one workflow.
- Every reference is directly linked from `SKILL.md` with a load condition.
- No duplicated reference content, unused resource directories, README, or auxiliary process docs.
- `SKILL.md` is concise, imperative, and below 500 lines.

## Workflow Completeness

- Specialized terms are defined before use.
- Preconditions, inputs, context, workflow, observable result, and failure state are clear.
- CLI commands satisfy the complete command contract checklist.
- Native file/search/shell/edit/Git tools remain available.
- CLI work is deterministic and non-AI; semantic authorship remains with the agent.
- Collection output is bounded and narrowing/pagination guidance is practical.
- Long-lived and cursor-based commands define ordering, replay/gaps, cursor lifetime, schema
  compatibility, waiting, cancellation, interruption, backpressure, and bounded agent defaults.
- Failures include preserved results, actions, escalation, and user input requirements.

## Validation

- Changed Skill passes the Skill validator.
- `agents/openai.yaml` matches the final Skill.
- Published containing plugin passes plugin validation.
- Forward tests use fresh agents and raw realistic artifacts without leaked expected answers.
- Tests include normal, clean/no-op, ambiguous, failure, and authorization-boundary requests.
