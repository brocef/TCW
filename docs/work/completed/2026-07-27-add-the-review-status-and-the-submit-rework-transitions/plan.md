# Implementation plan

Six ordered tasks. Each is one commit. The order is chosen so the test suite is
green at every commit boundary — no task leaves the tree broken for the next.

Task 1 is deliberately first and alone: deleting `phase` touches the same
dataclass and the same three creation sites that task 2 edits, and doing it
first means task 2's diff is purely additive.

## Task 1 — delete `phase`

Pure removal, no behavior change, no new status yet. Landing it first keeps it
out of every later diff.

- `tcw/store/base.py:531` — drop the field from `WorkItem`.
- `tcw/store/fs.py:1785` — drop `phase=state.get("phase", "")` from the loader.
- `tcw/store/fs.py:2124`, `:2169`, `:2289` — drop `"phase": ""` from the three
  `state.yaml` creation sites.
- `tcw/work/cli.py:97-98` — drop the `show` line.
- `tcw/work/recursion.py:127,134` — drop the column from the header, the
  separator row, and the row template. The separator has one fewer `---`.

**Test:** `tests/test_work.py` gains a case that writes a stale `phase:` into a
`state.yaml` by hand, loads the item, asserts no error and no attribute, writes
an unrelated field, and renders the item through `show`. This is the no-op
migration proof the spec requires; it is the only new test in this task.

**Corrected during implementation:** the plan first asserted the key would be
*dropped* on the next write. It is not. `set_field` (`fs.py:2173`) is a
read-modify-write over the raw mapping, so unknown keys survive. The migration
is that `phase` stops being read and stops being displayed, not that it is
erased — and no rewrite pass is being added to erase it, because churning every
item's `state.yaml` to delete an already-ignored value is not worth it. The
spec's design section and criterion 9 were corrected to match.

Existing rollup assertions in `tests/test_recursion.py` that match the table
header will need updating — check before assuming the task is test-free.

**Green when:** full suite passes and `grep -rn '\bphase\b' tcw/ web/client/src/`
returns only unrelated hits (`fs.py` and `base.py` module docstrings refer to
the historical build phases; `taxonomy/cli.py:1` and `work/cli.py:1` likewise).
Those prose mentions stay — the criterion is about the work model, not the word.

## Task 2 — the `review` status and the four edges

Model only. No CLI surface yet, so nothing user-visible changes.

- `tcw/store/base.py:434` — `WORK_STATUSES` gains `review` after `active`.
- `tcw/store/base.py:446` — `LEGAL_TRANSITIONS` gains the four edges, each with
  the same trailing comment style as the existing four.
- `tcw/store/base.py` — `WorkStore.submit()` and `.rework()` beside `start()`.
  `rework()` reads `self.artifacts(slug)` and raises `ValueError` naming
  `refined-outcome.md` if it is present.
- `tcw/store/fs.py:2183` — `_effect_transition` creates the destination folder
  with `mkdir(parents=True, exist_ok=True)` before the move.
- `tcw/store/base.py:502` — `WORK_ARTIFACTS` gains `rework` and `post-mortem`.

**Ordering within `WORK_ARTIFACTS` matters more than it looks.** The tuple is
iterated to build the `list` stage letters (`work/cli.py:292-301`) and the
artifact registry in `get_detail`. Append the two new names at the end rather
than inserting them in lifecycle position, so no existing item's stage display
shifts. Confirm against the stage-letter derivation before committing.

**Tests:** a new `tests/test_work_review.py` covering the transition matrix —
`active → review → active → review → completed`, `review → discarded`,
`submit` from `backlog` raising `IllegalTransition`, `rework` refusing while
`refined-outcome.md` exists and succeeding once removed, and a `review` item
still blocking a dependent's `start` and still holding its epic open.

Lazy folder creation gets its own case: build a `tmp_path` node, delete
`docs/work/review/` outright, and assert a `submit` recreates it. Delete
`docs/work/completed/` in the same test and assert a `complete` does too — the
fix is status-agnostic and the test should say so.

**Two things that should be free, and are therefore tested rather than
inspected.** Both were raised in review as possible gaps; both are derived from
`WORK_STATUSES` in the code as it stands, which is exactly why a test is worth
more than reading the source and concluding "fine":

- **Discovery.** `_item_dirs` (`fs.py:1552`) globs every status folder, and
  status-path locators (`fs.py:212`) and the qualifier guard (`fs.py:246`) both
  test membership in `WORK_STATUSES`. Assert that an item in `review` appears in
  `tcw work list`, resolves by bare slug, and resolves by the `review/<slug>`
  status-path locator.
