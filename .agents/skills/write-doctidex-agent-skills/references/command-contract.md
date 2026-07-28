# CLI Command Contract Checklist

Document each command where it first becomes necessary. Link shared grammar from a foundational
Skill rather than repeating it, but keep task-specific behavior local.

## Invocation and Inputs

- Exact command and subcommand spelling.
- Positional argument forms and whether paths are filesystem, repository-relative, or logical.
- Required, optional, mutually exclusive, repeatable, and value-constrained options.
- Meaning of placeholders and accepted formats.
- Behavior when every optional argument or mode flag is omitted.
- Whether an input must already exist, be a file/directory, or come from another command result.

## Context Selection

- How cwd is used.
- How a root, host, source, or maintenance context is selected.
- Ambiguity behavior and how to provide an exact target.
- When changing cwd reduces parameters and when an explicit source file/path is preferable.

## Effects

- Read-only versus write behavior.
- Public files, Git index, internal runtime state, and working directories that may change.
- Network access, credentials, remote mutations, and offline reuse.
- Preview/apply semantics and whether omission defaults to preview.
- Batch ordering, partial success, rollback, interruption, and preserved results.

## Results

- Operation discriminator and success/warning/blocked states.
- Fields the agent must read to decide the next action, including types and null/absence meaning.
- Independent result domains that top-level status or exit code cannot replace.
- Collection budget, total/returned counts, collapse/group summaries, truncation and opaque cursor.
- Difference between findings, semantic candidates, plans, changes, and next actions.

## Failures

- Stable failure code and user-level cause.
- Affected object and operation that did not complete.
- What remains valid or readable.
- Ordered safe recovery steps.
- Required user permission, credential, selection, or Git action.
- Point at which the agent must stop and report rather than retry.

## Long-Lived and Cursor-Based Operations

When a command watches, subscribes, polls, follows, or streams, also define:

- bounded agent mode versus explicitly opted-in continuous program mode;
- event ordering, duplicate-delivery and replay guarantees, and gap representation;
- cursor opacity, scope, retention, expiry, advancement, acknowledgement, and safe retry behavior;
- schema-version negotiation and handling of unknown fields or event kinds;
- wait timeout, cancellation, interruption, reconnect, backpressure, and slow-consumer behavior;
- whether closing, disconnecting, or retrying preserves unread and already-consumed results.

An agent-facing default must return a bounded page and must not follow indefinitely. Document how an
empty page differs from end-of-stream and how the caller resumes without changing cursor meaning.

Verify every statement against the current public implementation or accepted target Architecture.
Do not expose the internal mechanism used to produce the result.
