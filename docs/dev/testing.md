# Testing

This document defines how to build tests for `doctidex-git`. It currently covers normal cases, robustness cases, and the external-interference boundary; additional testing rules are added here as the testing strategy evolves.

## Test-case construction

Design tests from the user surface and the current architecture, not from implementation details.

1. Cover normal cases first: valid command invocations that reach the documented successful result.
2. Add robustness cases proportionately. Use valid invocations that reach an expected but unsuccessful result, such as a blocked removal or an unavailable source, and invalid or inconsistent input, such as a missing required option or a rejected selector combination.
3. Derive each case from a real command, selector, or design rule. Do not invent a scenario the current design excludes.

Prefer end-to-end tests that observe the CLI result and its durable filesystem and Git effects. Use a narrow mock only for a core mechanism that no realistic end-to-end case can reach.

## Script validation tests

`src/python/tests/test_validate_user_doc_links.py` tests only `scripts/validate-user-doc-links.py`. It is marked
`validator_script`, so the default test suite excludes it, and it carries `no_cover` so it is not part of code-coverage
statistics.

Run it explicitly from `src/python/`:

```bash
cd src/python
../../.venv/bin/python -m pytest -o addopts='' -m validator_script \
  tests/test_validate_user_doc_links.py
```

The `-o addopts=''` override is required because the default `addopts` excludes `validator_script`.

## External interference boundary

The following three exclusions are one principle: `doctidex-git` does not coordinate against the user or other programs while a command is running.

- Do not model state JSON under `.doctidex-git/` being externally damaged or changed during a command.
- Do not model the repository or cache being changed by the user or another program during a command.
- For concurrency, model only interactions between `doctidex-git` CLI processes, not external actors.

The same principle is stated as a design rule in [architecture/overview.md](architecture/overview.md#cross-cutting-rules).
