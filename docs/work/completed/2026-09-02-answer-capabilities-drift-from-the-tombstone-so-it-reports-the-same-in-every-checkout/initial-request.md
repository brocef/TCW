# Answer capabilities drift from the tombstone so it reports the same in every checkout

## What is being asked for

`tcw capabilities drift` should give the same answer in every checkout of a
project at the same commit. Today it does not: it reports drift for whoever
completed the work and reports nothing for everyone else, which means it says
nothing in CI and nothing in a colleague's clone.

The second half of the request is wider than that one command. **Find every
other place in the codebase that decides "did this ship?" or "did this ever
exist?" by asking whether an item is currently in the store**, and report what
it finds. Two sweeps have already looked for exactly this pattern and both were
recorded as complete while missing an instance. A third informal pass is likely
to miss one too, so the sweep is part of the deliverable rather than a step on
the way to it.

## Why it matters

Resolved items are kept out of the tracked tree on purpose, but their folders
stay on the machine that resolved them. Anything that reads the store to decide a
question about finished work therefore gets a different answer depending on who
is asking. That is the same defect the tombstone work removed for references
between items, and it fails in the quiet direction here: `drift` under-reports,
so a capability left `Missing` after its work shipped is simply invisible
everywhere except one laptop.

This was found by the adversarial review of the tombstone item, not by anyone
using the command, which is itself the point — a check that silently reports
nothing is not a check anybody notices is broken.

## Constraints

- **Keep the distinction the current code makes deliberately.** `drift` asks
  "did it ship?", not "is it closed?". A discarded item's capability is supposed
  to stay `Missing`, and reporting it as shipped-but-unreconciled would be a
  false positive. The comment in `tcw/capabilities/cli.py` says so explicitly and
  records that this was got wrong once before.
- **When it cannot tell, it says nothing.** A record backfilled with
  `tcw work tombstone add` often carries no resolution, because whoever
  backfilled it did not know one. In that case `drift` reports nothing rather
  than guessing. Requester's decision, made with the trade-off stated: it means
  a project that backfilled without resolutions gets no drift detection for those
  items until someone fills them in, and that is preferred to ever calling
  abandoned work shipped.

## Out of scope

- **`unresolved_blockers`.** Making it distinguish a resolved blocker from a
  misspelled one is a separate decision that changes when transitions refuse. It
  was already non-goaled once, deliberately, and stays out here.
- **Backfilling resolutions into anyone's existing graveyard.** The constraint
  above accepts that unresolved records are silent; it does not ask for a pass
  that fills them in.
- **Anything about how long resolved documents are kept.** That stays the repo
  manager's call via `.gitignore`, as before.

## Notes

- Asked the requester for reference material; none provided. The intake is the
  whole of the supplied context.
- The request originates from a review finding rather than from a user hitting
  the bug, so there is no reporter to report back to and no reproduction from
  the field — only the code path.
- Worth knowing while specifying: the tombstone record that makes this
  answerable at all is new, and a project only benefits from it for work
  resolved after it shipped, or work someone has explicitly backfilled. The
  request does not assume otherwise.
