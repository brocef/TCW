# Live-Jira walkthrough — plan

The requester decided on 2026-09-23 (`requester-decisions.md`) that this walkthrough
is required before the epic ships. It runs after the last child landed, against the
code on `main`, and it is the last gate before the epic's `verify`. If it disagrees
with the fake tracker, the fake tracker is what is wrong, and that becomes its own
item rather than a quiet change to a criterion.

It proves the epic's criteria 5–8 against real Jira. Each was a defect found in real
use rather than by the suite.

## Where it runs

- **Jira:** the `TCW` project on `proposit.atlassian.net`, with the credentials from
  `~/.bashrc` (`TCW_JIRA_EMAIL`, `TCW_JIRA_API_KEY`).
- **TCW:** a throwaway node in the session scratchpad: a fresh git repository whose
  `tcw-config.yaml` copies this repository's `work.tracker` block. This repository's
  own board, Jira sync and epic ticket `TCW-2` are never touched. The `tcw` on the
  path is the editable install of this checkout, so it runs `main` as committed. The
  walkthrough first confirms this with `python -c "import tcw; print(tcw.__file__)"`.
- **Not strict**, matching this repository's configuration and the criteria as
  written.

## The workflow it runs against

Read from the project on 2026-09-24 (read-only):

| From | Offers |
| --- | --- |
| Triage | Accept → To Do · Cancel → Won't Do |
| To Do | Start → In Progress · Cancel → Won't Do |
| In Progress | Submit → In Review · Complete → Done · Cancel → Won't Do |
| In Review | not yet observed; read during step 3 |
| Done, Won't Do | nothing: both are terminal |

The terminal statuses decide the order below: a ticket that reaches Done or Won't Do
cannot be reused, so two tickets are needed, and each one's closing step comes last.

## Steps

Every hand move in Jira is made through the REST API as the same account, and every
state is read back from Jira instead of trusting TCW's output.

**Setup.** Create tickets **X** and **Y** in `TCW` (issue type Task), each with the
summary "TCW walkthrough throwaway — safe to delete". Accept each from Triage to
To Do, leaving both unassigned.

1. **Criterion 7, link then sync on an active item.** Item A: `tcw work new`, then
   `tcw work start A`, which is not bound yet. Then `tcw work tracker link A X`,
   and confirm that `link --sync-status` is refused. Then `tcw work tracker sync A`.
   Expected: X ends in In Progress. If `sync` instead says to claim first, as the
   Jira guide now documents ("`tracker claim`, then `tracker sync`"), follow that
   advice, record that the criterion's wording predates the design, and check the
   end state.
2. **Criterion 8, a ticket moved ahead by hand is brought back.** Move X by hand to
   In Review (Submit). `tcw work tracker sync A`. Expected: X is back in In Progress.
   This is also where In Review's own transitions are read. If In Review offers no
   way back to In Progress, `sync` should report conflicting instead of doing
   anything else. That would be a finding about criterion 8 on this workflow, not a
   TCW defect, and is recorded as such.
3. **Criterion 5, `start` does not move a ticket backwards.**
   `tcw work tracker unlink A --reason walkthrough`. With X in In Review, unassign
   it by hand. Item B: `tcw work new`, `tcw work tracker link B X`,
   `tcw work start B`. Expected: X stays in In Review, now assigned to the caller.
   Then finish B normally (`submit`, then `complete --resolution done`), so X's
   last state is Done.
4. **Criterion 6, discarding a never-started, unassigned ticket.** Item C:
   `tcw work new`, `tcw work tracker link C Y`, then
   `tcw work complete C --resolution wontfix --confirm`. Expected: exit 0, and Y in
   Won't Do.

Also recorded, without being a criterion: what each command printed, whether any
`tracker.yaml` sync record was left behind (none should be), and that no comment was
posted (`comments` is off).

## Cleanup

- Both tickets end in a terminal status (X in Done, Y in Won't Do) with the throwaway
  summary.
- **Deleting them from Jira is a separate, irreversible step,** done only if the
  requester asks, through `DELETE /rest/api/3/issue/<key>`.
- The scratch node is deleted from the scratchpad.

## Results

_To be filled in by the run._
