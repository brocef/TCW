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
if the file did not exist.

**The API already expresses the difference; only the UI discards it.** The item
detail endpoint (`tcw/serve/__init__.py`, the artifacts list built from
`read_artifact`) sends a blank artifact as `{name, present: false, revision,
mediaType}` and an absent one as `{name, present: false}` with no revision, and
`tests/test_serve.py::test_a_blank_artifact_still_reads_back_with_its_revision`
pins that. The client type already carries `revision?`. What treats every
`!present` alike is the UI: the "not yet present" message in
`web/client/src/ui/work-document-tabs.tsx`, and `content-views.tsx`, which hides
non-tab artifacts that are not present. (Corrected by the 2026-09-15 backlog
audit; the original text said the API could not express the difference.)

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
- **The abstraction litmus test is already answered by the store contract.**
  `WorkStore.artifacts()` in `tcw/store/base.py` says "An adapter has to
  implement both rules, not one", and `read_artifact` returns a blank artifact
  with a revision and `None` only when nothing exists. A store that lists only
  non-empty resources would break that contract, so it is not a case to design
  for. The spec's real choice is between a UI-only change (treat "revision set,
  `present` false" as blank) and an explicit field, so the UI does not depend on
  whether a key happens to be there.

## Out of scope

**The CLI.** The requester has settled this as web-only: the affordance problem
is in the web UI, and the CLI keeps today's single presence answer. If the spec
finds that the two surfaces cannot honestly diverge, that is a finding to raise
rather than a licence to widen the item.

## References

- [`2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`](tcw://W/2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule)
  — the item this follows up; it establishes the single presence story that must
  survive, and separated the two facts this item wants surfaced.

## Notes

- Asked for further reference material; none provided beyond what the intake
  already cites.
- The intake floats a second field (`exists` alongside `present`) as one shape.
  Recorded as the requester's illustration of what they mean, not as a chosen
  solution — the spec picks the mechanism.
