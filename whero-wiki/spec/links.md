# Links

Protocol status: **v0.0.2 active**.

## Internal Links

Every link in the body of a Whero-maintained document to another document in
the same owning `Whero Wiki` uses a standard relative Markdown destination.
Resolve it from the linking document. Preserve fragments and validate them
against Markdown headings or explicit HTML anchors.

Do not create URI-like Wiki-root destinations, Wiki-root absolute destinations,
or filesystem-absolute destinations. Tools accept a Wiki-root-relative path as
caller input when convenient, but must render the stored Markdown destination
relative to the document being written.

Links do not cross an `External Reference` ownership boundary implicitly. A
document may link to a logical mounted or View path, but resolution uses the
owning Wiki or View and respects that boundary.

## Collected Sources

Do not rewrite collected prose merely to conform to maintained-document link
style. An authorized localization workflow may repair only a destination or add
the exact unresolved marker defined by the maintenance contract.

## Views

A link to undisclosed content is valid in a `View`. Report it as unavailable,
not missing. Following or inspecting a link never expands a View automatically;
the link destination becomes a `Selection` only when a caller explicitly asks
for expansion. When the immediate source is itself a View, expansion can select
only a path currently available in that source View; it must not bypass the
source View to retrieve unavailable content from an ultimate Wiki.
