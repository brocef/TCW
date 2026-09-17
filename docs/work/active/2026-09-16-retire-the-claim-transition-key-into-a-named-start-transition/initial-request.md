# Retire the claim transition key into a named start transition

Child C3 of the epic
`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`.

`work.tracker.transitions.claim` is the odd one out in its own block. Pull
request #45 added `transitions.submit`, `.rework`, `.complete` and `.discard`:
each one names the tracker transition a lifecycle move should apply, each is
optional, and each is read the same way. `claim` predates them, is required, is
read through a field of its own on the parsed configuration, and is documented
as the transition that "starts a ticket" — which is what a `start` key would be
called if the block had one. The block deliberately has no `start` key today,
and the comment in the code that says so points at `claim` as the reason.

The epic removes the reason. Once claiming a ticket stops applying a workflow
transition, the key is not the claim's any more: it is the `start` move's, and
it should be spelled and read like its four siblings.

What is asked for:

- `work.tracker.transitions.start` names the transition the `start` move
  applies, alongside `submit`, `rework`, `complete` and `discard`.
- `work.tracker.transitions.claim` is no longer accepted.
- A configuration file still carrying the old key is reported by `tcw validate`
  with the replacement named, rather than with a bare "unknown key" — every
  tracker-backed project in existence carries the old key today, because it is
  required, so every one of them has to be migrated.
- The documentation, the skills and this repository's own `tcw-config.yaml`
  follow the rename.

## Constraints

- **New code has to cope with configuration files written for the old code.**
  We are not planning around old copies of `tcw` reading new files — assume
  everyone runs the new version — but a `tcw-config.yaml` on disk that still
  says `transitions: {claim: ...}` must either keep working or be told exactly
  what to change. Acceptance criterion 10 of the epic settles which: it is
  reported, with the replacement named.
- **Another item is being implemented at the same time** in a second worktree:
  `2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item` (C2 of
  the same epic). It edits `tcw/tracker/sync.py`, `tcw/store/base.py` around
  `SYNC_FIELDS`, `tcw/work/projection.py` and `tcw/work/cli.py`. Edits here stay
  narrow and local so the two merge cleanly.

## Out of scope

- Making `start` optional, or changing what a start does when no transition is
  named. The claim still applies the transition on every start until C4 lands;
  until then a start needs a name, so `transitions.start` stays required exactly
  as `transitions.claim` was. C4 is what makes it optional.
- Everything the epic lists under its own non-goals, in particular the removal
  of the `claim: owed | done` sync record (C2's) and the rewrite of the
  lifecycle moves (C4's).

## Notes

- There is no separate requester to interview: the epic's spec is the request,
  and the sections that bind this item are "C3 — `transitions.claim` retires
  into `transitions.start`", acceptance criterion 10, and risk 4. Reference
  material was not asked for beyond that, because the epic already names it.

## References

- `docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/spec.md`
  — the authoritative scope for this item; section "C3", criterion 10, risk 4.
- `tcw/store/base.py:1127` — `TRACKER_TRANSITION_KEYS` and the comment that says
  `start` is absent because `transitions.claim` names it; the line the rename
  turns around.
- `docs/guide/jira.md:566` — the same claim stated to users: "There is no
  `start` key: `transitions.claim` already names that one."
- `tcw/work/cli.py:1515` — `_stage_removed_form`, this project's existing
  pattern for retiring a spelling: report the replacement, refuse to act as an
  alias.
