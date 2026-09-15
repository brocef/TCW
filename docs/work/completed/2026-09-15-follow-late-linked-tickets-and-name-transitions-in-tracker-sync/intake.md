## Inbox manifest

- `2026-09-14-follow-ups-the-lifecycle-sync-review-left.md`

## Inbox body

# Follow-ups the lifecycle synchronization review left

Found by the adversarial review of
`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`. Each was judged
to need its own change rather than a fix on that branch.

## 1. Any staged sidecar write blocks a worktree item's merge-back

**Widened by the combined review of the tracker epic's children (2026-09-15).** Git
refuses a non-fast-forward merge while *any* file is staged, not only files in the
merging item's folder. So a `sync` or `comment` record staged on item Y blocks the
merge-back of worktree item X, and `_complete`'s hint only looks at X's own
`tracker.yaml`. Progress comments make records more common: a project whose account
may move tickets but not comment gets a comment record on every move. The hint
should check `git diff --cached` across the whole store.

`tcw work complete` merges the item's work branch into the primary checkout
(`merge_worktree`, `tcw/store/fs.py`). The branch carries the item's folder, so a
staged but uncommitted file in that folder on the primary checkout makes git refuse
the merge ("would be overwritten by merge"). Sidecar writes are staged, never
committed: `tracker link`, `tracker unlink`, and now the synchronization record all
do it. The synchronization item added a hint naming the record when one exists;
`link` and `unlink` on a worktree item still produce only git's message.

Options: commit sidecar writes made to an item with a worktree, or check for staged
changes in the item's folder before merging and name them.

## 2. Two failed moves and a hand move read as drift

A `submit` whose delivery fails records `since: In Progress`. A `complete` that
also fails keeps that `since` and replaces the move. If someone then moves the
ticket by hand to `In Review`, `sync` accepts `since` (`In Progress`) or the recorded
move's target (`Done`), not `In Review`, and reports the ticket as moved in the
tracker. Accepting every mapped status between `since` and the target would close
it.

## Triage (2026-09-15)

Merged at triage because every part changes how `tcw work tracker sync` and the
outbound delivery decide and report a move (`tcw/tracker/sync.py` and the `sync`
command): the maintainer asked for items that touch the same feature to be combined.

- **In scope:** §2 of the entry above; GitHub issues #40 and #42 below; §2 of
  `2026-09-15-strict-mode-and-sync-follow-ups-from-the-combined-review.md` below.
- **Not in scope here:** §1 of the entry above (staged sidecar writes blocking a
  worktree merge-back) is tracked with the tracker binding reads and writes item.
- GitHub #41 (moving an unassigned ticket) is related and was held back at triage
  for further discussion.

## Origin: GitHub issue #40

