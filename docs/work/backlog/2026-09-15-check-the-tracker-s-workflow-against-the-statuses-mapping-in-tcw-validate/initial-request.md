# Check the tracker's workflow against the statuses mapping in tcw validate

## What is wanted

A `work.tracker` block can be well-formed and still unable to move tickets, and today
nobody finds out until a real item moves — after `submit`, `complete` or a discard
has already moved and committed the item, leaving a `conflicting` record and a ticket
to repair by hand. In the reporter's first real use, the problems only surfaced by
running a throwaway item through the whole lifecycle: two transitions into one status
(GitHub #40), a mapped status the workflow cannot reach from where the previous move
leaves the ticket, and moves that need the ticket assigned (GitHub #41).

Wanted (GitHub #44, reshaped at triage): `tcw validate` checks, for each move TCW can
send — claim, submit, rework, complete, and discard with each resolution — the status
the ticket starts in, the status the mapping targets, and the transitions that lead
there, and reports any move with none, with more than one, or that depends on
assignment. It covers each issue type the project uses.

## Decided with the maintainer at triage

- **Inside `tcw validate`, not a new `tcw work tracker check` command.** It is one
  named check among `validate`'s others. The maintainer's sketch:

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

  Each check reports pass, fail or skip; the characters are not required. The report
  itself belongs to
  `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`;
  this item adds the Jira workflow row.
- **It contacts the tracker when credentials are set**, and is **skipped, not failed,**
  when they are absent or the tracker cannot be reached. The maintainer chose this over
  "offline unless a flag asks" and "online by default".

## Constraints

- **This reverses a documented rule, and the request knows it.** `docs/guide/work.md`
  says "`tcw validate` never contacts the tracker. That is deliberate and
  load-bearing", `tcw/validate.py` says the same beside `tracker_problems()`, and
  `tests/test_tracker_validate.py` fails if a connection is attempted. The reason
  given: this repository binds `tcw validate` as a `pre` hook on `complete`, so a
  network call would make finishing an item depend on the tracker, the shell's
  credentials and the token — and `validate` recurses into every descendant project.
  With the chosen behaviour, an unreachable tracker no longer blocks `complete`, but a
  real workflow problem would. The spec must settle what the hook, the guide, the code
  comment and the test become.
- The check only reads; it never moves or edits a ticket.

## Notes

- Reference material: asked; none provided.
- GitHub #44 stays open until the change ships.

## References

- `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes` —
  owns the pass/fail/skip report and graded exit codes this check reports through.
- `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition` —
  reads the same Jira workflow definition, and holds the prerequisite both share: can a
  non-admin token read it at all.
- `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items` —
  the same question asked at the moment of a move.
- `2026-09-15-let-tracker-sync-name-its-transitions-bring-a-late-linked-ticket-forward-and-stop-reading-ordinary-moves-as-drift` —
  named transitions (#40) change what "ambiguous" means for this check.
