# Finding and Review Output Contract

## Finding Fields

Use this structure for every candidate finding:

```text
ID: <lens>-<number>
Severity: critical | high | medium | low | advisory
Disposition: must_fix | recommended
Confidence: high | medium | low
Authority: <document section, requirement statement, or engineering invariant>
Location: <file:line>
Impact: <observable failure or maintenance consequence>
Evidence: <what the artifact does and why it violates the authority>
Direction: <bounded correction, not a speculative rewrite>
```

Omit a candidate rather than produce a vague concern without a location, impact, and falsifiable
claim.

## Severity

| Severity | Meaning |
|---|---|
| `critical` | Likely data loss, credential exposure, destructive unauthorized behavior, or a failure that makes the primary system unusable. |
| `high` | A protocol violation, unmet core requirement, materially false public contract, or common-path behavioral failure. |
| `medium` | A real but bounded correctness, architecture, compatibility, operability, or test-coverage risk. |
| `low` | Localized clarity, maintainability, or uncommon-edge weakness with limited immediate impact. |
| `advisory` | Subjective organization or polish suggestion that may improve comprehension but is not a defect. |

Severity measures impact, not whether a change is mandatory.

An implementation feature in an area the protocol leaves unspecified is not a protocol defect. A
proposal to standardize it, even when valuable, is `advisory` and `recommended` unless a separate
existing authority is actually violated; it cannot become `high` or `must_fix` merely because the
protocol is silent.

## Disposition

- Use `must_fix` for verified correctness, safety, protocol, applicable Requirement, or public
  contract failures.
- Use `recommended` for subjective organization, optional hardening, future resilience, or a valid
  alternative with no current authoritative violation.
- A `low` finding may still be `must_fix` when an explicit rule is violated with limited impact.
- A `high` risk may be `recommended` only when it is genuinely outside the accepted requirement or
  compatibility scope; explain why.

## Confidence

- `high`: direct artifact and authoritative text establish the finding.
- `medium`: evidence is strong but one environmental or intent assumption remains.
- `low`: report only as an open question unless the possible impact is critical.

## Aggregated Review Shape

1. Verified findings, highest severity first.
2. Open questions or assumptions that block a conclusion.
3. Lens coverage, including `not_applicable` reasons and reduced-independence fallback.
4. Validation and residual risks.

When no finding survives adjudication, say so explicitly and still report coverage and test gaps.

Do not include generic praise, a long change summary before findings, or raw subagent transcripts.
