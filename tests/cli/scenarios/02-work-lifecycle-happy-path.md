# 02 — The work lifecycle, happy path

One item walked from creation to completion through every transition, with the
artifacts and commits that go with it.

## Functionality covered

- `tcw work new` → `start` → `submit` → `complete`
- `tcw work list` (the board), `tcw work show`, `tcw work show --json`
- The status folders: `backlog/ active/ review/ completed/`
- TCW's own transition commits

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `SLUG=$(tcw work new "Add a widget")` — the slug and **nothing else** reaches stdout. The captured value is usable directly as the next command's argument. |
| 2 | The slug matches `^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$` and its folder exists under `docs/work/backlog/`. |
| 3 | The new item's folder contains `state.yaml`; `tcw work show $SLUG` exits 0 and reports status `backlog`. |
| 4 | `tcw work list` includes the slug; the board line carries status and title. |
| 5 | `tcw work start $SLUG` moves the folder `backlog/ → active/` and exits 0. |
| 6 | `tcw work submit $SLUG` moves `active/ → review/`. |
| 7 | `tcw work complete $SLUG --resolution done --confirm` moves `review/ → completed/`. |
| 8 | After each transition, `git status --porcelain` in the node is **clean** — TCW commits its own status moves. |
| 9 | The commit count increases by exactly one per transition, and each message names the slug and the destination status. |
| 10 | `tcw work list` (no flags) **omits** the completed item; `tcw work list --all` and `tcw work list --status completed` include it. |
| 11 | `tcw work show --json $SLUG` emits parseable JSON carrying a schema version, the slug, the status, and the artifact list. Parsed with `python -m json.tool` or `jq`, not grepped. |
| 12 | Artifacts written into the item folder (`initial-request.md`, `spec.md`, …) appear in both `show` and `show --json` as present. |
| 13 | A **whitespace-only** artifact reports `present: false` — the lifecycle presence rule. (Regression: the two presence rules disagreeing is a fixed defect.) |
| 14 | `tcw work new --priority 5 --effort high --complexity M --tag bug` records all four; `--effort H` and `--effort high` produce the same stored value. |

## Refusals asserted

- `tcw work show no-such-slug` → non-zero, nothing on stdout
- `tcw work complete $SLUG --resolution done` **without** `--confirm` → non-zero,
  item unmoved
- `tcw work new` with an empty title → non-zero, nothing created

## Explicitly not covered here

Stage prompts and hooks (scenario 04), worktree mode (scenario 09).

## Notes for the implementer

Assertion 1 is the reason this whole file exists. `SLUG=$(tcw work new …)` is the
idiom every downstream script and agent uses; anything that leaks into stdout
breaks it silently, and an in-process test that inspects `capsys` will not notice
that it was on the wrong stream.

Assertion 8 also guards a subtler thing: TCW committing its transitions means a
scenario cannot leave the temp repo dirty between steps, so a dirty tree at the
end is itself a finding.
