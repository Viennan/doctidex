# Testing

This document defines how to build tests for `doctidex-git`. It currently covers normal cases, robustness cases, and the external-interference boundary; additional testing rules are added here as the testing strategy evolves.

## Test-case construction

Design tests from the user surface and the current architecture, not from implementation details.

1. Cover normal cases first: valid command invocations that reach the documented successful result.
2. Add robustness cases proportionately. Use valid invocations that reach an expected but unsuccessful result, such as a blocked removal or an unavailable source, and invalid or inconsistent input, such as a missing required option or a rejected selector combination.
3. Derive each case from a real command, selector, or design rule. Do not invent a scenario the current design excludes.

Prefer end-to-end tests that observe the CLI result and its durable filesystem and Git effects. Use a narrow mock only for a core mechanism that no realistic end-to-end case can reach.

## External interference boundary

The following three exclusions are one principle: `doctidex-git` does not coordinate against the user or other programs while a command is running.

- Do not model state JSON under `.doctidex-git/` being externally damaged or changed during a command.
- Do not model the repository or cache being changed by the user or another program during a command.
- For concurrency, model only interactions between `doctidex-git` CLI processes, not external actors.

The same principle is stated as a design rule in [architecture/overview.md](architecture/overview.md#cross-cutting-rules).
