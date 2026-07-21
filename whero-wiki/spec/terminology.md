# Whero Wiki Protocol Terminology

Protocol status: **v0.0.2 active**. These terms define the current contract.

Use the exact terms below in protocol documents. Wrap a protocol term in
backticks when it is introduced or when the distinction is material.

## Core Terms

- A `Whero Wiki` is a directory-rooted knowledge organization identified by a
  valid `whero-wiki-meta.md`.
- A `Wiki Root` is the directory containing that identity file. Its directory
  name is not part of the identity contract.
- A `Maintained Document` is authored or maintained by Whero Wiki. A
  `Collected Source` is an externally acquired snapshot whose prose is not
  maintained in place.
- A `Framework Document` is a maintained document required to identify,
  navigate, validate, or operate the Wiki. Framework documents required along
  a selected ancestor path are `View-Required Documents`.
- An `External Reference` places content owned outside the containing directory
  tree at a stable logical path. Every external reference uses either a
  `Mount` or a `Whero Wiki View` as its projection.
- A `Mount` exposes an external repository or directory in full. Its transport
  may be a relative symbolic link, an ordinary Git checkout, or a Git
  submodule.
- A `Whero Wiki View`, or `View`, is a structure-preserving, selective,
  read-through projection of a `Whero Wiki` or another `View`.
- A `Preserved Boundary` is a local ownership rule that prevents Whero
  maintenance inside a file or directory. It is not a transport or projection
  mechanism.
- A `Selection` is a source-logical file or directory requested for a `View`.
  An `Effective Root` is a materialized root after framework completion,
  whole-boundary or traversed-source-symlink promotion, and collapse rules are
  applied. A selection and its effective root may therefore differ without
  changing the caller's intent.
- A `Source-Reachable Path` is a logical path that exists in the immediate
  source Wiki or source View, including paths reached through declared Mounts
  and source symbolic links allowed by the source ownership rules.
  Materialization preserves that immediate source path and does not replace it
  with the final resolved target.
- A `Source Locator` records how an external source can be found or restored. A
  `Source Identity` records which source state was reviewed or materialized.

## Reserved Vocabulary

Use `View` for the selective projection and for the materialized result. Use
*directory*, *subtree*, *topic*, or *collection* for ordinary organizational
groupings.

`Disclosure` remains an ordinary verb describing the act of exposing content;
it is not a protocol object name. `Preserved` describes maintenance ownership,
not whether bytes are local, remote, mounted, or selected.

## Canonical Names

The View metadata document is `whero-wiki-view.md`. It sets `whero_view: true`.
Framework context that must accompany a selection sets
`whero_view_required: true`. The View validation profile is named `view`.
