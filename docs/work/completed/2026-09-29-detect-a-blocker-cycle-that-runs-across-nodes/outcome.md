# Outcome — Detect a blocker cycle that runs across nodes

## What shipped, task by task

1. **Tests** (`62f1e40d`, `d69d82ad`, `7c60cca3`):
   `tests/test_cross_node_blocker_cycles.py`, 17 tests over criteria 1-10 plus
   the review's additions (a walk crossing into a store with an interrupted
   claim; a local claim not failing `tcw work new`; a hand-edited plain-string
   blocker not crashing `--blocks`).
2. **The walk in the model** (`fa73710b`): `WorkStore._store_key()`,
   `WorkStore._blocker_target(entry)`, `_reaches` over (store, slug) pairs,
   `_check_new_blocker` and the `--blocks` half of `check_blocker_edits`
   through the hook.
3. **The filesystem adapter** (`c3c0e7e5`): `_qualified_shape`,
   `_qualified_target` (shared with `external_blocker_state`), the
   `_blocker_target` override for `<project-id>/<slug>`, `_store_key` by
   folder identity, and `create_work` checking new blockers once the slug is
   known.
4. **Docs** (`95d39c74`): changelog and release-note entries, the blocker
   comment in `docs/guide/work.md`, `work/manage-blocking-relations`, and
   `capabilities.yaml`. README, skills, configure references and the Jira
   guide state no cycle rule (checked by grep) and are unchanged.

Every guard was mutation-checked: removing the cross-node follow (7 tests
red), keying stores by spelling (1), the `create_work` check (2), the bare
external follow (1), the swallowing of unreadable items (3), the type guard
(1), and the `--blocks` pre-check (1, after the test was strengthened to pair
`--blocks` with a title change).

## Test result

Bare `pytest` at `1196488d`: **5001 passed, 3 skipped**, 22 minutes.

## What the plan or spec got wrong

- **The bare-slug rule.** The spec and plan said a bare `external` slug is
  followed only when the item exists. Criterion 6 (a dangling entry naming a
  slug not created yet) contradicts that; the code follows any slug-shaped
  text, and a missing item is a dead end. Spec and plan corrected
  (`1196488d`).
- **Unreadable items.** The spec swallowed read failures only in *other*
  stores. Code review found that made `tcw work new` fail on an unrelated
  local item's interrupted claim, which it never did before; the rule is now
  "not followed" in any store, and the next item decides what to say about it.
- **The web app's field name.** Hands-on, a `PATCH` must send
  `{"fields": {"blockers": [...]}}`; my first attempts used other names and got a
  silent 200. Not a defect, but worth knowing when testing it by hand.
- **Criterion 6 depends on the date.** Its tests build the expected slug from
  `date.today()` while the CLI reads the date itself; a run crossing midnight
  fails. The CLI takes no date, so this stays.

## Verification beyond the suite

In a scratch graph (`r` → `pa`, `pb`): `tcw work edit` closing the loop from
`pb` printed `pa/2026-09-29-build-the-thing → 2026-09-29-ship-the-other-thing
would create a blocking cycle`, exit 1, and `pb`'s item gained no blocker.
Through `tcw serve`, the same `PATCH` answered 422 with that message; a
non-looping blocker through the same route answered 200 and was written.

## Autonomous decisions

- **Spec review** — advisors: Opus (AGREE WITH CHANGES); Codex unavailable
  (usage limit until 2026-10-03). Opus found `create_work` can close a cycle,
  the need to follow what settling follows, folder identity instead of path
  text, foreign read failures, sharper criteria. **Taken: all**, bar the
  two-nodes-one-folder case, recorded as a known limit (only differs when two
  nodes' graphs differ, which nothing sets up).
- **Code review** (adversarial-code-reviewer): no blocking findings.
  Taken: unreadable items not followed in any store; a type guard for
  hand-edited entries; a test reaching the cross-store error branch; the
  spec/plan wording. **Rejected:** removing an extra registry open on one
  read path (results unchanged; removing it would split the shared helper that
  keeps settling and the cycle walk in agreement). **Noted, not changed:** the
  date dependency above.
- **Verify decision**: mine — green suite, all criteria covered, hands-on
  checks match; submitted.
