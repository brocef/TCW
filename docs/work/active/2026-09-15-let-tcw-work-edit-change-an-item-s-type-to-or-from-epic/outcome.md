# Outcome: Let tcw work edit change an item's type to or from epic

## What shipped

1. **Store** — `bb7e4cf6`. `WorkStore.update_work` gains `type`; a concrete
   `WorkStore.check_type_change(item, new_type)` refuses a value outside
   `WORK_TYPES`, and `epic` → `""` while `initiative_children()` is non-empty (any
   status) or `incomplete_graph_note()` is non-empty. `FsWorkStore.update_work` calls
   it before any write and omits the `type` key for a plain item, as `create_work`
   does.
2. **CLI** — `4db2b460`. `tcw work edit --type {epic,""}`. `_edit` refuses any
   `--type` under strict tracker mode, then runs the type check before its blocker
   writes, then passes `type` to `update_work`. Tests: `tests/test_edit_type.py`
   (10) and `test_a_type_change_is_refused` in `tests/test_tracker_strict.py`.
3. **Docs** — `72904e77`: README command table, `docs/guide/work.md` epic section,
   `docs/guide/jira.md` strict-mode exception, `skills/work/references/commands.md`,
   release notes, changelog.
4. **Capabilities** — `ffb6d2ee`: `work/coordinate-a-cross-node-epic` and
   `work/require-tracker-backed-work`, declared in `capabilities.yaml`.
5. **Review fixes** — `640fa466`: `check_type_change` made public (the CLI calls
   it); `create_work` validates against `WORK_TYPES` instead of its own
   `!= "epic"`; the strict capability sentence attributes the refusal to epics being
   ungated, not to the worktree rule; a same-type set on an epic with children is
   tested.

## Evidence

- Every new test was red before its code (TypeError / unrecognized argument). The
  strict test and the rules were then mutation-checked: removing the strict refusal,
  the CLI pre-check, the children check, the graph check, or the promotion
  short-circuit each turns a named test red. The last two mutations first stayed
  green; that exposed a missing test (a plain `""` over a partial graph), added
  before continuing.
- Hands-on in a scratch project: promote, the `-i` board nests the child under the
  promoted epic and shows `ready-to-close` once the child is resolved (identical to
  a `new --epic` epic); demotion with a child is refused naming it, and changes
  neither title nor type; `--type story` is rejected by argparse; demotion succeeds
  once the child's `--initiative` is cleared.
- Full suite at `ffb6d2ee`: 3617 passed. After the review fixes: see
  `refined-outcome.md`.

## What the plan or spec got wrong

- **Criterion 8 named the wrong board view.** `tcw work list` never groups by
  `initiative:`; only `--include-descendants` does (`_render_descendant_boards`).
  My first test passed without checking the grouping at all — the hands-on run
  showed a flat board. The spec was corrected and the test now asserts the child is
  not nested before promotion and is nested after.
- **`fs.py` does not import `WORK_TYPES`**; the review fix initially referenced it
  unimported. Caught by the targeted test run before commit.
- The plan had the spec's criterion edit committed with the CLI task rather than on
  its own.
