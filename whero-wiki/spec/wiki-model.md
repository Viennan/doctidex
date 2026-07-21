# Whero Wiki Model

Protocol status: **v0.0.2 active**.

## Identity

A `Whero Wiki` is identified only by `whero-wiki-meta.md` at its `Wiki Root`.
The file must be a maintained `Framework Document` and contain:

```yaml
type: Whero Wiki
format_version: "0.0.2"
whero_wiki: true
whero_maintenance: true
whero_view_required: true
```

A full Wiki owns a regular identity file. A `View` exposes the source identity
through a relative symbolic link and adds its own regular
`whero-wiki-view.md`.

## Document Classes

The model has four document classes:

1. A `Collected Source` preserves externally acquired bytes and normally has no
   Whero frontmatter.
2. A `Maintained Document` sets `whero_maintenance: true` and contains Whero-
   authored or Whero-maintained knowledge.
3. A `Framework Document` is maintained and may set
   `whero_view_required: true` when every selected descendant needs it for
   interpretation or operation.
4. `whero-wiki-view.md` is generated View metadata. It is maintained and View-
   required, but exists only in a materialized `View`.

`whero-wiki-meta.md`, maintained `index.md`, and maintained `log.md` are the
standard framework filenames. A maintained knowledge document must not become
View-required merely because it is useful or curated.

## Ownership

The nearest containing `Wiki Root` owns a path unless the path enters an
`External Reference` or a declared `Preserved Boundary`. The outer Wiki may
route to and cite such content, but it must not maintain content owned beyond
that boundary.

An ordinary external repository is preserved automatically at its `Mount`
root. A mounted `Whero Wiki` or `View` retains its own Whero ownership and
lifecycle instead of inheriting ownership from the containing Wiki.

## Navigation And History

Use lowercase `index.md` for maintained routing and lowercase `log.md` for
useful maintenance history. Neither file is mandatory when it would be empty.
When present as framework metadata, each sets both `whero_maintenance: true`
and `whero_view_required: true`.

Internal document links follow [Links](links.md). External ownership and
projection follow [External References](external-references.md). Selective
projection follows [Whero Wiki Views](views.md).
