# Issue Note: Add sad/bad-path testing guidance and bound coordination guarantees

Status: implemented

## Problem

The restructured suite covers user-facing happy paths, but the repository had no guidance for constructing sad and bad paths from the user surface and the design. Tests written without that guidance risk inventing failure scenarios that the current design does not support, or under-testing argument- and design-driven failure handling.

The same ambiguity existed in the concurrency boundary. The user guide said `doctidex-git` coordinates only `doctidex-git` processes, but [overview.md](../../../architecture/overview.md) did not state this as a design principle, and the testing guidance did not say which interference scenarios are out of scope.

## Decision

The repository now records test construction and the coordination boundary in three places.

[docs/dev/testing.md](../../../testing.md) is the authoritative home for test construction. It separates normal cases from robustness cases, and states one external-interference boundary: `doctidex-git` does not coordinate against the user or other programs while a command is running. That boundary excludes tests that model state JSON under `.doctidex-git/` being externally damaged, the repository or cache being changed by an outside actor, and concurrency with non-`doctidex-git` processes.

[overview.md](../../../architecture/overview.md) states the same boundary as a cross-cutting design rule: coordination is scoped to cooperating `doctidex-git` processes, and a command does not protect its state files, managed paths, or cache from external edits or non-`doctidex-git` concurrent actors.

[docs/AGENTS.md](../../../../AGENTS.md) routes documentation maintenance to `docs/dev/testing.md` for test-construction decisions.

The same usage limitation already appears in [user/overview.md](../../../../user/overview.md): `doctidex-git` coordinates only `doctidex-git` processes that follow its lock and transaction protocol, and does not guarantee race safety against direct external edits.

This change is documentation only. It changes no product code and no user surface.

## Alternatives considered

**Model external interference in tests.**
Rejected: it would require fabricating destructive scenarios that the design intentionally does not protect against, and would blur the boundary between supported behavior and unsupported external races.

**Record the exclusions only in `docs/dev/testing.md`.**
Rejected: the boundary is a runtime design fact, so architecture is its authoritative home.

**Make bad-path coverage exhaustive.**
Rejected: exhaustive robustness testing is disproportionate and tends to over-fit implementation details. Design-driven, representative robustness cases are sufficient.

## Consequences

The decision keeps negative tests grounded in the user surface and design rather than external races. It costs direct coverage of user- or program-induced interference, which is intentionally unsupported. The coordination boundary is now stated consistently in testing, architecture, and user guidance.
