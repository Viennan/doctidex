# Issue Notes

One kind of design doc lives here. An **Issue Note** records a decision or proposal that affects this codebase — the *why* and *what we gave up*, the parts code and docs can't carry. This file defines where Issue Notes live, how they are classified, and the in-file format. For how to find, update, archive, and move Issue Notes, see [AGENTS.md](AGENTS.md).

## Layout and naming

Every Issue Note has two axes, both encoded in its **path** — `{lifecycle}/{class}/yyyy-mm-dd-topic-title.md`:

- **Lifecycle** (the top-level folder) is the Issue Note's status:
  - **`proposed/`** — proposals reviewed before implementation; not yet built (or only partly).
  - **`developing/`** — the issue is under active design and implementation; the note carries design details, an implementation plan, and current progress.
  - **`implemented/`** — the decision shipped. The file records what was decided and what was rejected, and is kept current with what actually shipped: when the code later moves a file, renames a package, or changes a key/default, the Issue Note is updated in the same change to match (facts only — paths, names, structure — not the decision itself).
  - **`rejected/`** — the proposal was considered and declined. Keep it only while its rationale prevents a tempting, meaningful mistake; otherwise delete the complete triplet.
- **Class** (the nested folder) is the *kind* of decision — see [Classification](#classification).

The date in the filename is when the topic was **first proposed** (per git history). Cross-references between Issue Notes use relative markdown links (`[topic](../../implemented/architecture/2026-…-….md)`) — never bare prose or numbers.

## Classification

Each Issue Note belongs to one path-encoded class from the closed set below.

| Class | What it covers |
|---|---|
| `feature` | A new user- or model-facing capability. |
| `bug-fix` | Corrects a defect or closes a gap a postmortem surfaced. |
| `simplification` | Removes code, behavior, or surface area without adding a capability. |
| `architecture` | A structural decision about the **shipped source** — how packages relate, what the runtime vocabulary is. |
| `process` | Tooling, policy, or workflow **around** the code — gates, the package manager, vendoring — not runtime behavior. |
| `testing` | Test infrastructure and strategy. |

The `architecture` / `process` line: **architecture** is about the source we ship; **process** is the surrounding tooling and workflow. (`refactor` is deliberately absent — it overlaps `simplification`, whose discriminator, "does observable behavior change?", already covers it.)

## The file format

Every active Issue Note follows one in-file format; the rationale for the format — and the alternatives it rejected — is the uniform-format Issue Note. Archived notes retain the format they had when sealed plus the archive-date line above.

### The header block

The first three lines of every Issue Note are exactly:

```markdown
# Issue Note: <title>

Status: <status>
```

followed by a blank line. The `Status:` value is one of four forms, and must agree with the lifecycle folder the file sits in:

- `Status: proposed`
- `Status: developing`
- `Status: implemented`
- `Status: rejected — <why, in one line>`

The status carries no dates and no parentheticals: the filename holds the first-proposed date, git holds everything else, and an "accepted in amended form" note is body content (state the amendment where the decision is stated). The rejection reason is the one status with content, because a rejected Issue Note's verdict is the fact readers come for.

### The body skeleton

Every Issue Note opens its body with `## Problem` — the motivation, written to stand without the solution. What follows depends on the lifecycle; recurring sections use these canonical names and nothing else, while genuinely bespoke technical sections (package topology, wire contracts, schemas) remain free-form between the required ones.

#### `proposed/`

```markdown
## Problem
## Proposal
…bespoke sections…
## Alternatives considered
## Acceptance criteria
## Risks
```

`## Proposal` is the intended change and may legitimately speak in the future tense — plans, migration steps, and open questions belong here while the work is unbuilt. `## Acceptance criteria` says what observable state means done. `## Risks` covers both what could go wrong and what the change knowingly gives up.

#### `developing/`

```markdown
## Problem
## Design
## Implementation plan
## Progress
…bespoke sections…
## Alternatives considered
```

`## Design` records the design details and decisions being worked out. `## Implementation plan` records the bounded work and sequencing. `## Progress` states what is complete, what is in flight, and what remains.

#### `implemented/`

```markdown
## Problem
## Decision
…bespoke sections…
## Alternatives considered
## Consequences
```

`## Decision` describes shipped reality in the present tense, and the whole file is kept current with it. `## Consequences` records what the trade-off cost **and** bought. Proposal- and development-era headings are spec-speak here; `## Proposal`, `## Design`, `## Plan`, `## Implementation plan`, `## Migration plan`, `## Progress`, and `## Acceptance criteria` may not appear in an implemented Issue Note. A `## Testing`, `## Deferred`, or `## Related` section is fine where it states present-tense fact.

#### `rejected/`

A rejected Issue Note is the proposal, frozen: it keeps whatever proposal-time sections it had (including `## Acceptance criteria` or `## Plan`), and the verdict lives on the `Status:` line. Only the header block, the `## Problem` opener, a `## Proposal` section, and the Alternatives-considered mandate below apply.

### Alternatives considered — mandatory

Every Issue Note carries an `## Alternatives considered` section: each genuine alternative and why it lost, one bold-led paragraph per alternative or a `### Why not <X>?` subsection per contested one. A decision recorded without what it beat invites re-litigation — the failure Issue Notes exist to prevent.

Alternatives are recorded, never invented. An Issue Note dated before 2026-07-05 whose alternatives are not reconstructible from the record carries this exact comment in place of the section, which is accepted for pre-format files only:

```markdown
<!-- issue-note-format: alternatives-not-recorded (pre-format Issue Note) -->
```

### Chinese counterparts

A `.zh.md` counterpart mirrors its English sibling's structure section-for-section under the i18n contract; the machine-checked header tokens (`# Issue Note: ` and the `Status:` line) stay in English verbatim. The format checks skip `.zh.md` files; pairing checks verify their consistency.
