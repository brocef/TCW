# Close the originating GitHub issue when a work item completes

## Origin

Requested by the user during the `verify` stage of
[`2026-07-29-triage-github-issues-into-tcw-work-items`](../../review/2026-07-29-triage-github-issues-into-tcw-work-items/),
while approving the replies that item's first live sweep produced:

> part of the TCW work item close-out checklist will be to reply that it is
> fixed and to close the issue

Raised as a separate item rather than folded in, because **that item's spec
listed this as an explicit non-goal** ("No back-sync. Completing the work item
does not close the issue. The link is one-directional and written once."). It
was scoped out deliberately; this reverses that decision, so it gets its own
request rather than widening a spec at verify time.

## Product changes

Today `tcw-triage-issues` writes a one-way link: an accepted issue's URL lands in
the new item's `## Origin`, and nothing ever goes back. The reporter is told the
work is tracked and then hears nothing again, even when it ships.

The request is to close that loop at completion — when a work item that came from
a GitHub issue completes, reply on the issue saying it is fixed, and close it.

Three live examples exist right now: issues
[#9](https://github.com/brocef/TCW/issues/9) and
[#8](https://github.com/brocef/TCW/issues/8) were both told "leaving this open
until it ships", which is a promise this item has to make good on.

## Technical changes

Nothing decided — that is the `spec` stage's job. The shape of the question:

- **Where does the trigger live?** The completion path is `tcw work complete`,
  and per this repo's harness rule anything that must be *guaranteed* belongs in
  the CLI rather than in skill prose. But posting to GitHub from the CLI pulls a
  network dependency and a `gh`/token requirement into a command that has neither
  today, and completion must not fail because GitHub is unreachable.
- **How is the issue found?** The link is the URL in `## Origin`, written as
  prose. Reading it back is a parse, which is the cost of having declined a
  first-class field. Whether that is good enough, or whether this is the change
  that finally justifies a `source`/`external-ref` field on the work model, is
  the central spec question — and the abstraction litmus test applies.
- **Approval.** The sibling skill's core guarantee is that nothing reaches GitHub
  without the user approving the exact text. A closeout step that posts
  automatically would break that rule from the other end.
- **Which resolutions close the issue?** `done` clearly. `duplicate` and
  `superseded` and `wontfix` all mean something different to the reporter, and
  issue #5 in this very repo shows how badly a `superseded` item reads if it is
  reported as a plain rejection.

## Meta changes

Touches `skills/tcw-triage-issues/SKILL.md` (it currently states the link is
one-directional), `skills/tcw-work/references/stage-verify.md` or
`transitions.md` if the checklist grows a step, and the capability
`plugin/triage-github-issues`, whose description says the sweep records the issue
"which is also how a later sweep recognizes it as already tracked" — a
one-directional claim.

## Notes

**Constraints**

- `tcw work complete` must not become able to fail because a network call did.
- A Codex user must get the same behavior; if this lands only as Claude-side
  skill prose, it is in the wrong layer.

**Out of scope**

- Any broader GitHub sync — labels, assignees, milestones, status mirroring.
  This is one reply and one close, at one moment.
