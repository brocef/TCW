# Outcome — wontfix

Closed on 2026-07-23 (backlog audit) as speculative work with no demand signal.

## Why

The item asks for additional per-capability sidecars (`events.md`, `metrics.md`)
and was itself explicitly conditional: "pull in only when a real project needs
them." Its blocker recorded the same condition as an external wait —
"a real project that needs `events.md` or `metrics.md` sidecars" — with no owner
and no follow-up trigger. Five weeks on, no project has asked, and nothing is
watching for the signal that would unblock it.

A backlog entry that nobody can act on and nobody is monitoring is noise on the
board. The idea is not lost: `docs/plan/phase-6-beyond.md` still records it
(with the same "wait for a real project to pull them" framing), which is the
right home for a deferred maybe.

## Reopening

If a project does need one of these sidecars, file a fresh item driven by that
project's concrete requirement — it will be better specified than this
placeholder was.

## Resolution

`wontfix` — deferred indefinitely, tracked in `docs/plan/phase-6-beyond.md`.
