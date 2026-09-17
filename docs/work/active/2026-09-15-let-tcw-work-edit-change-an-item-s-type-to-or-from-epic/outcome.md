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
- Full suite at `ffb6d2ee`: 3617 passed. After the review fixes, at `640fa466`:
  3617 passed.

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

## Autonomous decisions

Run unattended under `autonomous-work`; these replace the human checkpoints.

- **Strict tracker mode: refuse every `--type`, allow promotion of a never-bound
  backlog item, or no special handling?** Codex: refuse outright — type controls the
  ticket exemptions, and "never bound" needs history guarantees for little benefit.
  Opus: refuse outright — plain items under strict mode come from `tracker import`,
  so the finer rule serves a nearly empty set, and `ever_bound` counts even an
  unlinked binding. Chose refuse outright.
- **Demotion with children: any child, or only open ones?** Both: any child — a
  resolved child still points at the epic; an epic whose children are resolved
  should be completed. Chose any.
- **Demotion over a partial graph?** Both: refuse, as `complete` does. Chose refuse.
  (Review later found this over-refuses when only a parent is missing — filed as
  inbox entry `2026-09-17-a-missing-parent-project-blocks-epic-gates-that-only-look-down`,
  because the note is shared with `complete`.)
- **Resolved items: refuse type changes?** Split. Opus: refuse, it only rewrites
  history. Codex: no rule, nothing depends on it. Chose Codex's: `update_work`
  already allows title and estimate edits on resolved items, so a type-only rule
  would be an inconsistency with no invariant behind it.
- **Web app:** both advisors: out of scope; its whitelist already rejects `type`.
- **Code review findings accepted:** the strict capability sentence's misattributed
  reason; duplicated type-value check (`create_work` now uses `WORK_TYPES`); the
  missing same-type-with-children test; making `check_type_change` public since the
  CLI calls it.
- **Code review findings rejected or deferred:** parent-missing over-refusal
  (deferred, shared with `complete`, filed); blockers written before a bad tag is
  refused (pre-existing, not worsened, filed as
  `2026-09-17-tcw-work-edit-writes-blockers-before-refusing-a-bad-tag`); the
  children walk running twice on a CLI demotion (rejected — skipping the store's
  own check would let a direct caller through, and the cost is one graph walk).
- **Verifier note: criterion 8 was reworded by the implementer.** Kept: the original
  named `tcw work list`, which never groups by initiative, so it could not have been
  met by any implementation.
- **Verify decision:** accept. Verifier: criteria 1-8 met; criterion 9 met by the
  3617-test run at `640fa466`.
