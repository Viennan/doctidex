# External References

Protocol status: **v0.0.2 active**.

## Model

An `External Reference` maps an independently owned source to a stable logical
path. Its projection is exactly one of:

- `Mount`: expose the referenced source in full;
- `View`: selectively expose a source that is a `Whero Wiki` or another
  `View`.

Non-Whero content must use a `Mount`. A `Whero Wiki` or `View` referenced from
another directory tree must use the external-reference system; copying selected
files is not a conforming projection.

## Declaration

Inside a `Whero Wiki`, declare references in the nearest maintained,
View-required `index.md`:

```yaml
whero_external_references:
  - path: vendor/project
    projection: mount
    content: ordinary
    locator:
      kind: git-submodule
```

Each declaration contains:

- `path`: a safe relative POSIX path from the declaring index;
- `projection`: `mount` or `view`;
- `content`: `ordinary`, `whero-wiki`, or `view`;
- `locator`: the information required to locate or restore the source.

Supported locator kinds are:

- `filesystem`: `kind: filesystem`, a `path` relative to the declaring index,
  and `type` equal to `file` or `directory`;
- `git`: `kind: git`, a credential-free `url`, and an optional reviewed
  `revision` as a full 40-character commit ID;
- `git-submodule`: source data derived from `.gitmodules` and the parent
  gitlink.

Unknown declaration or locator fields are reserved. A declaration with an
unsupported value, unsafe logical path, malformed locator, or overlapping
external-reference ancestor is non-conforming.

A `View` additionally records its source locator, identity, requested
selections, effective roots, and policy in `whero-wiki-view.md`. A View outside
a Wiki therefore remains independently restorable.

## Mount Rules

- A relative symbolic-link Mount should be used only when Git transport is not
  appropriate. Restoration validates existence and type, then warns that v0.0.2
  does not hash arbitrary symbolic-link targets.
- A Git Mount not controlled by the containing repository records a sanitized
  remote and reviewed revision when available.
- A Git submodule uses `.gitmodules` and the gitlink as transport authority.
- An ordinary Mount is automatically a `Preserved Boundary`.
- Every Mount is exposed whole, regardless of whether its content is ordinary,
  a `Whero Wiki`, or a `View`. Selecting any reachable descendant is valid and
  automatically promotes the effective root to the Mount root; callers do not
  need to select the root or pass a boundary-specific flag.
- A mounted `Whero Wiki` retains independent validation and maintenance, but
  does not gain selective projection while it is mounted. Use a `View`
  projection when selective exposure is required. Selecting inside a referenced
  View is limited to material already available in that View and creates no
  generated child View.

## Restoration

Restoration is a planned, validated operation:

1. Read declarations and View metadata without mutating the filesystem.
2. Classify each reference as present-valid, present-invalid, or missing.
3. Validate a filesystem locator in place. Do not silently substitute a
   different target.
4. For a Git locator, use the caller-provided repository store or destination,
   fetch the recorded remote, and verify the reviewed identity.
5. Restore Mounts before Views whose immediate source paths depend on them.
6. Rebuild View-relative symbolic links to the recorded immediate-source path
   entries; do not resolve source symlinks or infer unavailable source-View
   content from an ultimate Wiki.

Network fetches and replacement of user-owned target content require explicit
application of a reviewed restoration plan.
