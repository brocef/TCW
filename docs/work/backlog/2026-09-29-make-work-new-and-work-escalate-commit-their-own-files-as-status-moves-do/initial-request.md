# Make work new and work escalate commit their own files, as status moves do

From GitHub issue [#66](https://github.com/brocef/TCW/issues/66) (filed
2026-09-29 by @brocef), preserved as this item's `intake.md`.

## The request

Status moves (`start`, `submit`, `rework`, `complete`) make their own commit.
The commands that create things do not, and they leave two different states:

- after `tcw work new`, the item's files are **staged but not committed**;
- after `tcw work escalate`, the new inbox entry is **untracked** — not even
  staged.

The `work` skill says TCW commits its own transitions, and agents reasonably
read that as covering creation. The creation then gets folded into the next
commit — usually the request artifact, which the skill says must be committed
on its own. In a store several sessions commit to, a file staged by one session
can be swept into another session's commit.

Asked for: creation commands commit for themselves, as transitions do. Failing
that, every creation command should leave the same state, and print that the
files still need committing.

Workaround in use: commit the item folder by hand right after `new` or
`escalate`, limited to that path.

Seen on tcw 2.6.4.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue; nothing else was offered.
- Other commands that create files — `inbox accept`, `delegate`, `scaffold` —
  are the same question, and the spec should say which it covers.

## References

- `2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git` —
  the same question for `scaffold`.
- `2026-09-29-hold-one-lock-on-the-work-store-for-every-transition-not-only-the-resolving-ones`
  (GitHub #73) — a staged file left by one session is what another session's
  commit sweeps up; that item makes each transition commit only the paths it
  wrote.
