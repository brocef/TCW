# Distinguish a blank artifact from an absent one in the web UI

Follow-up from `2026-08-18-reconcile-read-artifact-with-the-canonical-presence-rule`.

That item made `tcw serve` tell **one** story about artifact presence: a
whitespace-only artifact now reports `present: false` everywhere in the payload,
and the `/open` gate agrees, so the UI no longer draws an **Open** button that
can only 404.

Consistent is not the same as informative. A user who scaffolded `spec.draft.md`,
renamed it to `spec.md`, and left it empty now sees exactly what they would see
if the file did not exist. The API cannot currently express the difference, and
the two situations call for different actions: "write the spec" versus "the file
is there, you just haven't filled it in".

Both facts are already available at the boundary — `artifacts()` answers the
lifecycle question and `read_artifact` answers the resource question; the fix was
to stop mixing them, not to discard one. So this is an affordance question, not a
data-availability one.

Worth considering:

- A second field on the artifact summary (`exists` alongside `present`), leaving
  `present` as the lifecycle answer the gate uses.
- Whether the abstraction litmus test is satisfied: could a non-filesystem store
  answer "a resource is here but it is empty"? Probably yes, but it needs
  checking before the field is added — a store that only lists non-empty
  resources could not.
- Whether the CLI should show it too, or whether this is web-only.

Deliberately not urgent: nothing is broken now, and the previous behaviour was.
