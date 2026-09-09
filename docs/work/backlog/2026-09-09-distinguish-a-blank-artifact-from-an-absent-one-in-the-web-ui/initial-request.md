# Distinguish a blank artifact from an absent one in the web UI

## What is wanted

A user looking at the web UI should be able to tell "the file is not there" from
"the file is there and you have not filled it in", because the two call for
different actions.

## The observation

An earlier item made `tcw serve` tell one story about artifact presence: a
whitespace-only artifact reports `present: false` everywhere in the payload and
the `/open` gate agrees, so the UI no longer draws an **Open** button that can
only 404. That was the right fix and is not in question.

Consistent is not the same as informative. A user who scaffolded `spec.draft.md`,
renamed it to `spec.md`, and left it empty now sees exactly what they would see
if the file did not exist. The API cannot currently express the difference.

## Why it matters

The two situations ask for different next moves — "write the spec" versus "the
file is there, you just have not filled it in" — and the UI currently gives the
same prompt for both. Nothing is broken; the previous behaviour was worse. This
is an affordance gap, and it is recorded as deliberately not urgent.

## Constraints

- **Both facts are already available at the boundary.** `artifacts()` answers
  the lifecycle question and `read_artifact` answers the resource question. The
  earlier fix stopped mixing them; it did not discard either. So this is an
  affordance question, not a data-availability one.
- **`present` keeps its meaning.** Whatever expresses the distinction must not
  change what the gate reads, or the 404-button defect returns.
- **The abstraction litmus test is an open question here, not an assumption.**
  Could a non-filesystem store answer "a resource is here but it is empty"?
  Probably, but a store that only lists non-empty resources could not, and that
  needs checking before any second field is added.

## Out of scope

**The CLI.** The requester has settled this as web-only: the affordance problem
is in the web UI, and the CLI keeps today's single presence answer. If the spec
finds that the two surfaces cannot honestly diverge, that is a finding to raise
rather than a licence to widen the item.

## References

- `2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`
  — the item this follows up; it establishes the single presence story that must
  survive, and separated the two facts this item wants surfaced.

## Notes

- Asked for further reference material; none provided beyond what the intake
  already cites.
- The intake floats a second field (`exists` alongside `present`) as one shape.
  Recorded as the requester's illustration of what they mean, not as a chosen
  solution — the spec picks the mechanism.
- Its predecessor is named as a plain slug rather than a `tcw://` reference:
  it resolved and was removed before tombstoning existed, so the record
  cannot answer for it and a link would dangle permanently.
