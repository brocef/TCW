# Plan — Synchronize the work lifecycle outward to the tracker

Implementation happens in `.worktrees/<slug>/` on `work/<slug>`, started after C5
(`2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`)
is merged into `main` (it is, as `7969bbdb`), since this item extends its `WorkItem.tracker`,
`classify_binding`, `_tracker_text` and `TrackerField`. The editable install is
pointed at the worktree for tests and restored before `tcw work complete`.

New tests go in new files so the existing tracker tests stay unedited, except where a
task says otherwise:

- `tests/test_tracker_sync_config.py` — Task 2
- `tests/test_tracker_sync.py` — Tasks 3 to 7
- `tests/test_tracker_surface.py` — Task 8 extends C5's file (its assertions about the
  bound value gain `sync: None`, which is the shape change the spec states)

Every test node builds its tracker block through one helper whose `statuses` argument
has no default, because the mapping is the axis the code branches on (the project's
"a shared fixture may not default an axis" rule).

## Task 1 — Extend the fake tracker

**Files:** `tests/tracker_fake.py`.

- `CATEGORY` gains `In Review` (`indeterminate`), `Won't Do` and `Duplicate` (`done`).
- A `SYNC` workflow: from `To Do` — `Start Progress → In Progress`, `Won't Do`,
  `Duplicate`; from `In Progress` — `Ready for Review → In Review`, `Finish → Done`,
  `Won't Do`, `Duplicate`; from `In Review` — `Back to Progress → In Progress`,
  `Finish → Done`, `Won't Do`, `Duplicate`; `Done`, `Won't Do`, `Duplicate` — none.
  `GLOBAL` gains the three new statuses as keys offering its existing transitions.
- `FakeJira.down: bool` — when true every request raises `TrackerUnavailable` before
  it is recorded as answered.
- `FakeJira.site: str | None` and a module function `install_sites(monkeypatch,
  *fakes)` that routes each request to the fake whose `site` equals
  `client.config.base_url`, raising `AssertionError` for any other. `install` keeps
  its behaviour for a fake with no site.

**Proves:** the whole existing `tests/test_tracker_*.py` passes unedited.

## Task 2 — `work.tracker.statuses`

**Files:** `tcw/store/base.py`, `tests/test_tracker_sync_config.py`.

- `TRACKER_KEYS` gains `statuses`; `TRACKER_STATUS_KEYS = {"active", "review",
  "completed", "discarded"}`; `TRACKER_TRANSITION_KEYS` stays `{"claim"}` and its
  comment is corrected to say where the mappings went.
- `TrackerConfig.statuses: dict` (default empty): `{"active": str, "review": str,
  "completed": str, "discarded": str | {resolution: str}}` with only the keys set.
- `parse_tracker_config` reports: not a mapping; an unknown key; a value that is not
  a non-empty string (or, for `discarded`, not such a string or a mapping of them);
  an unknown resolution under `discarded`; any key set without `active`.
- A small pure helper `target_status(statuses, status, resolution) -> str` returning
  `""` for no mapping.

**Proves:** criterion 21 through `tcw validate` in a node, with `tcw work list` and
`show` still exiting 0; parent inheritance of one `statuses` key tested once.

## Task 3 — The `sync` record in the binding

**Files:** `tcw/store/base.py`, `tcw/tracker/intake.py`, `tcw/work/projection.py`,
`tests/test_tracker_sync.py`.

- `Bound.sync` (compare=False): `None`, a record dict, or `{"problem": reason}`.
  `classify_binding` accepts a record mapping with `state` in `{pending,
  conflicting}`, `move` in `TRANSITION_IDS`, `claim` in `{done, owed}`, and string
  `since`, `reason`, `at`; anything else under `sync` becomes the problem value and
  the binding stays bound.
- `binding_value` includes `sync`; `_TRACKER`'s bound object gains `sync` as a
  closed `oneOf` of null, the record and the problem.
- `tcw/tracker/intake.py`: `with_sync_record(content, record | None) -> str` (sets or
  removes the key, leaving every other key and its order); `unlink_document` drops
  `sync`.

**Proves:** criteria 17 (the classification half), 18 (the JSON half) and 24.

## Task 4 — The site check

**Files:** `tcw/tracker/intake.py`, `tcw/work/cli.py` (import and link pass the
configured base URL), `tests/test_tracker_sync.py`.

- `same_site(ticket_url, base_url) -> bool` with `urllib.parse`: scheme and host
  equal ignoring case, path starting with `base-url`'s path plus `/browse/`; empty
  or unparseable is false.
- `find_binding(..., base_url)` raises `BindingProblem` naming the item and both
  sites when a binding with the same ticket id fails `same_site`.

**Proves:** criterion 15's `import` half with `install_sites`; the existing
`import`/`link` tests pass with the new argument.

**Mutation check:** make `same_site` return true for a matching host with any path
and confirm the colliding-id test goes red.

## Task 5 — Delivery

**Files:** `tcw/tracker/sync.py` (new), `tests/test_tracker_sync.py`.

- `Outcome(state: "current" | "pending" | "conflicting" | "held" | "none", reason,
  claim_owed: bool)`.
- `classify_error(error) -> state`, per spec § 7.
- `expected_statuses(statuses, previous_status, record) -> tuple[str, ...]`: the
  record's `since` and its move's target, or the fallback chain `review → active`.
- `deliver_claim(client, config, bound)` — the site check, `read_ticket`, `claim`,
  then the `statuses.active` check (spec § 3).
- `deliver_move(client, config, bound, *, move, status, resolution, expected)` —
  steps 2–8 of spec § 4. Steps 2–6 are a separate pure function over a `TicketRead`
  so C4 can call them before a mutation.
