# External-Reference Workflows

This guide covers preserved ownership and external-reference operations. The
normative model is in [External References](../spec/external-references.md) and
[Preserved Boundaries](../spec/preserved-boundaries.md).

## Inspect Boundaries

Run:

```bash
<python> <skill-directory>/scripts/whero_wiki.py mounts --wiki <root>
```

The command reports exact and pattern-derived preserved paths, declarations,
nested Wikis and Views, and Git submodules. Treat each result as an ownership
boundary for outer maintenance.

## Declare A Reference

Put the declaration in the nearest maintained, View-required `index.md`:

```yaml
whero_external_references:
  - path: vendor/project
    projection: mount
    content: ordinary
    locator:
      kind: filesystem
      path: ../../sources/project
      type: directory
```

Use `projection: mount` for whole exposure. Use `projection: view` only for a
Whero Wiki or View that should retain its current selective availability. Git
locators use `url` and optional `revision`; `git-submodule` derives transport
from the containing repository. Never store credentials in a locator.

## Preserve Owner-Managed Paths

Declare exact paths or direct-child basename patterns:

```yaml
whero_preserved_paths:
  - vendor
  - exports/raw.md
whero_preserved_patterns:
  - '^generated-.*$'
  - '.*\.lock'
```

Patterns use Unicode-aware full matching and do not recurse. A pattern with no
current match is valid. Outer validation, link scans, and maintenance do not
enter preserved content. Selecting a preserved descendant for a View is legal
and automatically exposes the whole boundary.

## Mount And View Behavior

- A Mount always exposes its complete source. Selecting its root, a descendant,
  or an outer selected directory containing it needs no opt-in flag.
- A mounted Whero Wiki retains its own maintenance and validation lifecycle.
- A declared View projection exposes no content unavailable in that View.
- View expansion links immediate-source paths and does not generate a child
  View or mutate the referenced source.

## Restore References

Create a read-only plan first:

```bash
<python> <skill-directory>/scripts/whero_wiki.py restore --wiki <root>
<python> <skill-directory>/scripts/whero_wiki.py restore --wiki <root> \
  --store /path/to/repository-store
```

The plan classifies each declaration as present-valid, present-invalid, or
missing. Filesystem locators are validated in place. Git locators use the
caller-supplied store, and submodules use the containing repository. Apply only
after review by adding `--apply`; the command never replaces an existing
invalid target.

Restore Mounts before Views that depend on them. For a missing or relocated View
source, use the View restoration workflow in [View Workflows](view-workflows.md).
