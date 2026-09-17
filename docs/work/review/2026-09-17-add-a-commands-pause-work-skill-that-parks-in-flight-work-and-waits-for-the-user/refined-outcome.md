# Accepted

Accepted by the requester on 2026-09-17, after one rework cycle.

_Accepted. This artifact is the verdict; never write it beside a `rework.md`._

## The decision

The first pass was rejected at `verify` — see `rework.md` — for being over-specified
rather than wrong. The second pass simplifies exactly what that rejection named:
the handoff's contents are the pausing agent's judgment, the file is
`handoff-<UTC timestamp>.md`, and the skill is 79 lines. Accepted on that basis.

## Evidence

- `python -m pytest` — **3609 passed, 2 skipped**, re-run after the rework.
- `tcw validate` exits 0, with and without a handoff file present in an item folder.
- `git diff --stat origin/main...HEAD -- tcw/` is empty: the request's hard
  constraint held through both passes.
- Reviewed as [brocef/TCW#57](https://github.com/brocef/TCW/pull/57), `mergeable_state: clean`,
  no open review threads. CI is skipped on this branch by the repository's own
  opt-in policy (`test.yml`), a choice the requester made deliberately rather than
  an unexplained absence.

## Definition of Done

- **tests pass** — above.
- **docs synced** — `README.md`, both `upcoming.md` files, `skills/work/references/commands.md`,
  and the two resume-side skills. The changelog and release note were also corrected
  where this change made an *existing unreleased* entry stale ("sixteen" skills,
  "four" command skills).
- **capabilities reconciled** — `skills/commands-pause-work` flipped `Missing` →
  `Supported` (`a51988f`); taxonomy Feature `commands-pause-work-skill` registered.
- **reviewed** — an independent verifier pass (15/16 criteria, four defects, all
  fixed) plus the requester's own review, which produced the rework.
- **version offered** — offered at closeout; see Deferred below.
- **originating GitHub issue** — none; this came from a chat request.

## Deferred

- **The version cut** is offered separately at closeout rather than taken here.
  This adds a shipped skill, so it is at least a minor bump; the choice is the
  requester's and is made after this item closes, per this repository's own
  ordering (complete → cut → push).
- **Registering `handoff` in `WORK_SIDECARS`** so `tcw` can see, validate and
  display the file. Not filed as a work item: it needs the Python change this item
  excluded, and the judgment of whether it is worth making is better made after the
  convention has been used than before. Blocked on nothing but that experience —
  named here so it is not mistaken for an oversight.

## What this item is worth remembering for

Two things that cost real cycles and would repeat:

1. **A command name in a "not for this" aside got wrong three times running** —
   `tcw work discard` (does not exist), then `tcw work drop` (exists, but refuses
   any item not in `backlog`), and the commit that fixed the first introduced the
   second. The root fix was deleting the command name, not correcting it. Verifying
   `file:line` citations, which this item did carefully, does not verify that a
   named command exists and accepts the implied arguments.
2. **Every acceptance criterion passed while the deliverable was twice the size it
   needed to be.** The criteria asked whether things were *stated*; none could ask
   whether stating them earned the reader's time. A spec that enumerates required
   contents builds in no way to notice that the enumeration is itself the defect —
   which is why the rework came from the requester and not from any gate.

A post-mortem was not run: both are understood, and the second is recorded in the
spec's own Notes.
