As a user, I run `tcw capabilities drift` to find where the standing capability
ledger has fallen out of step with reality. It reports two kinds of drift: an
inherited capability I have never reviewed locally, and a completed work item
whose `capabilities.yaml` declares a change today's ledger no longer shows — a
`new:` capability that is gone or reads `Missing` again, a `changed:` one that
is gone, a `removed:` one that is back, and the same for the taxonomy terms it
declares. When several items declare the same path, the most recently created
one decides, and two created the same day that disagree are reported as
ambiguous. The command exits non-zero when it finds
either, so it works as a check in a pipeline as well as a report.

The work items are read from the project's configured work store, wherever
`work.path` puts it, and a completed item's folder never moves, so the answer is
the same in every checkout. Only the `completed` stage counts: a discarded item
shipped nothing, and an unfinished one has not shipped yet. An item whose
`item.yaml` cannot be read is reported, since its declarations went unchecked.
A project with no work store degrades to silence rather than an error, so the
capabilities axis never depends on the work axis.
