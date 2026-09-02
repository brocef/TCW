As a user, I run `tcw capabilities drift` to find where the standing capability
ledger has fallen out of step with reality. It reports two kinds of drift: an
inherited capability I have never reviewed locally, and a local capability still
marked Missing whose `Planning doc` names a work item that already shipped. The
command exits non-zero when it finds either, so it works as a check in a
pipeline as well as a report.

The `Planning doc` lookup resolves through the project's configured work store,
wherever `work.path` puts it — including another Git repository — so drift is
reported the same way whether the project uses the default layout or an external
store, and a leftover `docs/work/` folder neither creates nor suppresses a
finding. A project with no usable work component degrades to silence rather than
an error: drift detection follows an existing capability→work pointer and never
makes the capabilities axis depend on the work axis.

Only `completed` counts as shipped. A discarded item's capability is supposed to
stay Missing, and an item still in `backlog`, `active`, or `review` has not
shipped yet, so neither is reported.

**The answer does not depend on which checkout I run it in.** A finished item's
documents leave the tracked tree, so asking whether the item is still there
would have told me one thing on the machine that finished the work and another
thing everywhere else — quietly, since the missing answer looks exactly like no
drift. Where the item has gone, the command reads the record its resolution left
behind, which every clone has.

One limit follows from that, and it is deliberate. A record backfilled with
`tcw work tombstone add` may carry no resolution, because whoever backfilled it
did not know one. The command cannot tell whether that work shipped or was
abandoned, so it reports nothing rather than guessing — I would rather miss a
capability than be told abandoned work shipped.
