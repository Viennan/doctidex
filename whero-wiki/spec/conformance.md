# Conformance

Protocol status: **v0.0.2 active**.

## Conformance Profiles

A `Full Wiki` profile validates complete owned content, declared boundaries,
framework structure, and source identities. A `View` profile validates readable
material, View metadata, effective roots, and relative links to immediate-source
path entries while treating unselected content as unavailable.

Validation must emit stable diagnostic codes and structured path context.
Mutation commands must support a complete dry plan before applying changes.

## Version Identity

The files in `spec/` describe the v0.0.2 contract. A conforming Wiki identity
and View metadata document set `format_version: "0.0.2"`. View metadata uses
`whero-wiki-view.md` and `whero_view`; View-required framework documents use
`whero_view_required`; the View validation profile is `view`.

The bundled tools implement only this version identity. An absent or different
`format_version`, a different View status filename, or substitute identity
fields do not identify a conforming v0.0.2 Wiki or View.

## Required Test Surfaces

Conformance tests cover:

- Wiki and View identity;
- external-reference declaration and restoration planning;
- legal selection through boundaries and automatic whole-root promotion;
- View-of-View availability limits and immediate-source symlink chaining;
- the source-path and collapse matrix in `views.md`;
- exact and pattern-preserved boundaries;
- relative-link parsing, graph inspection, and View-unavailable reporting;
- strict v0.0.2 identity and framework-field validation;
- preflight atomicity, Git identity, source relocation, and recovery.

English and Chinese protocol trees must contain the same relative filenames.
A protocol change updates both language versions in the same product change.
