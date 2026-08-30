# Issue Note: Standardize doctidex-git config access

Status: implemented

## Problem

The original config model was lost during later scaffolding changes. The intended contract was:

- `config.toml` is the configuration source.
- the global default config is the `config.toml` under the `DOCTIDEX-GIT-HOME` directory.
- each repository's `config.toml` is repository-level config.
- repository-level options override the global defaults.

Before this change, [git_cache.py](../../../../src/python/whero/doctidex/git_cache.py) read only the global
`config.toml` to resolve `cache-path`; there was no `Config` model or shared read interface, and the repository-local
`.doctidex-git/config.toml` created by [initialization.py](../../../../src/python/whero/doctidex/initialization.py)
was never read. Cache metadata also lived directly inside the cache data root.

## Decision

Config access is a first-class domain service implemented by [config.py](../../../../src/python/whero/doctidex/config.py).

`Config.from_environment(git_root=None)` is the only `config.toml` reader. It:

- resolves home from `DOCTIDEX-GIT-HOME`, defaulting to `~/.doctidex-git`;
- creates the global `<home>/config.toml` empty when it is absent;
- reads and validates the global file;
- reads the repository `.doctidex-git/config.toml` when a Git root is selected;
- merges repository values over global values;
- records which file declared each option in `sources`;
- resolves a relative `cache-path` from the directory containing the declaring config file, and uses absolute paths
  as-is;
- raises `config.invalid` for missing, malformed, or unusable config.

`GitCache.from_config(config)` constructs the user-level cache from an already-resolved `Config`. The CLI reads
`Config` once for each cache-using command through `_git_cache` in [cli/main.py](../../../../src/python/whero/doctidex/cli/main.py),
so workflows do not parse `config.toml` again.

Cache storage keeps `cache-path` as the data root:

| Artifact | Location |
|---|---|
| Cache metadata | `<cache-path>/cache-status.json` |
| Bare repository records | `<cache-path>/data/<domain>/<repository...>` |

`CacheStore` in [store/cache.py](../../../../src/python/whero/doctidex/store/cache.py) publishes
`cache-status.json`; a missing status file is treated as no records, and the file is created on the first cache write.
New `CacheItem.path` values start with `data/`, so the publication record sits beside the data directory rather than
mixed with repositories. No legacy `status.json` location is migrated.

## Testing

[test_config.py](../../../../src/python/tests/test_config.py) covers `Config.from_environment`, global auto-creation,
repository overrides, source-relative and absolute `cache-path` resolution, and invalid config.

[test_cache_config_cli.py](../../../../src/python/tests/test_cache_config_cli.py) covers CLI-level cache publication,
repository `cache-path` overrides, and invalid global config. The full suite passes with 205 tests; `ruff check` and
`git diff --check` pass.

## Alternatives considered

**Keep the current cache-only `_configured_cache_path` parsing.**
Rejected: it duplicates config parsing in one workflow, ignores repository-level config, and leaves the next config
consumer to invent another ad hoc loader.

**Move `cache-status.json` to the home directory.**
Rejected: a home-owned publication record cannot safely hold relative paths when repository config may select different
cache roots. Keeping the record inside `cache-path` preserves the existing relative-path semantics.

**Keep `cache-path` global-only.**
Rejected: that preserves one global cache, but it prevents repository-level config from selecting a cache root and does
not match the intended repository-over-global override rule.

**Replace config files with CLI flags.**
Rejected: the existing contract is file-based, and the cache path must be discoverable before command-specific parsing
so the CLI can construct the cache for many command clusters.

## Consequences

`doctidex-git` now has one config model and one read path. Repository config can override global options, and relative
paths are anchored to the file that declared them.

The cache publication record and bare repositories are separated by the `data/` prefix, which keeps cache maintenance
from scanning the metadata file as repository data.

The change intentionally provides no backward compatibility while the product is unstable. Orphaned `status.json` files
or bare repositories from earlier builds are not read, migrated, or repaired.
