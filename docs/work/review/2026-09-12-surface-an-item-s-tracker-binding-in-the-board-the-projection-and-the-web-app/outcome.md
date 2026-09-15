# Outcome — Surface an item's tracker binding in the board, the projection and the web app

## What shipped, task by task

| Plan task | Commit | What |
| --------- | ------ | ---- |
| 1 — classification into the model | `9a1c6803` | `Unbound`, `Malformed`, `Bound`, `classify_binding`, `binding_value` in `tcw/store/base.py`; `tcw.tracker.intake` re-exports them and keeps `read_binding` as parse-then-classify. |
| 2 — `WorkItem.tracker` and the schema | `bf2e2ab9` | The field, `FsWorkStore._read_item` filling it, and a closed `oneOf` in `WORK_ITEM_SCHEMA`. |
| 3 — `show` and `list` | `18813037` | `tracker:` line after the fields; ` \| ticket:` segment at the end of a bound row. |
| 4 — web app | `d1383fa7` | `TrackerField` on the work item detail; built client regenerated. |
| 5 — capabilities | `b7bf1908` | `read-a-work-item`, `view-the-board`, `manage-external-tracker-intake`; item `capabilities.yaml`. |
| Documentation Sync | `4b71d06e`, `89a97968` | README, release notes, changelog, `skills/tcw-work/references/commands.md`, and the search procedure's list of optional row segments. |
| Review fixes | `df3d73d8` | See `## Review`. |
| Spec correction | `33eeaa02` | The criterion 1 exception also names hook payloads. |
| Follow-up filed | `d249ff8b` | `docs/work/inbox/2026-09-14-an-unreadable-capabilities-yaml-breaks-the-whole-board.md`. |

## Test results

- `python -m pytest` from the worktree with the editable install pointed at it,
  before the review fixes: **3135 passed** in 660 s.
- After round 1's fixes: `tests/test_tracker_*.py`, `test_projection.py`,
  `test_serve*.py` and `test_work.py` — 767 passed. After round 2's:
  `tests/test_tracker_surface.py` — 34 passed. The full suite is re-run with bare
  `pytest` on merged `main` at verify.
- Web: `pnpm test` 63 passed; `tsc --noEmit` clean; `pnpm lint` clean; Prettier
  clean on the four changed files. (`pnpm prettier --check .` reports hundreds of
  unformatted files on `main` too; that is not this change.)

**Mutation checks** — each broke the named behaviour and the test went red for that
reason, then the code was restored:

- `_read_item` importing its classifier from `tcw.tracker.intake` → the
  fresh-interpreter test failed with `LOADED tcw.tracker,tcw.tracker.intake`.
- `additionalProperties` removed from the `ticket` object, and from the problem
  object → the extra-key tests failed with `DID NOT RAISE ValidationError`.
- An unbound row printing ` | ticket: -` → the "print nothing new" test failed on
  that text.
- The web detail without `TrackerField` → both new `vitest` tests failed.
- `_read_item` catching only `YAMLError` again → all four "does not break the board"
  tests failed.
- `bound` rendered with `str()` again → three of the four non-text `bound` cases
  failed (the datetime case is converted before that line).
- `FileNotFoundError` re-raised again → the mid-read removal test failed with the
  item missing from `query()`; `read_binding` without `RecursionError` → the deep
  nesting test failed.

## What the plan or spec got wrong

- **`Bound` equality.** The plan said `Bound` gains `bound` "unchanged" otherwise.
  An unedited test (`tests/test_tracker_binding.py::test_a_complete_binding_is_bound_with_its_values`)
  compares a `Bound` built without a date, so `bound` is `field(compare=False)`: a
  binding's identity is its key, not when it was made.
- **Writing test bindings through `write_sidecar`.** The plan said so; the store
  refuses text that is not a YAML mapping, which is exactly the malformed case.
  Bindings in the tests are written into the item folder directly.
- **"Only YAML errors" was too narrow.** The plan caught `YAMLError` in `_read_item`;
  the spec's goal 2 ("never breaks the read") needed every read failure. Found by
  review, fixed in `df3d73d8`.
- **`str()` of `bound`.** The spec said a YAML date renders ISO; it did not say what
  anything else renders as, and `str()` was wrong for datetimes, bytes, lists and
  anchor chains. Found by review.
