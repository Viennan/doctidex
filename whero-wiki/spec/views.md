# Whero Wiki Views

Protocol status: **v0.0.2 active**.

## Contents

- [Identity And Layout](#identity-and-layout)
- [Selection Processing](#selection-processing)
- [Source-Path Matrix](#source-path-matrix)
- [Collapse](#collapse)
- [Source Change Safety](#source-change-safety)
- [Restoration](#restoration)

## Identity And Layout

A `View` is a structure-preserving, read-through projection of a `Whero Wiki`
or another `View`. It may be placed in a Wiki or in an ordinary directory.

The View root contains:

- a relative symbolic link to the source `whero-wiki-meta.md`;
- a regular generated `whero-wiki-view.md`;
- relative symbolic links and generated containers for its `Effective Roots`.

`whero-wiki-view.md` has the following canonical frontmatter:

- identity: `type: Whero Wiki View`, `format_version: "0.0.2"`,
  `whero_maintenance: true`, `whero_view_required: true`, and
  `whero_view: true`;
- source locator and identity: relative `source`, `source_validation` equal to
  `path` or `git-commit`, and, for Git, `source_commit`, `source_git_path`, and
  optional sanitized `source_git_remote_*` fields;
- policy and intent: `layout: source-relative`, `view_name`,
  `collapse_threshold`, `requested_selections`, and `effective_roots`;
- optional reconstructed diagnostics such as `disclosed_symlinks`, which are
  not selection authority.

`requested_selections` and `effective_roots` are lists of safe source-logical
POSIX paths. The former is the rebuild intent authority. The latter records the
last applied plan and can be reconstructed from readable links after an
interrupted metadata write.

Every generated content link targets the `Effective Root` path entry in the
immediate source Wiki or source View. Compute the link relative to that source
entry without resolving a source symbolic link to its final target. A View of a
View therefore links to the parent View, not to its ultimate source Wiki.

The View materialization does not reproduce an explicit boundary merely because
a path crosses a preserved path, Mount, nested Wiki, source View, or symbolic
link. Boundary rules may promote an effective root to an ancestor, but the
result remains a structure-preserving link at that source-logical path.

## Selection Processing

Process a requested `Selection` in this order:

1. Resolve caller-friendly paths or link destinations into source-logical POSIX
   paths. A caller may select any `Source-Reachable Path`, including a path that
   crosses one or more ownership or reference boundaries.
2. Report ambiguity, unapproved source escape, or absence from the immediate
   source. Do not obtain content hidden or unavailable in a source View from an
   ultimate Wiki.
3. Promote selections when a boundary rule requires a whole file, directory,
   preserved boundary, Mount, or traversed source symlink. When a path
   traverses one or more source symlinks, promote to the first such symlink path
   entry. This changes the `Effective Root`, not the validity or meaning of the
   caller's selection.
4. Add available ancestor-path `View-Required Documents`.
5. Apply permitted adaptive collapse.
6. Preflight links, collisions, source identity, and filesystem changes before
   mutation.

The View records both requested selections and resulting effective roots.
Incremental expansion changes only the target View; it must not mutate the
source Wiki or source View. Callers do not need boundary-specific flags or need
to replace an internal selection with its required whole-exposure root.

## Source-Path Matrix

| Selected path | Required projection | Collapse consequence |
| --- | --- | --- |
| Ordinary owned file or directory | Relative link at the same logical path | Normal View rules |
| Preserved root or descendant | Promote to and expose the whole preserved root | Do not inspect or count descendants |
| Mount root or descendant, regardless of content type | Accept the selection and promote its effective root to the Mount root | Expose the whole Mount |
| Available path in a source or referenced View | Link the corresponding immediate-source entry without resolving it further | Visibility cannot exceed that source View |
| Path unavailable in a source or referenced View | Do not materialize it; report that it is unavailable from the immediate source | No fallback to an ultimate Wiki |
| Source symbolic link or descendant reachable through it | Promote to the first traversed source symlink and link that path entry without resolving it | Expose the source-visible content represented by that symlink |
| Explicitly selected ancestor directory | Link that source directory and expose its source-visible subtree | The directory selection authorizes that subtree |

Crossing several boundaries does not create nested View metadata. Resolve the
requested logical path against the immediate source, compute any required
ancestor promotion, and create the resulting relative link.

## Collapse

Adaptive collapse replaces generated descendants with one link to the matching
directory entry in the immediate source only when the replacement exposes
exactly the authorized effective content.

- Whole-boundary promotion occurs before collapse coverage is calculated.
- An explicit directory selection authorizes its complete source-visible
  subtree, including source boundary entries already present below it.
- Preserved boundaries, Mounts, and traversed source symlinks are atomic. The
  planner does not inspect or count their internal files separately.
- A source View contributes only paths currently available in that View.
  Unavailable source paths do not count toward coverage and cannot be exposed by
  collapsing to an ultimate source directory.
- Collapse decisions are part of the reviewed plan and must not broaden during
  execution.

## Source Change Safety

For Git-controlled sources, record a reviewed commit and Wiki path. Accept only
forward ancestry automatically, and only when changed content or structure does
not intersect an effective root. Reject selected dirty, untracked, or ignored
content before mutation. A View remains read-through, so diagnostics must state
that existing links may already expose changed source bytes.

For path-identified sources, require the recorded resolved source unless a
reviewed restoration or relocation plan establishes the same source identity.

## Restoration

Restore the immediate source before rebuilding links. Validate source identity,
requested selections, effective roots, source-path availability, and collisions
in a dry plan. Recreate each relative link to its corresponding immediate-source
path entry and atomically replace `whero-wiki-view.md`. Do not resolve through a
source symlink or fill a missing source-View path from an ultimate Wiki.
Readable links remain the availability authority after an interrupted metadata
write; stored selections remain the intent authority for a full rebuild.
