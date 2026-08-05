# Independent Review Lenses

Select only lenses applicable to the frozen scope. Read each named authoring Skill completely rather
than reconstructing its rules here.

## Protocol Compliance

Authority: `spec/overview.md`, read completely. Requirements, Architecture, Impls, references, and
code are evidence but cannot create protocol obligations.

Review every scoped interface and path that can produce, accept, interpret, validate, traverse,
mutate, or report a doctidex tree. Trace each finding to an exact normative rule and observable
failure. Protocol silence permits implementation choice; a valuable new rule is at most an
`advisory`/`recommended` specification suggestion unless another authority is violated.

Do not infer CLI, source-identity, revision, scope, reuse, scheduling, implementation, or write
authorization requirements from protocol concepts. `unsafe` is a conformity exception, not a
permission, trust conclusion, or write boundary. Check its local declaration, path, reachability,
and safe-link annotation; its mere existence is not a defect, and an unnecessarily broad scope is
only `advisory` under section 5.3 unless another mandatory rule fails. `atomic-indexing` changes
indexing granularity, not responsible-index ownership, unsafe status, reading access, link roots, or
boundary rules. Evaluate links from their current doctidex root using root-internal lexical paths.

## Agent-Facing Skill Surface

Authority: `AGENTS.md`, the applicable product Architecture design constraints, the changed Skills
and metadata, and the public behavior they claim. For doctidex-git Published Skills, read
`docs/doctidex-git/architecture/skill-system.md` first.

Classify each Skill as published or repository-local. Apply installed-product information boundaries
only to published Skills. Verify trigger precision, audience, acyclic reading, workflow and command
completeness, native-tool freedom, deterministic helpers, bounded output, actionable failures,
metadata, validation, and proportionate forward-test evidence. For doctidex-git, the Overview's
fixed-tag GitHub distribution bootstrap is an Architecture-authorized product user surface; do not
classify it as repository development information or recommend removing it merely because it states
the current version and package installation command. Treat style preferences as advisory unless
they create ambiguity, unsafe action, or a false surface.

## Requirement Fulfillment and Lifecycle

Authority: the applicable record under `docs/requirements/` and
`$write-doctidex-requirement-docs`.

Trace reviewed intent and acceptance criteria to authorized artifacts and evidence. Check negative
requirements and failures, not only happy paths. Verify status and explicit approval provenance,
active-artifact update order, question/answer handling, live user comments, dependency links,
large-Requirement aggregate gates, scope, and approved-history preservation. Do not invent missing
historical wording or infer authority to repair another layer.

Use current Architecture, Impls, code, tests, and public surfaces as realization evidence in their
normal authority order; they do not rewrite the Requirement.

## Architecture Design

Authority: `$write-doctidex-architecture-docs`, the current Architecture, applicable Requirement,
and normative protocol dependencies explicitly claimed by the Architecture.

Check user-surface coverage, key common models and dependencies, mechanism and policy closure,
workflow derivation, observable semantics, language neutrality, public/internal separation, current
authority uniqueness, and authorized structural replacement. Apply the Architecture Skill's bounded
cold-read and materiality rules exactly; do not demand byte-level implementation detail without an
explicit interoperability contract.

## Impls Realization

Authority: `$write-doctidex-impls-docs`, the applicable Architecture and Requirement, current Impls,
and the variant source, tests, packaging, and public surfaces as evidence.

Check applicability, variant user entry, key capability coverage, concrete component and physical
state design, flows, side effects, failure/concurrency/recovery boundaries, code ownership, source
and test traceability, and material limitations. Do not require prose for every helper or accept a
code map as the whole design. A required Architecture gap cannot be hidden as an Impls choice.

## Cross-Layer Consistency

When more than one documentation lens applies, check that Requirements preserve historical intent,
Architecture owns common current design, and Impls owns concrete realization. Verify useful links,
no duplicate authority, no language-specific leakage upward, and no current compatibility shim kept
solely for history. Do not apply current completeness rules retroactively to archives or approved
history.

## General Engineering

Apply to code, configuration, scripts, runtime behavior, and tests. Check correctness, regressions,
boundary inputs, error classification, authorization, destructive effects, credentials, concurrency,
partial success, interruption, cleanup, retry, security, performance, bounded output, portability,
schema compatibility, code/document drift, and tests proportional to risk.

Prioritize observable bugs and irreversible risk. Do not inflate refactoring preferences into
correctness findings.