- **The criterion 1 exception** named `show --json` and `tcw serve` but not `generate`
  hook payloads, which are the same document. Spec corrected.
- **Building the web client from a worktree.** The worktree has no `node_modules`;
  a symlink to the primary checkout's let `pnpm` run, but esbuild then wrote
  `../../node_modules/...` paths into `tcw/serve/dist/server.cjs`. That file was
  restored (its source did not change) and the symlink removed before committing.
  The client bundle has no such paths. `pnpm check:build` is re-run on merged `main`.
- **The browser check could not be done.** The plan's Verification step 2 asked for
  the dedicated Chrome profile; no browser connected to this session. Checked
  instead: `curl` of `tcw serve`'s item API returns the bound `tracker` value, the
  served bundle is the rebuilt one and contains the new field's text, and the
  `vitest` tests render the detail view.

## Review

Round 1: the `adversarial-code-reviewer` agent on `a6242e38..4b71d06e`. Round 2, on
the fix commit `df3d73d8`: the same agent was asked twice and did not answer, so a
bounded Codex review (read-only sandbox, confirmed from its session header) stood in.
Every finding was checked against the code.

| Finding | Decision | Why |
| ------- | -------- | --- |
| A `tracker.yaml` that is not UTF-8, is a directory, cannot be opened, or nests too deep crashes `list` for the whole board | **Accepted** | Reproduced by the reviewer; fixed by turning each read failure into the item's problem value, with `FileNotFoundError` still left to `_item_from_dir`. Four tests. |
| `str(bound)` misrenders non-text values and expands a YAML anchor chain without limit | **Accepted** | Fixed: text kept, date/datetime ISO, anything else empty. Tests include an anchor chain. |
| The YAML-error reason is written twice | **Accepted** | `unreadable_binding` in `base.py`, used by both. Read failures are worded "not a readable text file" rather than "not valid YAML". |
| Invalid-YAML text output and ordering after `blocked_by` untested | **Accepted** | Tests added. |
| Search procedure's segment list omits `ticket:` | **Accepted** | Updated. |
| Criterion 1 exception omits hook payloads | **Accepted** | Spec updated. |
| The `node_modules` symlink could be committed | **Accepted** | Removed; never committed. |
| The same crash exists for `capabilities.yaml` | **Narrowed to a follow-up** | Older code beside this change; filed in the inbox. |
| *Round 2:* a `tracker.yaml` deleted between `exists()` and the read drops a healthy item from the board | **Accepted** | Reproduced with a test reading `query()`; now unbound (`ea70cc93`). |
| *Round 2:* `read_binding` lets `RecursionError` escape to `import` and `link` | **Accepted** | Caught and reported as unreadable (`ea70cc93`). |
| *Round 2:* a FIFO named `tracker.yaml` blocks the read forever | **Rejected** | Needs a deliberately created special file in an item folder; every other file the store reads (`state.yaml`, `capabilities.yaml`, the artifacts) has the same exposure, so it is not this change's to fix alone. |
| *Round 2:* `MemoryError` on a huge file; `exists()` raising on older Python | **Rejected** | The same for every file the store reads; the item folder was already readable to get this far. |
| *Round 2:* `bound` for every YAML type | **No defect** | — |

## Notes

- **The editable install.** A stale `tcw 0.10.3` distribution was still registered
  beside `tcw-cli 2.2.0`, shadowing the worktree. Removed with `pip uninstall tcw`,
  as the project guide describes for a stale hook; that also removed the `tcw` script
  until `tcw-cli` was reinstalled.

## Autonomous decisions

- **JSON route** — Codex: a `WorkItem` field; Opus: the same. Chose the field, no
  version bump (spec § Design).
- **Where the classifier lives** — Codex: a new small module outside `tcw.tracker`;
  Opus: `base.py`, over already-parsed data, like `declared_capabilities`. Chose
  Opus's: it follows a pattern already in the model.
- **Board segment position** — Opus: before the claim segment; chose the end of the
  row instead, the only place that moves no existing segment.
- **Epic capability table** — corrected `work/open-a-work-item` to
  `work/view-the-board` without consulting; the capability texts settle it.
- **Order among the remaining children** — this item before C3, so C3 extends an
  identity that already prints; recorded in the request and the epic spec.
