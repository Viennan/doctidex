# Preserved Boundaries

Protocol status: **v0.0.2 active**.

A `Preserved Boundary` prevents the containing Wiki from maintaining a file or
directory in place. The content remains readable, searchable, linkable, and
citable. Preservation does not create a new source identity or projection.

## Exact Paths

Declare exact paths in the nearest maintained, View-required `index.md`:

```yaml
whero_preserved_paths:
  - vendor
  - exports/raw.md
```

Paths are safe, non-empty relative POSIX paths. They must not name framework
files, escape the Wiki, enter another external reference, or overlap after
canonical boundary resolution.

## Direct-Child Patterns

Direct-child regular-expression rules use:

```yaml
whero_preserved_patterns:
  - '^generated-.*$'
  - '.*\.lock'
```

Apply each expression with Unicode-aware `fullmatch` to the basename of direct
children of the declaring index directory. Do not recurse. An expression with
no matches is valid so a project can declare a stable policy before generated
content exists. Invalid expressions are conformance errors.

Framework filenames are never preserved by a pattern. Exact and pattern rules
are resolved into one boundary set; duplicate matches are harmless, while an
ancestor boundary shadows descendant matches.

## Maintenance And Views

Do not inject metadata, repair links, validate internals, or create framework
documents inside a preserved boundary. Selecting the root or any descendant for
a `View` is valid and exposes the whole boundary as one atomic effective root.
The caller may keep selecting the desired descendant and does not need to know
or request the boundary root. The outer planner does not inspect preserved
descendants or count them for collapse.

An ordinary external `Mount` is preserved automatically. It need not be
duplicated in `whero_preserved_paths` or `whero_preserved_patterns`.
