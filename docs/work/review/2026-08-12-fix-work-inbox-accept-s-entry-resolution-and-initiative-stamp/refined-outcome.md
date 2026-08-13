# Refined outcome — Fix work inbox accept's entry resolution and initiative stamp

**Decision: accepted.** Approved by the user on 2026-08-13, who asked for the
review-stage bug items to be checked as merged and closed.

## Evidence at acceptance

Implemented directly on `main`; no branch or worktree remains, so "merged" is
simply that `aabd62e`, `3c1aeac`, `f25e048`, and `599f942` are ancestors of `HEAD`
(`5645635`).

Re-verified on `main` at acceptance rather than trusting `outcome.md`:

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 1294 passed |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate` | `validate OK` |
| `git status --short` | clean |

The one criterion no test can settle — whether `delegate --help` reads as
"canonical project id" to someone who has not read the source — was re-checked
against rendered output, not the diff:

```
positional arguments:
  child                 child node's canonical project id (`tcw work nodes`
                        lists them)
```

## The corrected criterion stands

The spec's original ambiguity criterion contradicted its own Design; the
correction (exact reference wins; ambiguity reserved for an input that is neither
an exact ref nor `<input>.md`) was committed to `spec.md` in `83165b8` before any
implementation, and `test_inbox_exact_reference_wins_over_a_colliding_title` pins
the case the old wording had backwards. Accepted as resolved — the alternative
would make a folder unaddressable by its own name the moment a file landed beside
it.

## Capability reconciliation

No `capabilities.yaml`, as `spec.md` said: this corrects existing work-inbox and
delegation behavior rather than adding a user capability. `tcw capabilities drift`
confirms nothing went stale.

## Closeout

- **Route: direct to `main`.** No branch to merge.
- Documentation current at acceptance: `README.md` (inbox example and cross-node
  section), both `upcoming.md` files, and
  `skills/tcw-work/references/commands.md`. `SKILL.md` deliberately untouched —
  its body sits at the 60-line router budget and both details are conditional.
- Released in **v0.21.1**, folded in by `5645635`.

## Follow-ups

- **Carried, not filed:** the `FsWorkStore._frontmatter` extraction now serves
  `_plan_manifest` and `_inbox_initiative`. A third caller would be the point to
  ask whether it belongs somewhere more visible than the adapter's private
  surface; two is the threshold this repo already set for extracting, so nothing
  is owed today.
