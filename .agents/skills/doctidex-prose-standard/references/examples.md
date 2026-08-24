# Distilled prose examples

Use these examples to identify the governing principle, not as text templates. “Balanced” preserves every load-bearing proposition with the least explanation needed at that location.

## Preserve every factual clause

**Original:** “The repair command carefully aligns JSON records, recreates missing Installations, and removes stale managed links.”

**Over-trimmed:** “The repair command fixes state.”

**Balanced:** “The repair command aligns JSON records, recreates missing Installations, and removes stale managed links.”

Remove decoration and repetition, not propositions. The model baseline, Installation recovery, and managed-link cleanup are separate facts.

## Explicit skill scope is functional

**Over-trimmed:** “Read the sources and use judgment.”

**Balanced:** “This skill is guidance, not a complete checklist. Use judgment beyond the named checks; documented requirements still apply.”

Keep the explicit limitation because it changes how an agent applies the workflow. Trim repeated persuasion, not the guardrail.

## A cookbook keeps action and verification

**Over-trimmed:** “Add tests for the command.”

**Balanced:** “Test cache hit and cache miss paths through `StoreCoordinator.with_repository`, then verify that a `preparing` record is cleaned on the next transaction.”

**Over-detailed:** A walkthrough of every fixture and assertion already visible in the test code.

Keep the required action and observable verification. Remove fixture narration.

## Preserve ownership and timing

**Over-trimmed:** “Cache work is recovered during startup.”

**Balanced:** “CacheStore removes interrupted `preparing` records before exposing records to a transaction.”

The actor, timing, and recovery boundary are separate factual clauses.

## Public API documentation includes failures

**Over-trimmed:** “Returns the cached repository.”

**Balanced:** “Returns the published cached repository. Raises `cache.repository.unavailable` when the Git URL has no usable cache record.”

Failure states and preconditions are caller-visible contract facts.

## Orient complicated code without narrating it

**Over-trimmed:** “RuntimeStore support.”

**Balanced:** “Owns journaled publication of the four state projection files. Write transactions mark themselves prepared before publishing; repair reconciles residual journals.”

Keep the module's role and non-obvious lifecycle behavior. Let code show local control flow.

## Link rationale while keeping the local contract

**Over-trimmed:** “Transactions are documented in the architecture.”

**Balanced:** “RuntimeStore writes are journaled and retried through `StoreCoordinator`. See the stores-and-transactions architecture for recovery details.”

Keep the behavior where callers need it. Link aggressively for rationale; a link cannot replace the local contract.

## Implemented Issue Notes retain verification contracts

**Over-trimmed:** Deleting the testing section because the Issue Note has shipped.

**Balanced:** “Tests cover cache hits, cache misses, interrupted cache publication, and RuntimeStore recovery. The real workflow path is exercised; snapshot coverage is deferred where transport is process-specific.”

Remove migration tasks and test narration. Keep the behaviors the tests pin and the named gaps.

## Delete reasoning transcripts entirely

**Over-detailed:** “First the loop checks whether the path exists. If it does not exist, the next branch returns early. Otherwise it continues, which is why the final check is safe.”

**Balanced:** No comment when the code already expresses those branches. If the early return protects a non-obvious invariant, state only that invariant.

## Configuration comments explain what the tree cannot

**Over-detailed:** “This entry loads the local cache, followed by the repair rule, followed by the validate rule.”

**Balanced:** “Load repair before validation so residual journals are reconciled before the tree is scanned.”

Keep the consequence of order or a security boundary. Let configuration show its own inventory.

## Model-visible text follows ownership

**Over-trimmed:** “The command returns errors when a call fails.”

**Balanced:** “Quote stable CLI result and error text owned by this command. Link generated schemas and reference text owned elsewhere.”

Wording that reaches a user or model is behavior, but duplication still drifts. Exactness belongs at the owner.

## Generated summaries must stand alone

**Over-trimmed:** “Installation record.” The owner explains revision and tracking later, but the generated catalog exports only the first sentence.

**Balanced:** “Installation record that fixes one Git URL at one commit and one install path.” Keep non-catalog detail in later sentences.

Know what the generator extracts. That fragment must preserve the contract needed on its generated output.

## Limitations are contracts, not debt inventories

**Over-trimmed:** Omitting a process-lifetime cache that makes configuration changes require a new command run.

**Balanced:** “Cache configuration is read when `GitCache` is constructed; changing `cache-path` requires a new command process.”

Retain gaps and non-obvious constraints that affect use or safe maintenance. Do not turn a document into a backlog dump.
