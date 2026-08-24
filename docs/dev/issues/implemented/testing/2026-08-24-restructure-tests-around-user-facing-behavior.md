# Issue Note: Restructure tests around user-facing behavior

Status: implemented

## Problem

The Python test suite had grown against implementation internals rather than the CLI and model surfaces users rely on. The largest modules mixed several command clusters, and many tests pinned private helpers, parser fields, monkeypatched call sequences, and transaction journals. Those tests narrowed future design work: a legitimate internal refactor broke them even when observable behavior was unchanged.

The suite at the time was 2,673 lines across six files. `test_boundary_and_import.py` (1,278 lines) combined boundary, import, installation-context, worktree, and cache-coordination coverage. `test_work_model_stores.py` (578 lines) tested `RuntimeStore`, `CacheStore`, journal entries, and private encoders directly. `test_validate_repair.py` (484 lines) mixed validation, annotation parsing, coordination, and repair.

This conflicted with the testing guidance in [src/AGENTS.md](../../../../../src/AGENTS.md), which prefers public-interface functional coverage over small internal-interface tests, and with the implementation rule in [doctidex-issue-impl](../../../../../.agents/skills/doctidex-issue-impl/SKILL.md) to avoid tests for small internal interfaces and to organize tests by architecture, feature, and module. The cache-aware pattern in [cache-aware-command-pattern.md](../../../cookbook/cache-aware-command-pattern.md) also prescribes verifying cache and transaction behavior through the real workflow path.

## Decision

The test suite now treats the CLI entry point as the public test surface. Tests invoke `whero.doctidex.cli.main.main(argv)` through a shared runner and assert its JSON result plus Git and filesystem effects. Test files import no workflow, store, or private helper symbols; `conftest.py` owns all Git and durable-JSON fixture setup.

The suite is organized by command cluster into `test_cli_contract.py`, `test_init.py`, `test_boundary_set.py`, `test_import.py`, `test_worktree.py`, `test_validate.py`, `test_repair.py`, `test_installation_context.py`, and `test_store_recovery.py`. The mixed legacy modules are removed.

`src/python/pyproject.toml` adds `pytest-cov` to the `test` extra so the coverage gate is reproducible.

The only test-side product import is `test_store_recovery.py` importing `coordination` to stub `repair_core` once. That narrow seam covers the retry-exhaustion branch in [coordination.py](../../../../../src/python/whero/doctidex/coordination.py), which no isolated on-disk precondition can otherwise reach; no other workflow or store internals are mocked.

## Testing

`pytest`, `ruff`, and `git diff --check` pass. Coverage is 84%, above the 80% gate and below the 90% quality target; coverage is raised through user-surface and public-interface cases rather than small internal-interface tests.

## Alternatives considered

**Keep the current unit tests and add end-to-end tests on top.**
Rejected: it leaves the narrow-design and internal-unit tests in place, so they continue to block internal refactors and contradict the repository testing guidance.

**Replace all tests with subprocess-level black-box tests.**
Rejected: invoking the installed console script through a subprocess is the most faithful user path, but it is slower and less convenient for isolated per-command cases. The in-process `main` entry point is the documented CLI surface and is sufficient for most cases.

**Delete every internal test without adding compensating user-space cases.**
Rejected: the removal alone would lose durable-store and cache-recovery verification and risk dropping below the coverage target.

**Cover unreachable core logic with broad monkeypatching.**
Rejected: stubbing workflow, store, or transaction internals to observe ordinary ordering is exactly the coupling this issue removes. The design arranges real on-disk states for those paths and reserves mocking for the single retry-exhaustion core mechanism.

## Consequences

The restructure removes narrow-design coupling and makes internal refactors safe against test churn. It costs some direct unit coverage of store and transaction internals, and it keeps one narrow mock for retry exhaustion. The suite now communicates behavior through the CLI and durable effects rather than through internal call ordering.
