# Show the tracker's untriaged tickets on `tcw work inbox list`

## What is wanted

The work inbox should not stop at the raw intake TCW holds itself. On a project
that has connected Jira, `tcw work inbox list` should also report the tickets
that are waiting to be triaged, so that a triage session has one list to work
from rather than two.

In the requester's words:

> In TCW, the inbox list command should also check Jira if the project has Jira
> integration enabled. In order to do this, however, the project config will
> have to declare a Jira query to search for inbox items. The inbox CLI output
> should have two sections, one for files on disk and another for Jira tickets.

Three parts to that, and the second is the requester's own framing rather than
an inference: the project must **declare** the query that selects its inbox
tickets — the existing query that selects tickets ready to be taken is not it —
and the output grows **two sections**.

## Decisions the requester made when asked

- **The tracker section is not read-only.** `inbox show <ticket>` and
  `inbox accept <ticket>` should both work on a ticket the section printed, with
  accept doing what taking a ticket already does — claim it, bind it, create the
  item. This is deliberately wider than the sentence above, which named only
  `list`: the requester chose full triage parity over a list that has to be
  acted on from a different command.
- **A project without the new query sees no change at all.** No headings, no
  empty section, no note. What `inbox list` prints today it keeps printing, and
  the sections appear only once a project declares the query.
- **A ticket that already has a work item is the query's problem, not TCW's.**
  Asked whether the section should hide tickets already bound to an item, the
  requester was explicit: *"The Jira query for the inbox tickets should account
  for this. We should not need to handle this case ourselves."* So no
  binding-aware filtering, and no board scan to support one.

## Constraints

- **Raw intake must survive a tracker that is down.** The inbox is how work gets
  triaged; a project that has connected a tracker must not lose the half of the
  answer that needs no network when the network is the thing that failed.
- **Nothing here may be paid for by projects that have no tracker.** That is the
  overwhelmingly common case, and it already holds for every other tracker
  surface — a project with no tracker configured loads none of that code.
- **A ticket is not raw intake.** The inbox's existing entries are opaque
  store-provided references that a store hands out; tickets come from somewhere
  else entirely, and both now have to be addressable from the same commands.
  How that is reconciled is the spec's to decide, but it may not be decided by
  teaching either half to pretend to be the other.

## Out of scope

- Any second tracker provider. Jira Cloud is the only provider that parses
  today and this does not change that.
- Changing what the existing ticket-listing commands select or print.

## References

Asked; none provided.

## Notes

- This request was made in chat, so there is no intake. Everything above is
  either the requester's own words, quoted, or an answer they gave to a direct
  question — the three decisions are recorded as theirs rather than as
  inference.
- One tension the requester was not asked about, recorded here for the spec
  rather than settled: accepting a raw entry is refused today under strict
  tracker mode, which tells the user to take a ticket instead. If accept can
  now take a ticket, that refusal has a case it should no longer refuse. The
  spec has to decide it explicitly.
