Filed out of the fix for `tcw work show --json` on a resolved-and-deleted slug,
which now exits 1 with an empty stdout rather than printing the human block under
a success code.

`Tombstone` exists to answer one question — *did this slug ever exist here?* — so
that a reference to finished work is distinguishable from a reference to a typo.
After that fix the only interface that answers it is the human block. There is no
`tcw work tombstone show`; the subcommand has only `add`. A script has no way to
ask.

Projecting the tombstone through `tcw work show --json` was considered and
rejected: `WORK_ITEM_SCHEMA` is closed twice over (`additionalProperties: False`,
and `required` computed as every property), `hook_payload` already cites that
closedness as the reason a sibling key goes in the envelope rather than beside
`body`, and `tcw serve` returns the same document — so a second shape under
`schema: 1` is a contract change in three places, not a bugfix. `hook_payload` is
also the precedent for this state: with no item it sends `{"item": null, …}`.

The cheapest shape is a separate question with its own `schema` key —
`tcw work tombstone show <slug> [--json]` — leaving `WORK_ITEM_SCHEMA` closed and
letting `tcw serve` grow a matching route if it is ever worth one.

One design trap to settle rather than trip over: `Tombstone.location` is
documented as opaque, presentation-only and never parsed, and the human path
prints `describe_location(...)`. A JSON document must therefore either embed a
rendered presentation string in a DTO or hand a machine a handle it is forbidden
to parse. Neither is obvious, which is why this is a design question rather than
a line that belonged in the fix.
