# Independent Review Lenses

Use only the lenses applicable to the frozen review scope. Each lens must inspect raw artifacts
independently and must distinguish normative requirements from implementation preferences.

## Protocol Compliance

Authority: read `spec/overview.md` completely. Background under `spec/refs/`, Requirements,
Architecture, implementation documents, and existing code are not protocol authority, but they are
required review evidence when the scope includes an implementation variant.

Check both materialized directory trees and the implementation design, code, configuration, CLI,
and tests that can produce, accept, interpret, validate, resolve, traverse, mutate, or report those
trees. Determine whether any supported input, lifecycle transition, failure path, or partial result
can yield behavior or observable state that violates protocol requirements. Cover frontmatter,
root/index/log semantics, filters, links, reserved paths, mounts, and conformance claims; the absence
of a currently nonconforming fixture is not evidence that the implementation conforms.

Also check that an implementation-specific rule is not mislabeled as protocol and that a protocol
placeholder is not silently expanded into a requirement. Trace each suspected implementation defect
to the exact protocol rule and the design or execution path that can expose the violation.

Report the exact protocol section and affected behavior. Do not report a different implementation
choice as a violation when the protocol leaves it open.

The absence of a protocol rule is not evidence of nonconformance. An implementation may add
observable features in unspecified areas provided they do not violate an existing rule or falsely
claim normative status. When standardizing such a feature would have substantial future value,
report a specification suggestion as `advisory` and `recommended`; do not classify it as `high` or
`must_fix` on the basis of unspecified behavior alone.

Apply these adjudication boundaries:

- Protocol mount and maintenance semantics do not prescribe a CLI, source-identity algorithm,
  revision-comparison method, writable-root construction, scope command, reuse policy, replanning
  procedure, or agent scheduling strategy. Review those choices against the implementation's
  accepted Requirements and current Architecture. Report them under this lens only when their
  observable result violates an actual protocol boundary, such as writing through a mount path.
- Treat `protected` as the default authority boundary for ordinary tree-scoped maintenance, not as
  irreversible storage. Explicit user direction may authorize an exact protected target or a
  protection-configuration change. Report silent, inferred, or over-broad writes, but do not report
  the existence of this explicit override path as a protocol violation.
- `atomic_entries` defines how the responsible index organizes a directory. It does not create a
  separate content or link root and does not require links inside the unit to remain below the
  atomic directory. Evaluate a link against the document's actual doctidex link root and applicable
  mount rules; leaving the atomic directory alone is not an escape, while crossing that actual link
  root remains subject to the general protocol rule.

## Agent-Facing Skill Surface

Authority: the `Agent-Facing Skill Design` section of `AGENTS.md`, the changed Skills and metadata,
and the public CLI behavior those Skills claim. Use `$write-doctidex-agent-skills` when deeper
authoring guidance is needed.

Check installed-product wording; user-only information; explicit acyclic reading chains; term
definitions; exact commands, arguments, defaults, root selection, effects, network, batch and
pagination behavior; native-tool freedom; deterministic non-AI CLI boundaries; bounded output;
actionable failures; and metadata/plugin validation. A foundational plus specialized Skill must be
sufficient without source code, implementation docs, `--help` trial and error, or repository-local
debug instructions.

Treat stylistic preferences as advisory unless they cause ambiguity, unsafe action, repeated
guessing, or a false description of the public surface.

## Requirement Fulfillment and Architecture Alignment

Apply this lens when the user request introduces or changes behavior, or when a Requirements record
is part of the review scope.

Authority order:

1. The applicable record under `docs/requirements/`.
2. Current related documents under `docs/<implementation>/architecture/`.
3. Concrete implementation and tests.
4. `docs/<implementation>/details/` as a code map, not as authority over current Architecture.

Build a trace from each requirement statement to observable behavior, implementation, tests, and
public documentation. Verify the result actually solves the stated scenario instead of merely
adding a command, field, or placeholder. Check negative requirements and failure behavior as well
as the happy path.

Flag deviation from Architecture unless the Requirement explicitly changes that design. When it
does, require the current Architecture to be updated while preserving the historical Requirement.
If a new requirement lacks a corresponding record where the repository expects one, report the
traceability gap without inventing historical wording.

Verify that every reviewed Requirement uses exactly `draft`, `implemented`, or `approved`; that
agent-completed but unconfirmed work is `implemented`; and that `approved` or any rollback from it
has explicit user provenance. Check every inter-Requirement dependency from both ends. During
`draft`, unresolved `<question>` blocks may remain, with an immediately adjacent `<answer>` when the
user answered in-document; resolved pairs should be incorporated and removed unless explicitly
retained.

## Implementation Design Documents

Authority: `Implementation Documentation Design` in `AGENTS.md`, plus the current document tree.
These principles apply to every implementation under `docs`, not only `doctidex-git`. Use
`$write-doctidex-design-docs` for the full authoring contract.

Check that Architecture starts from concrete user problems, mental models, workflows, observable
results, and failures before internal models; remains language-neutral except where explicitly
authorized; and defines subsystem responsibilities, non-responsibilities, constraints, concepts,
and every property. Check that Requirements preserve source wording, intent, decisions, outcomes,
and implementation impact without retroactive rewriting. Check that Details explain how current
code realizes Architecture, including module callers, dependencies, types/functions, attributes,
side effects, errors, concurrency, examples, tests, and known limitations.

Verify current design, historical intent, and implementation fact are visibly distinct but linked
into a useful knowledge network. Look for duplicate authorities, orphan documents, stale links,
language-specific leakage into Architecture, source listings without design explanation, and
published Skill tutorials duplicated in Details.

## General Engineering

Apply to code, configuration, scripts, runtime behavior, and tests. Check:

- correctness, behavioral regressions, boundary inputs, and error classification;
- preserved results, destructive actions, write authorization, network and credential handling;
- concurrency, atomicity, partial success, interruption, cleanup, and retry behavior;
- security, path traversal, secret exposure, trust boundaries, and unsafe subprocess use;
- performance, unbounded output, context-window pressure, repeated remote work, and scalability;
- portability and explicit environment assumptions;
- public schema compatibility and code/document drift;
- tests proportional to blast radius, including failure and non-action cases.

Prioritize user-visible bugs and irreversible risk. Do not inflate refactoring preferences into
correctness findings.