- **The reserved project id.** `RESERVED_PROJECT_IDS` derives from
  `WORK_STATUSES` (`store/project.py:16`) so `review` is rejected automatically
  the moment the tuple grows — but an automatic rejection is not necessarily a
  *legible* one. Assert that `tcw init --id review` fails, and that the message
  names the collision rather than reporting a generic invalid id. Fix the
  message if it does not.

## Task 3 — `tcw work submit` and `tcw work rework`

- Two `_submit` / `_rework` handlers in `tcw/work/cli.py`, following `_start`'s
  shape: `_resolve`, call, catch `_ERRORS`, print, return 0/1.
- Two subparsers beside `start`: `submit` ("active → review") and `rework`
  ("review → active").
- `submit` prints a next-step hint pointing at `complete`, matching
  `_complete_hint`'s existing style. `rework` prints one pointing back at
  `submit`.
- `_complete` emits the verify-skipped warning to stderr when the item's status
  is `active` at the time of the call. Read the status **before** the
  transition — afterwards it is `completed` and the branch cannot be taken.

**Tests:** extend `tests/test_work_review.py` with CLI-level cases for both new
commands, the warning appearing on the `active` route, and the warning being
absent on the `review` route.

## Task 4 — the `pr` field

- `pr: str = ""` on `WorkItem` after `branch`.
- Persisted alongside `worktree`/`branch` — follow exactly how those two are
  written and read, since they are the closest existing precedent.
- `tcw work edit --pr <url>`; `show` prints it when non-empty.

Small and independent of tasks 1–3; kept separate so that if it is dropped, the
drop is one revert.

**Reviewer note, carried forward deliberately:** two independent reviewers
flagged this field as speculative because nothing in this child consumes it.
That is accurate. It is kept because the epic plan assigns it here and because
child 2's `complete --already-integrated` is its consumer one child later —
adding it now costs one field and avoids a second `state.yaml` shape change.
If child 2's design moves away from it, this task is the one to cut.

## Task 5 — the TypeScript mirror and the parity test

- `web/client/src/model/types.ts:5` — add `review` to `WORK_STATUSES`.
- `web/client/src/model/tree.ts:9` — add `["review", 1]` to `WORK_STATUS_ORDER`
  and renumber `backlog`/`completed`/`discarded` to 2/3/4. The map is
  display-precedence, and a reviewable item belongs directly under active work.
- `tests/test_status_parity.py` — read `types.ts`, regex out the array literal,
  assert set equality with `WORK_STATUSES`.

`tests/test_status_parity.py` is a **committed test and runs in the normal
`pytest` sweep** — that is the whole deliverable. What is *not* committed is the
demonstration that it works: during verification, remove `review` from
`types.ts`, watch the test go red, restore it, and do the same on the Python
side. A guard nobody has ever seen fail is not yet known to be a guard.

`web/client/src/model/tree.test.ts:17` already iterates `WORK_STATUSES` to
assert the sorter covers every status, so the TS half becomes self-guarding once
`types.ts` is updated. Run the web suite — this task is the only one that can
break it.

## Task 6 — documentation sync

Evaluated against the `## Documentation Sync` table in `AGENTS.md`. Three of the
four entries fire.

| Entry | Fires | Why |
|---|---|---|
| `README.md` | yes | New status and two new public commands. |
| `docs/release-notes/upcoming.md` | yes | New review step; **and the reserved-project-id break.** |
| `docs/changelogs/upcoming.md` | yes | Code change. Added/Changed/Removed, with the hash range. |
| `skills/tcw-work/SKILL.md` | yes | The component's model and lifecycle both change. |

The `SKILL.md` update is **minimal and interim**: enough that the shipped skill
is not lying about the state machine — the `review` status, `submit`, `rework`,
and the rework-blocks-on-`refined-outcome.md` rule. Child 4 restructures the
skill wholesale, so anything beyond accuracy is wasted work that child 4 will
delete. Same for `references/task-lifecycle.md` and `epic-lifecycle.md`, which
child 4 deletes outright: correct them only where they now state something
false.

**The release note is the one that matters.** `review` becoming a reserved
project id is the only breaking change in this child, and it fails at upgrade
time for anyone who used that id. It needs plain language and a stated remedy,
not a changelog line.

## Verification

Beyond the suite:

1. `tcw validate` on this repo.
2. Drive a scratch item through `start → submit → rework → submit → complete`
   in a `tmp_path` node and confirm the folders exist where expected.
3. Break the parity test by hand in each direction; confirm red both ways.
4. Confirm `tcw work list` and `tcw work show` render a `review` item without
   the removed `phase` line.
5. Run the web client's test suite.

## Rollback

Tasks are independently revertible in reverse order. The only task that changes
data on disk is 1 (drops a `state.yaml` key on next write) and it is a no-op by
construction — a revert would simply start writing `phase: ""` again, which
every reader tolerates.
