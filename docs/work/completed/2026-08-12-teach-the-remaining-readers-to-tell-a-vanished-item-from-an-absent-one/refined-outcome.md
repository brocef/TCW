# Refined outcome — Teach the remaining readers to tell a vanished item from an absent one

**Decision: accepted.** Approved by the user on 2026-08-13, who asked for the
review-stage bug items to be checked as merged and closed.

## Evidence at acceptance

Implemented directly on `main`; `d6aa7a5`, `af9d645`, `258dac3`, `b8d8404`, and
`d2be73b` are all ancestors of `HEAD` (`5645635`), and no branch or worktree
remains.

Re-verified on `main` at acceptance:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 1294 passed |
| `tcw taxonomy check` / `capabilities check` / `drift` | all OK, no drift |
| `tcw validate` | `validate OK` |
| `git status --short` | clean |

## What the item found beyond its own spec

The spec framed the defect entirely around `.claiming/`, but `get` has a second,
unrelated find-then-read window that an ordinary `git mv` transition can land in
— no claim evidence for `get` to key on. Found because
`test_get_detail_survives_a_move_between_find_and_read` still failed after Task 3
was implemented exactly as planned. Fixed inside `_get_now` with one re-probe.

Accepted as the right resolution: the re-probe sits at the only level where the
stale path is known, and the spec's design section was simply narrower than the
defect it named. The three call sites that deliberately keep `_get_now`
(`_lost_the_claim`, `start`'s take-over probe, `_effect_transition`'s lost-race
message) are each justified in `outcome.md`, and the full classification of every
`self.get(` and `_find` call site that Step 3 and Task 4 required was carried out
— Task 4 correctly produced no commit, because no sibling was vulnerable.

## Capability reconciliation

No `capabilities.yaml`, as `spec.md` said: this restores concurrency safety the
existing lifecycle already promised. `tcw capabilities drift` clean.

## Closeout

- **Route: direct to `main`.** No branch to merge.
- Documentation current at acceptance: both `upcoming.md` files and the
  concurrency description in the skill references (`d2be73b`).
- Released in **v0.21.1**, folded in by `5645635`.

## Follow-ups

- **Carried, not filed:** the bounded retry (5 snapshots, 500 ms claim window) is
  a timing constant, not a proof. It is asserted from both sides — misses never
  sleep, abandoned claims consume exactly one window — but a slower store would
  need the numbers revisited rather than the design.
- `_Moved` stays private to the filesystem adapter and never crosses `WorkStore`;
  "the folder moved" has no abstract analog, so it must not leak into the store
  interface if this area is touched again.
