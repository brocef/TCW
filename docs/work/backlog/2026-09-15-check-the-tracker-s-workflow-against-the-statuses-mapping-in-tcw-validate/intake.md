# Check the tracker's workflow against the statuses mapping in tcw validate

## Origin

GitHub issue [#44](https://github.com/brocef/TCW/issues/44), filed 2026-09-15 by @brocef:
**Add tcw work tracker check: verify the statuses mapping against the tracker's workflow before an item depends on it**

> ### Motivation
>
> A `work.tracker` block can be well-formed and still unable to move tickets, and today nothing finds that out until a real item moves. `tcw validate` rightly never contacts the tracker. `tracker list` proves the query and credentials work, and `tracker show` reports whether a ticket offers the claim transition. Nothing checks the `statuses` mapping against the project's actual workflow.
>
> So the problems show up in the worst place: after `submit`, `complete` or a discard has already moved the item and committed. The command exits 1, `tracker.yaml` gains a `conflicting` record, and the ticket has to be repaired by hand. In our first real use, the problems we only found by running a throwaway item through the whole lifecycle were:
>
> - **Two transitions into one status.** `Complete` and `Cancel` both led to Done, so `completed: Done` could never sync. That is #40.
> - **A mapped status the workflow cannot reach from where the previous move leaves the ticket.** Nothing tells you whether each step (active → review → back to active → completed or discarded) has exactly one transition.
> - **Moves that depend on assignment.** Nothing warns that, with a query selecting unassigned tickets, discarding unstarted work will be refused.
>
> Environment: tcw 2.2.0, macOS 26.6.2, pip into a pyenv-managed Python 3.14, Jira Cloud company-managed project.
>
> ### Description
>
> Add a read-only tracker check that walks the configured mapping over the workflow and reports, before any real item depends on it:
>
> ```text
> tcw work tracker check [<ticket>]
> ```
>
> For each move TCW can send (claim, submit, rework, complete, discard with each resolution), it reports the status the ticket starts in, the target status from `statuses`, and the transitions that lead there:
>
> ```text
> claim     To Do        → In Progress   Start                         ok
> submit    In Progress  → In Review     Submit                        ok
> rework    In Review    → In Progress   Rework                        ok
> complete  In Review    → Done          Complete, Cancel              conflicting: more than one transition
> discard   To Do        → Done          Cancel                        ok (needs the ticket assigned to you)
> ```
>
> - **Where the workflow comes from.** Jira Cloud can return the workflow for a project and issue type (`POST /rest/api/3/workflows` with the project's workflow scheme). When the account cannot read workflow definitions, fall back to a sample ticket: read its offered transitions from each status the check can reach, or report what it could not determine.
> - **Issue types.** A project can use a different workflow per issue type, so the check should cover each issue type it finds, or take `--issue-type`.
> - **Exit code** non-zero when any mapped move is conflicting or unreachable, so it can run in a setup script or CI (not in `validate`, which stays offline).
> - **`strict` and `comments`** could be covered too, for example by warning when strict mode is on and a required status is unreachable.
>
> This concerns the **work** axis (tracker configuration).
>
> ### Benefits
>
> - Mapping mistakes are found while configuring, not after a real item has moved and committed.
> - It turns the throwaway-ticket test run we had to do by hand into one command.
> - It gives a clear place to explain Jira-specific requirements, such as one transition per target and assignment, next to the exact workflow that breaks them.

## Triage (2026-09-15)

Decided with the maintainer at triage, in place of the issue's separate command:

- **No `tcw work tracker check` command.** The workflow check becomes a check inside
  `tcw validate`. The maintainer's sketch of the output:

  ```text
  $ tcw validate
  ☑︎ YAML correctness validation
  ☒ tcw:// link resolution (1)
    - docs/capabilities/capabilities/reset-an-override/description.md: tcw:// tcw://C/caps/override-inherited → no capability: caps/override-inherited
  ☑︎ Project reference resolution
  ☒ Jira workflow validation (2)
    - TCW status "backlog" has no available Jira transitions
    - TCW "start" move has ambiguous Jira transition
  ```

  Each check has three results — pass, fail, skip. The ballot characters are not
  required.
- **Network: runs when credentials are set.** The Jira check runs when the tracker's
  credentials are present, and is skipped (not failed) when they are absent or the
  tracker cannot be reached. The maintainer chose this over "offline unless asked" and
  "online by default".
- **This reverses a documented rule.** `docs/guide/work.md` ("`tcw validate` never
  contacts the tracker", with the reason), the comment in `tcw/validate.py` beside
  `tracker_problems()`, and `tests/test_tracker_validate.py` (which fails if a
  connection is attempted) all say otherwise. This repository binds `tcw validate` as
  a `pre` hook on `complete` (`tcw-config.yaml`), so a real workflow problem would
  then block completing items, and `validate` recurses into every descendant project.
  How the hook and those promises change is for the spec.
- **The pass/fail/skip report belongs to `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`**, which was widened to own
  it; this item adds the Jira workflow check as one row of that report.

Related items:

- `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes` — introduces per-check results and graded exit codes that this check reports through.
- `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` — reads the same Jira workflow definition for claim exclusivity, and records the unanswered prerequisite both share: whether a non-admin token can read that endpoint. It may later become another row of this check.
- `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items` — checks the same "does the workflow offer a transition" question at the moment of a move, under strict mode.
- `2026-09-15-let-tracker-sync-name-its-transitions-bring-a-late-linked-ticket-forward-and-stop-reading-ordinary-moves-as-drift` — GitHub #40's named transitions change what "ambiguous" means for this check.
