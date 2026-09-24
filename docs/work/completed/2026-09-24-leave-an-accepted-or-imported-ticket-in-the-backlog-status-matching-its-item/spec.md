# Spec: leave an accepted or imported ticket in the backlog status, matching its item

## Capability changes

- **changed** `work/manage-external-tracker-intake` — after the claim, an import
  (and so an inbox accept) puts a ticket it moved back where the claim found it,
  still assigned to the importer, so the ticket reads as not started, like its
  item. Under strict mode it stays where the claim left it, as today. The
  description gains that sentence and one new accepted limit (Risks, R1).

No taxonomy change: no new term or feature.

## Problem

`tcw work tracker import <KEY>`, and `tcw work inbox accept <KEY>`, which runs it
(`_inbox_accept`, `tcw/work/cli.py:864`, ends in `_tracker_import`), claim the
ticket with `claim` (`tcw/tracker/intake.py:607`). `_claim_from` applies
`work.tracker.transitions.start` (`intake.py:650`, applied at `:703`), assigns only
when that applied (`:712`), and counts the claim only when the read-back shows the
ticket in the transition's destination and assigned to the caller (`:726-729`). On
an ordinary workflow that destination is the active status.

`_tracker_import` (`tcw/work/cli.py:2594`) then creates a **backlog** item with no
owner. `docs/guide/jira.md:263-266` says this is deliberate ("because importing is
not starting"). So from the moment the item exists, the ticket says In Progress and
the item says backlog.

Nothing corrects that later. `deliver` never gives a backlog item's ticket a
target (`tcw/tracker/sync.py:352-364`), on purpose: `sync` once pulled a ticket the
user was **already working** back to To Do, with nothing printed. So
`tcw work tracker sync <slug>` reports the item `current`. Seen for real with TCW-1
on 2026-09-24.

## Goals

1. When this run's claim **moved** the ticket (`outcome.transitioned`), and strict
   mode is off, `import` and `inbox accept` put the ticket back in the status the
   claim found it in, once the item and its binding are written. That status is
   read after any `pre-backlog` step, so a ticket taken out of Triage goes back to
   the backlog status, not to Triage. It stays assigned to the importer.
2. The way back is one transition from where the ticket now is to that status,
   found from what the ticket offers, with the same rule a lifecycle move uses
   when no transition is named (`assess_move`, `sync.py:245`): exactly one offered
   transition leading there, or nothing is sent.
3. When the ticket cannot go back (no such transition, more than one, a tracker
   error, or a read-back showing it somewhere else), the import still succeeds
   (exit 0). It prints one `warning:` line saying where the ticket is, that its
   item is in the backlog, and that it can be moved back by hand or left until the
   item starts.
4. The summary line `→ <KEY> is in '<status>', claimed by this run; bound to
   <slug>` names the status the ticket ends in.

## Non-goals

- **A ticket the claim did not move** (row `1e`: already assigned to the caller,
  so no transition was sent) is left where it is. That is work already under way,
  and moving it back is exactly the silent regression `deliver` guards against.
- **Strict mode** (`work.tracker.strict: true`) is unchanged. Its import checks
  exclusivity *at the status the claim leads to* (`claim_refusal`, `sync.py:1077`)
  and requires the ticket to be there. Moving the ticket back would offer the
  exclusive transition again, which is the proof strict mode rests on.
- **`tcw work tracker claim` with `exclusive-claim-transition`**, which also moves
  the ticket of an item that may be in the backlog. That move is documented as
  the point of the key (`jira.md:85`) and is the strict-mode path. The repo-wide
  sweep found no other command that claims through a transition and leaves the
  item in the backlog: `start` moves the item to `active` as well, and
  `tracker create` puts a new ticket in `statuses.backlog` directly.
- **Changing `deliver`/`sync`** to move backlog items' tickets. The guard at
  `sync.py:352` stays as it is.
- **Changing the claim itself** (`_claim_from`), including re-reading the assignee
  before assigning (see R1).

## Design

**Where.** One new function in `tcw/tracker/intake.py`, beside `claim`, that takes
the client, the claim's outcome and the status to return to. It re-reads the
ticket (`read_ticket`), asks `assess_move(ticket, target=<status>, expected=(),
move=None)` for the transition, applies it (`client.apply_transition`), and reads
the ticket back. It returns the status the ticket ends in and, when it did not get
back, a reason. It raises nothing a caller must handle: tracker errors become a
reason.

`claim` records the status it found the ticket in, after any pre-backlog step, on
`ClaimOutcome` (a new `claimed_from` field, set with `replace` on the success path,
like `left_status`), so the caller does not have to thread it through.

`_tracker_import` calls the function after the binding is written and before it
prints the summary line, only when `outcome.transitioned`, `claimed_from` is set,
`claimed_from` is not already the ticket's status, and strict mode is off. It then
prints the summary with the status the ticket ended in, and the `warning:` line
when it did not get back.

**Why after the item exists.** Every failure before that point already makes the
user run the command again. A re-run finds the ticket assigned to them (row
`1e`), sends no transition, and so moves nothing back. Moving back earlier would
leave a ticket in the backlog, assigned, with no item, and a re-run could not tell
that apart from work that was never claimed. After the binding is written, the only
thing at stake is the ticket's status, which is why a failure there is a warning.

**Abstraction test.** The operation is "move a ticket, by one offered transition,
to a named status", which any tracker adapter can do. Nothing here is a filesystem
detail.

**Harness.** CLI behavior only, identical under Claude and Codex.

**Docs.** `docs/guide/jira.md`, around the claim's steps (`:249-256`) and "What
`import` creates" (`:263`); the capability description; the changelog and release
notes in `docs/{changelogs,release-notes}/upcoming.md`.

## Acceptance criteria

Checked with the stateful fake in `tests/tracker_fake.py`, on a workflow that
offers a way back from In Progress to To Do (such as `GLOBAL`) unless a criterion
says otherwise.

1. `tracker import` of an unassigned To Do ticket exits 0, creates one backlog
   item, and leaves the ticket in **To Do**, assigned to the importer. The writes
   sent are, in order: the claim transition, the assignment, the transition back.
2. The same holds for `inbox accept <KEY>`.
3. With `pre-backlog: {Triage: Accept}`, a Triage ticket ends in the backlog
   status (To Do), not in Triage.
4. A ticket already In Progress and assigned to the importer (row `1e`) is bound
   with **no** write, and stays In Progress.
5. On `DIRECTED` (no way back from In Progress), import exits 0, creates and binds
   the item, the ticket stays In Progress, and stderr has one `warning:` line
   naming the ticket and 'In Progress'.
6. When the transition back fails with a tracker error, import exits 0, the item
   exists and is bound, and stderr has the `warning:` line.
7. Under `work.tracker.strict: true` (with an exclusive workflow), a successful
   import sends no transition back, and the ticket stays in the active status.
8. The summary line names the status the ticket ended in: 'To Do' in 1, 'In
   Progress' in 5.
9. The full suite passes, run the way CI runs it (bare `pytest`).

## Risks

- **R1: a narrower, new race.** Once the ticket is back in To Do, it offers the
  claim transition again. A second importer whose *read* of the ticket came
  before the first claim, and whose *transition* comes after the move back, gets
  its transition applied, and then assigns itself, because `_claim_from` decides
  whether to assign from that earlier read (`intake.py:712`). Both people would
  then have items, and the second holds the ticket. This needs two imports of one
  ticket within the few seconds one import takes, and a ticket that is anyone's
  to take (unassigned). A second importer arriving any later is refused at step 1
  (assigned to someone else). Accepted and written into the capability's limits;
  strict mode is not exposed to it. The fix, if it is ever seen, is to re-read the
  assignee just before assigning.
- **R2: projects relying on import to mark work started.** A team that read "In
  Progress" as "someone has picked this up" loses that signal until the item
  starts. The assignee still shows who holds it. Recorded in the release notes.
- **R3: an extra transition in the ticket's history** on every import. Harmless,
  but visible.

## Notes

- Choosing "the status the claim found it in" rather than `statuses.backlog`
  means no new configuration, and it works for projects that never mapped a
  backlog status (this one had none until 2026-09-24). After a pre-backlog step
  the two are the same by construction: the step must land on `statuses.backlog`
  (`jira.md:354-356`).
