# Hold one lock on the work store for every transition, not only the resolving ones

From GitHub issue [#73](https://github.com/brocef/TCW/issues/73) (filed
2026-09-29 by @brocef), preserved as this item's `intake.md`.

## The request

Status moves commit into the work store's repository. When several agent
sessions share one store, those commits can collide with each other and with
the sessions' own commits: a `.git/index.lock` failure, or one session's staged
files swept into another's commit. In a real run of three concurrent sessions
(tcw 2.6.4) only an external `mkdir`-based lock script wrapped around every
state-changing command prevented this — which each new agent had to be told
about.

Asked for:

- tcw takes its own short lock on the work store for the length of a
  transition, with a bounded wait and a clear message on timeout;
- it commits only the paths it wrote, not whatever the index holds.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue.
- Triage checked the code at 2.6.5 and narrowed the ask: transition commits are
  already limited to the paths they touched, and a lock (`_graveyard_lock`, an
  `flock` keyed to the store) exists but is taken only when the target status
  is a resolved one. `start`, `submit` and `rework` run unlocked, and nothing
  waits on another session's `.git/index.lock`.
- `work new` and `escalate` not committing at all is
  `2026-09-29-make-work-new-and-work-escalate-commit-their-own-files-as-status-moves-do`
  (#66); if that item lands first, its commits should take the same lock.

## References

- `2026-09-29-make-work-new-and-work-escalate-commit-their-own-files-as-status-moves-do`
  — the creation commands' commits, which should share this lock.
