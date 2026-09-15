# Plan — Refuse local work that no claimed tracker ticket authorizes

Implementation in `.worktrees/<slug>/` on `work/<slug>`, with the editable install
pointed at the worktree for tests and restored before `tcw work complete`. New tests
go in `tests/test_tracker_strict.py`, reusing `tests/test_tracker_sync.py`'s helpers
by import; its node helper gains a `strict` argument with no default in a thin
wrapper inside the new file, so `tests/test_tracker_sync.py` stays unedited
(criterion 19).

## Task 1 — `strict` in the configuration

**Files:** `tcw/store/base.py`, `tcw/store/fs.py`, `tests/test_tracker_validate.py`,
`tests/test_tracker_strict.py`.

- `TRACKER_KEYS` gains `strict`; `TrackerConfig.strict: bool = False`;
  `parse_tracker_config` reports a non-boolean `strict`, and with `strict: true`
  reports missing `statuses.active`, `statuses.completed`, and a `discarded` that is
  neither a string nor a mapping naming all three discard resolutions.
- `WorkStore.tracker_strict() -> bool`, concrete, `False`. `FsWorkStore` answers it
  from `_resolved_tracker`'s merged raw block: parsed `strict`, or — when the block has
  problems and is a mapping — its `strict` present and not `False`.
- `tests/test_tracker_validate.py::test_strict_is_reported_as_unknown` becomes
  `test_a_boolean_strict_is_accepted` (the key is no longer unknown; the plan edits
  this one test on purpose).

**Proves:** criteria 1 and 2 (the store half).

## Task 2 — `authorize` and the exclusivity check

**Files:** `tcw/tracker/sync.py`, `tests/test_tracker_strict.py`.

- `authorize(store, slug, client, config, *, change, target) -> str | None`, steps 1–5
  of the spec's § 2, reusing `same_site`, `read_ticket`, `expected_statuses` (for the
  status fallback) and `_normalize`; assignment checked before any status comparison.
- `claim_refusal(client, config, ticket_id, outcome) -> str | None`: `None` when the
  claim outcome is in `statuses.active` and `assess(..., landing_status=active)` over a
  fresh transition read is not `NOT_EXCLUSIVE`; otherwise the refusal sentence.

**Proves:** criteria 7, 8, 9, 10, 11 through direct calls.

## Task 3 — Command gates

**Files:** `tcw/work/cli.py`, `tests/test_tracker_strict.py`.

- `_strict_refusal(st, bare, verb, change) -> str | None` in `cli.py`: returns `None`
  without importing `tcw.tracker` unless `st.tracker_strict()`; skips epics; handles
  unbound items, a strict block with problems, and calls `authorize`.
- `_new` and `_inbox_accept`: refuse when strict (except `--epic`).
- `_start`: when strict and bound, the local checks (status, blockers unless
  `--force`, owner), then claim with `claim()`, then `claim_refusal`, then `st.start`;
  the "left claimed" message when `st.start` refuses. C3's delivery after the move
  then finds the ticket claimed and records nothing.
- `_submit`, `_rework`: `_strict_refusal` after the `pre` hook.
- `_complete`: for `done`, `_strict_refusal` before the merge-back.
- `_drop`: refuse when strict and the item has a `tracker.yaml`.
- `_tracker_import` and `deliver`'s claim retry: when strict, `claim_refusal` after a
  successful claim (import creates nothing; `deliver` records conflicting).

**Proves:** criteria 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 20.

**Mutation checks:** remove the assignment step (criterion 7 goes green-to-red);
gate `complete` after the merge (criterion 14); drop the landing-status check (the
`1e` half of criterion 15).

## Task 4 — `tcw serve`

**Files:** `tcw/serve/__init__.py`, `tests/test_tracker_strict.py`.

- One helper, `_strict_refuses(work, action, body) -> str | None`, called by the
  create, start, complete (`done` only) and drop routes and by the sidecar PUT for
  `tracker.yaml`; 409 with the message.

**Proves:** criterion 18.

## Task 5 — Capabilities

**Files:** item `capabilities.yaml`; the six descriptions in the spec's table;
`tcw capabilities set work/require-tracker-backed-work --status Supported`.

**Proves:** criterion 21.

## Documentation Sync

| Entry | Fires | Change |
| ----- | ----- | ------ |
| `README.md` | yes | Strict mode: what it refuses, what it allows, the tracker dependency, how to turn it off. |
| `docs/release-notes/upcoming.md` | yes | Plain entry. |
| `docs/changelogs/upcoming.md` | yes | `strict`, `tracker_strict`, `authorize`, `claim_refusal`, gates, serve. |
| `skills/tcw-work/references/commands.md` | yes | A strict-mode block in the tracker section. |
| `skills/tcw-configure/references/tracker.md` | yes | The `strict` key and what it requires. |

## Verification

1. The scratch node from C3's verification, with `strict: true` and an unreachable
   `base-url`: `tcw work new` refuses; `start` of a bound item refuses with "was not
   started" and the tracker message; the item stays in backlog.
2. Bare `pytest` on merged `main`; `tcw validate`; `tcw capabilities check`.

## Before `tcw work start` — done while planning

- The workflow-definition read is parked as a backlog item (not a child).
- A follow-up inbox note for decomposition under strict mode (spec Risk 6).
- The epic's spec amended per the spec's § 8.