GitHub issue [#40](https://github.com/brocef/TCW/issues/40), filed 2026-09-15 by @brocef:
**Let work.tracker name the transition for a status move, so sync works when two transitions lead to the same status**

> ### Motivation
>
> Status sync chooses a Jira transition by where it leads and nothing else. `assess_move` in `tcw/tracker/sync.py` needs exactly one offered transition that ends in the mapped status. When two do, the move is recorded as `conflicting` and the ticket stays where it is.
>
> Many Jira workflows have two transitions into `Done`: one for finished work and one for abandoned work, told apart by the resolution each sets. On such a workflow `complete` can never sync, and neither can a discard mapped to the same status. Retrying with `tcw work tracker sync` hits the same check. No setting in `work.tracker` gets around it.
>
> Environment:
>
> - tcw version: 2.2.0
> - OS / platform: macOS 26.6.2
> - Install method: pip, into a pyenv-managed Python 3.14
> - Tracker: Jira Cloud, company-managed project
>
> Steps, against a project whose workflow is Triage → To Do → In Progress → In Review → Done, with `Complete` (from In Progress and In Review) and `Cancel` (from every open status) both ending in `Done`:
>
> ```yaml
> work:
>     tracker:
>         provider: jira-cloud
>         base-url: https://example.atlassian.net
>         candidate-query: project = EX AND status = "To Do"
>         credentials:
>             email-env: EX_JIRA_EMAIL
>             token-env: EX_JIRA_TOKEN
>         transitions:
>             claim: Start
>         statuses:
>             active: In Progress
>             review: In Review
>             completed: Done
>             discarded: Done
>         comments: true
> ```
>
> 1. `tcw work new "Example item"`, then `tcw work tracker link <slug> EX-1` with EX-1 in To Do
> 2. `tcw work start <slug>`: the ticket is claimed and moves to In Progress
> 3. `tcw work submit <slug>`: In Review. `tcw work rework <slug>`: back to In Progress. `submit` again: In Review. All as expected.
> 4. `tcw work complete <slug> --resolution done --confirm`: the item completes locally, the command exits 1, and `tracker.yaml` gains:
>
> ```yaml
> sync:
>   state: conflicting
>   move: complete
>   since: In Review
>   claim: done
>   reason: EX-1 offers more than one transition to 'Done' (ids 41, 61); TCW will
>     not guess which.
> comment:
>   move: complete
>   state: conflicting
>   reason: EX-1 did not follow its item, so its comment waits for it.
> ```
>
> The workaround we used was to change the Jira workflow so `Cancel` ends in a separate `Won't Do` status (in the Done category), then map `discarded: Won't Do`. That works: complete then reaches `Done` and a discard reaches `Won't Do`. But it means changing a shared workflow to suit the tool, which not every team can do.
>
> ### Description
>
> Let `work.tracker.transitions` name the transition for a status move, the same way `transitions.claim` already names the claim:
>
> ```yaml
>         transitions:
>             claim: Start
>             completed: Complete
>             discarded: Cancel
>             # or, per resolution:
>             # discarded:
>             #     wontfix: Cancel
>             #     duplicate: Mark Duplicate
> ```
>
> - When a move has a named transition, sync applies the offered transition with that name. It still checks that the transition leads to the status in `statuses`, and reports `conflicting` if it does not.
> - When a move has no named transition, today's rule (exactly one transition into the target) is unchanged.
> - `tcw validate` checks the new keys the way it checks `statuses`: the same status keys, the same resolution names, text values only.
>
> A smaller alternative: when several transitions reach the target, pick the one whose name is configured, and report `conflicting` only when none is.
>
> This concerns the **work** axis (tracker sync).
>
> ### Benefits
>
> - Teams whose workflow separates finished from abandoned work by transition, not by status, get complete and discard sync without restructuring their Jira workflow.
> - A discard can use the transition that sets the matching Jira resolution (for example Won't Do or Duplicate), so the ticket's resolution agrees with the item's.
> - The failure stops being permanent: today the only fixes are editing the workflow or moving every resolved ticket by hand.

## Origin: GitHub issue #42

GitHub issue [#42](https://github.com/brocef/TCW/issues/42), filed 2026-09-15 by @brocef:
**Linking an item that is already active leaves its ticket behind for good, and sync reports it as tracker drift**

> ### Environment
>
> - tcw version: 2.2.0
> - OS / platform: macOS 26.6.2
> - Install method: pip, into a pyenv-managed Python 3.14
> - Tracker: Jira Cloud, company-managed project
>
> ### Steps to reproduce
>
> Workflow: To Do → `Start` → In Progress → `Submit` → In Review → `Complete` → Done, plus `Cancel` to Won't Do. Config as in the tracker docs, with `claim: Start` and `statuses` mapping `active: In Progress`, `review: In Review`, `completed: Done`, `discarded: Won't Do`.
>
> 1. `tcw work new "Example item"`, then `tcw work start <slug>`. The item is not bound yet, so no tracker call is made. This is the normal state of in-flight work on a team that adopts the tracker part-way through.
> 2. `tcw work tracker link <slug> EX-4`, where EX-4 is in To Do and unassigned:
>    `→ bound <slug> to EX-4 (…). The ticket is unchanged in the tracker.`
> 3. `tcw work tracker sync <slug>`:
>    `<slug>: conflicting — EX-4 is assigned to nobody, not to you, so it was not moved from 'To Do' to 'In Progress'.` (exit 1)
> 4. `tcw work submit <slug>`: the item moves to review, the ticket stays in To Do, and `tracker.yaml` records:
>
> ```yaml
> sync:
>   state: conflicting
>   move: submit
>   since: In Progress
>   claim: done
>   reason: EX-4 is assigned to nobody, not to you, so it was not moved from 'To Do' to 'In Review'.
> ```
>
> 5. Assign EX-4 to yourself in Jira, then `tcw work tracker sync <slug>` again:
>
> ```text
> <slug>: conflicting — EX-4 is in 'To Do', not 'In Progress' or 'In Review'; it was moved in the tracker, or TCW held it there for another part of the ticket whose item is not in this checkout. TCW does not move it back: put it in 'In Progress' or 'In Review', or move it on by hand.
> <slug>: comment still owed — the ticket has not followed yet
> ```
>
> ### Expected vs. actual
>
> - Expected: binding an item that is already active or in review brings the ticket to the item's status, or at least `sync` can do it once the ticket is assigned. Linking is documented as the way to tie existing work to its ticket, and existing work is often already in progress.
> - Actual: the ticket stays at its old status for good. Nothing TCW runs will move it, so every later move on the item is `conflicting` until someone walks the ticket through the workflow by hand. Two details make this harder to understand:
>   - `claim: done` is recorded, although nothing was ever claimed. The item was started before it was bound, and the ticket never left To Do.
>   - The final message says the ticket "was moved in the tracker, or TCW held it there for another part". Neither is what happened: it was never moved, because the binding was made after the item started.
>
> ### Remediation
>
> Suggestions, in order of preference:
>
> 1. When `link` binds an item whose status maps to a later ticket status than the ticket's, bring the ticket forward along the workflow, claim first. For example, from To Do: `Start` (assigning, as a claim does), then `Submit` for an item in review. Or offer this as `link --sync`.
> 2. At minimum, have `sync` on a freshly linked item with no earlier record treat "ticket behind the item" as something it can advance, rather than as drift it must not undo.
> 3. Record `claim: owed` (not `done`) when a bound item is active but its ticket was never claimed, and word the conflict message for this case ("the ticket was bound after the item started and has not been brought forward").
>
> Workaround today: before or after linking, move the ticket in Jira to the status the item's status maps to and assign it to yourself.
>
> This concerns the **work** axis (tracker bindings and sync).

## Folded in: from inbox entry `2026-09-15-strict-mode-and-sync-follow-ups-from-the-combined-review.md` (Strict mode and sync: follow-ups from the combined review)

### 2. `sync`'s owner rule can leave a strict item stuck

`tcw work tracker sync` skips an item whose owner is someone else and still exits 0.
Strict mode refuses while a record exists. Take an active item started as
`--owner agent-7` whose record says the claim is still owed:

- `submit`, or `start --take-over`, is refused with "run sync";
- `sync` from a shell without `TCW_WORK_OWNER=agent-7` prints "skipped" and exits 0.

**Suggested fix:** exit 1 when a slug named on the command line is skipped, and
mention `TCW_WORK_OWNER` in the strict refusal.

## Folded in after triage discussion (2026-09-15)

GitHub #41 was held back at triage and then accepted into this item by the maintainer,
with its scope fixed to the issue's "discard only" option: a discard may move an
unassigned ticket; every other move keeps today's assignment check.

## Origin: GitHub issue #41

GitHub issue [#41](https://github.com/brocef/TCW/issues/41), filed 2026-09-15 by @brocef:
**A status move refuses an unassigned ticket, so discarding unstarted work leaves its ticket open**

> ### Motivation
>
> Every status move checks that the ticket is assigned to the signed-in account before moving it. For work that was started with `tcw work start`, that is right: the claim assigned the ticket. But a common shape never goes through a claim: a backlog item is bound to an unassigned ticket, and then the work is dropped. The discard is refused in Jira, so the ticket stays open, even though the workflow allows the transition and nobody else holds the ticket.
>
> This is easy to hit when adopting the integration. A team queue usually selects `assignee IS EMPTY` tickets, as ours does, and binding a backlog of existing items leaves every ticket unassigned until someone starts it. In our first real use, 115 of 125 bound tickets were unassigned, so discarding any of those items leaves a stale open ticket.
>
> Environment: tcw 2.2.0, macOS 26.6.2, pip into a pyenv-managed Python 3.14, Jira Cloud company-managed project.
>
> Steps (workflow: To Do → In Progress → In Review → Done, plus `Cancel` from every open status to `Won't Do`; no conditions or validators on any transition):
>
> ```yaml
> work:
>     tracker:
>         provider: jira-cloud
>         base-url: https://example.atlassian.net
>         candidate-query: project = EX AND status = "To Do" AND (assignee = currentUser() OR assignee IS EMPTY)
>         credentials:
>             email-env: EX_JIRA_EMAIL
>             token-env: EX_JIRA_TOKEN
>         transitions:
>             claim: Start
>         statuses:
>             active: In Progress
>             review: In Review
>             completed: Done
>             discarded: Won't Do
>         comments: true
> ```
>
> 1. `tcw work new "Example item"` and `tcw work tracker link <slug> EX-3`, where EX-3 is in To Do with no assignee
> 2. `tcw work complete <slug> --resolution wontfix --confirm`
>
> The item is discarded and committed. The command exits 1 with:
>
> ```text
> tcw work complete: <slug> moved to discarded and was committed; EX-3 was not updated in the tracker (conflicting): EX-3 is assigned to nobody, not to you, so it was not moved from 'To Do' to 'Won't Do'. Run `tcw work tracker sync <slug>` once that is resolved.
> ```
>
> The ticket stays in To Do with no resolution. The only way through is to assign the ticket to yourself in Jira and then run `tcw work tracker sync <slug>`, which then moves it to Won't Do and posts the owed comment. For comparison, the same discard after `tcw work start` (which assigns the ticket) moves it to Won't Do straight away.
>
> ### Description
>
> Treat an unassigned ticket as movable by the account running the command, at least for a discard, instead of as held by someone else. Two ways this could work:
>
> - **Discard only.** A discard may move an unassigned ticket, since closing work nobody started takes nothing from anyone. Other moves keep today's check, because they only happen after `start` has claimed the ticket anyway.
> - **Assign first, as the claim does.** When a move finds the ticket unassigned, assign it to the caller and then transition it, as `import` and `start` already do for the claim. This could sit behind a setting such as `work.tracker.take-unassigned: true` for teams that want unassigned tickets left alone.
>
> Either way, a ticket assigned to a *different* account should still be refused, as now.
>
> This concerns the **work** axis (tracker sync).
>
> ### Benefits
>
> - Dropping backlog work closes its ticket, with no stale open tickets left behind.
> - Teams can bind an existing backlog without assigning every ticket to one person first, which also keeps the shared "unassigned and ready" queue meaningful.
> - The refusal message no longer describes an unassigned ticket as if another person held it.
