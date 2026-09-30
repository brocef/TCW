# Let a started item still pass its planning gates, or stop start from letting it past them

From GitHub issue [#71](https://github.com/brocef/TCW/issues/71) (filed
2026-09-29 by @brocef) — point 1 and the follow-up comment — preserved as this
item's `intake.md`.

## The request

An item started before its planning documents were written cannot pass the
`request`, `spec` or `plan` gates afterwards:

```
$ tcw work stage gate request <slug>
tcw work stage gate: 'request' is not legal for an item in 'active'; it runs in backlog
```

This happens when work is discovered mid-task and made into an item after the
fact. The lifecycle still expects those documents, but no gate will run for
them, so an agent reads the instructions with `stage prompt` and writes them
without the gate — skipping whatever the project bound to it.

The follow-up comment names how items get there: `tcw work start` on an item
with only `initial-request.md` proceeds with a warning ("has no spec.md or
plan.md; they can still be written while the item is active"), although the
plan stage's own instructions say `plan.md` is committed before `start`.

Asked for, as alternatives:

- let the planning gates run on an active item whose planning artifacts are
  missing; or
- make the refusal say what to do ("write it with `stage prompt`; the gate's
  checks will not run", or "move it back to backlog first"); or
- make `start` refuse, or require `--force`, when the planning artifacts the
  lifecycle binds are missing.

Seen on tcw 2.6.4 (a proposit-core session).

## Out of scope

- #71 point 2 (an artifact name given where a stage name is expected): tracked
  in `2026-09-29-suggest-what-was-meant-when-a-subcommand-or-stage-name-is-wrong`.

## Notes

- Written autonomously (an `/autonomous-work` run); there was no requester to
  ask. Reference material: the issue and its comment; nothing else was offered.