- `deliver(store, slug, client, config, *, move, previous_status)` — reads the item
  and its binding, applies the parts hold (another open item in `store.query()` with
  a bound `tracker` of the same ticket id), runs an owed claim first, then the move,
  and writes or removes the record with `with_sync_record` through `write_sidecar`.
  Skips the write when `store.pending_deletion(slug)`.
- Reasons are built by this module and cut to 300 characters.

**Proves:** criteria 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 and 23 as direct calls against
the fake, each asserting the fake's write list.

**Mutation checks:** drop the *expected* check (criterion 9 goes red on `GLOBAL`);
drop the assignment check (criterion 11); remove the parts hold (criterion 14).

## Task 6 — Deliver after local transitions

**Files:** `tcw/work/cli.py`, `tests/test_tracker_sync.py`.

- `_deliver_after(st, bare, verb, move, previous_status) -> int` in `cli.py`: returns
  0 without importing `tcw.tracker` unless `st.get(bare).tracker` is a binding and a
  tracker is configured or has problems; otherwise builds the client, calls
  `deliver`, prints per spec § 9, and returns 1 unless the outcome is current, held
  or none.
- `_start`: after the store move and `post` hooks, before `--worktree` setup; also
  after a `TransitionCommitError`. `_submit`, `_rework`: after `post`, and after a
  `TransitionCommitError`. `_complete`: after `post` and before `_auto_delete`; when
  delivery returns 1 and the item is pending deletion, skip `_auto_delete` and print
  the manual-fix message.
- Previous status is read before the move.

**Proves:** criteria 1, 2, 3, 4, 19, 20, 22 through `tcw.cli.main`, including
criterion 20's fresh-interpreter import probe for each verb.

**Mutation check:** move the `_start` delivery before `st.start` and confirm
criterion 2's "item active and committed" assertion fails when the claim is refused.

## Task 7 — `tcw work tracker sync`

**Files:** `tcw/work/cli.py`, `tests/test_tracker_sync.py`.

- `tracker sync [<slug>] [--all]`, exactly one required; `description`/`epilog` in the
  style of the other `tracker` subcommands (what it changes in the tracker, refusals,
  examples), and `help=` on the positional.
- The owner rule (spec § 8) using the same owner resolution `_start` uses, factored
  into one `_local_owner(st)` helper that `_start` also calls.
- No-record `<slug>`: check only.

**Proves:** criteria 4 (the `sync` half) and 16; `tests/test_tracker_help.py` and
`tests/test_documented_cli_surface.py` pass.

## Task 8 — Show the record

**Files:** `tcw/work/cli.py`, `web/client/src/model/types.ts`,
`web/client/src/ui/shared-components.tsx`, `web/client/src/ui/content-views.test.tsx`,
`tests/test_tracker_surface.py`, `tcw/serve/dist/**`.

- `_tracker_text` adds the row state; `_print_item` prints the `tracker sync:` line.
- `TTrackerBinding` gains `sync`; `TrackerField` appends the state and reason.
- Build the client from a worktree **without** a `node_modules` symlink leaking paths:
  build in the primary checkout after merge if the worktree build changes
  `server.cjs`, and verify with `pnpm check:build` on `main`.

**Proves:** criterion 18.

## Task 9 — Capabilities

**Files:** the item's `capabilities.yaml`; `docs/capabilities/work/…/description.md`
for the five capabilities in the spec's table, and `tcw capabilities set
work/synchronize-external-tracker-work --status Supported`.

**Proves:** criterion 25.

## Documentation Sync

| Entry | Fires | Change |
| ----- | ----- | ------ |
| `README.md` [Public-API] | yes | Tracker section: `start` claims a linked ticket; lifecycle moves follow `statuses`; pending/conflicting and `tracker sync`; the paragraph saying "nothing moves a linked ticket for you" is replaced. |
| `docs/release-notes/upcoming.md` [Public-API] | yes | Plain entry for tickets following items, and `tracker sync`. |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | yes | Added: `statuses`, `tcw/tracker/sync.py`, `tracker sync`, the `sync` record and schema; Changed: `start`/`submit`/`rework`/`complete` deliver for bound items, `find_binding` site refusal, fake tracker. |
| `skills/tcw-work/references/commands.md` [Skill-Driven-Component] | yes | The tracker section: delivery, record, `sync`, owner rule, the site refusal; the row for `tracker sync`. |
| `skills/tcw-configure/references/tracker.md` [Configuration-Key-Change] | yes | The `statuses` block, `active` requirement, per-resolution discards; and its stale opening sentence that says `link` claims. |

## Verification

1. A scratch node with a tracker block pointing at an unreachable address
   (`https://127.0.0.1:9`), a bound item, `start` → exit 1 with the pending message,
   `list` shows `(pending)`, `show` prints the `tracker sync:` line. No live Jira is
   contacted at any point, and no credentials exist in this session.
2. Bare `pytest` on merged `main`, `tcw validate`, `tcw capabilities check`,
   `pnpm check:build`.

## Before `tcw work start` — done while planning

- The spec review asked for this item to be blocked by C5. C5 completed
  (`e4c567d2`) before this plan was committed, so the blocker would be satisfied the
  moment it was written; not added.
- The progress-links child exists:
  `2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket`,
  `--initiative` of the epic, blocked by this item (`f6d13591`).
- The epic's spec records this item's settled design and the split (`18a3e22b`).

## Notes

- Sequential: every task after 1 builds on the one before, and Tasks 5–8 share
  `tests/test_tracker_sync.py` and `cli.py`.
