# Outcome — Harden _effect_transition against a lost status-transition race

Five plan tasks, five commits, in order. Full suite green at every boundary.
Nothing in the plan turned out to be wrong; two small mechanical details it did
not anticipate are recorded below.

## What shipped

### Task 1 — `_require_dir` and the eight-guard collapse — `239a9ff`

Added `FsWorkStore._require_dir` next to `_find` and replaced the eight
hand-written copies of the `no such work item` guard, exactly the eight the plan
listed. Net **-10 lines** in `fs.py` (14 insertions, 24 deletions).

Diff read for criterion 7: exactly eight `raise ValueError(f"no such work item:
{slug}")` statements disappear, one appears inside `_require_dir`. No site gains
or loses a `raise`. The parent lookups (`no such parent work item`) were left
alone as instructed. Criterion 8 holds structurally — `MultipleMatch` is raised
inside `_find`, which `_require_dir` calls before its own check.

Zero test edits; the three literal-text assertions passed unmodified. **1204
passed.**

### Task 2 — the four remaining unguarded sites — `7a16b16`

`start()`'s take-over commit lookup, `_plan_stage_path`, and `check()` route
through `_require_dir`; `get_detail` returns `None`, which its signature already
promised. Four tests, one per site, each written and run **before** the fix.

Observed first-failure exceptions — all four exactly as the spec predicted:

| Site | Test | Failure before the fix |
| --- | --- | --- |
| take-over commit lookup | `tests/test_external_work_store.py::test_takeover_lost_at_the_commit_lookup_is_a_valueerror` | `AttributeError: 'NoneType' object has no attribute 'relative_to'` |
| `_plan_stage_path` | `tests/test_work.py::test_plan_stage_path_lost_at_find_is_a_valueerror` | `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'` |
| `check()` | `tests/test_validate_target.py::test_work_target_reports_an_item_that_vanishes_mid_check` | `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'` |
| `get_detail` | `tests/test_store_editor.py::test_get_detail_lost_at_find_returns_none` | `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'` |

**1208 passed.**

### Task 3 — the race-aware error — `6cf20c0`

The spec's five lines verbatim, above the `mkdir` and the `_mv`. Two tests, both
run before the fix.

**The observed failure was `FileNotFoundError`, not `TypeError`** — the spec's
correction of the original bug report is confirmed empirically:

```
FileNotFoundError: [Errno 2] No such file or directory: 'None' -> '.../docs/work/completed/2026-08-08-race-me'
```

`completed/` is gitignored by default, so `_mv` takes the non-git branch and
`git_mv` stringifies `None` into the literal path `"None"`. Both the store-level
and CLI-level tests failed this way. That is recorded in the store test's
docstring, which is where it will survive.

After the fix: `ValueError` naming the slug and `is now in 'backlog'` (the
"competitor" moves the folder to `backlog` so the reported status differs from
both ends of the attempted move); the folder stays where the competitor left it
and nothing appears in `completed/`. At the CLI, `tcw work complete` exits 1 with
`tcw work complete: cannot move …` on stderr and no traceback. **1210 passed.**

### Task 4 — the residual pin and the follow-up — `bb6f2bf`

`tests/test_external_work_store.py::test_lost_complete_leaves_its_resolution_written`
asserts the *current* behavior: after the guarded `ValueError` the item is still
in `review` and still carries `resolution: done`. The docstring says plainly that
this is a documented limitation, names the follow-up slug, and notes that
`_status_resolution_problems`' "no code path can produce" docstring is now known
to be optimistic. It says the test should be inverted, not deleted, when the
follow-up lands.

Follow-up filed:
**`2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`**
(backlog, `--tag bug --tag work`). Its `initial-request.md` carries the
two-completers scenario, the `base.py:1272-1274` / `base.py:1397` write sites, and
the `work/cli.py:915-918` ordering constraint that blocks the obvious fix.
**1211 passed.**

### Task 5 — documentation — `e234e62`

`documentation-sync` run once over the finished diff. Verdicts matched the plan's
predictions on all four entries:

- `README.md` [Public-API] — **did not fire.** No command, flag, or documented
  behavior changed.
- `docs/release-notes/upcoming.md` [Public-API] — **fired.** One plain-language
  Fixed line.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fired.** Fixed (the guard,
  the four sites, and the `tcw work validate` output change) and Internal (the
  `_require_dir` collapse, the residual pin).
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — **did not fire.** Re-ran
  the plan's grep for `AlreadyClaimed|race|no such work item` across the skill and
  its references: no hits, so no existing statement is made stale.

Version cross-check before appending: `pyproject.toml` is `0.20.0` and
`v0.20.0.md` already exists in both directories, so `upcoming.md` is the correct
target for the next version and no rotation was implied.

## Test result

`pytest` (full suite), final: **1211 passed, 0 failed** in 5:05. Green at every
one of the five commit boundaries (1204 / 1208 / 1210 / 1211 / 1211).

Criterion 6 is a read-the-code check, run at the end. `grep -n "_find(" tcw/store/fs.py`
leaves 13 bare-`_find` hits, each one accounted for: the definition (2073), the
call inside `_require_dir` (2080), `path()` (2086) which returns `Path | None`,
five that check for `None` and return a fallback (`body_path` 2098, `artifacts`
2106, artifact locator 2121, `_validation_resources` 2547, `get_detail` 2813),
`_unique_slug`'s `is not None` loop (2264), `get`'s conditional (2326), `start`'s
claim lookup (2020, guarded by the sibling item's `FileNotFoundError`
normalization), `_effect_transition` (2736, this item's guard), and the two parent
lookups (2879, 3019) with their own guard and message. **No hit dereferences a
bare `_find` result.**

Criterion 10's CI half needs a push; local green is done.

## What the plan got wrong

Nothing substantive. Two mechanical corrections made in place:

1. **`store.complete(slug, "done")` does not typecheck.** `dod_ack` is a required
   positional in `WorkStore.complete`, so the Task 4 pin calls
   `store.complete(slug, "done", dod_ack=[])`. The plan wrote the call as if it
   were optional.
2. **The eight-guard block matched nine times, not eight.** `_require_dir`'s own
   body is byte-identical to the guard it replaces, so a naive `replace_all` would
   have made the helper call itself. The collapse skipped the first occurrence.
   Worth knowing for anyone re-running this mechanically.

## Notes

- **The plan's monkeypatch strategies were right for the right reasons.** Raw
  `_find` call counters were used only where the count is genuinely fixed
  (`_plan_stage_path` and `get_detail` take exactly two lookups;
  `_effect_transition` exactly two). Where the plan warned a counter would be
  brittle it was, and the wrapper approach it prescribed works: wrapping
  `set_field` for the take-over path, `_declared_plan_stages` for the validation
  path. For the two `complete`-driven tests the same trick was applied one level
  up — wrap `_effect_transition` itself and install a fresh call-2 patch on entry,
  which makes the count independent of everything `complete()` does beforehand.
- **The Task 4 pin needs `monkeypatch.undo()`.** The patch is installed on the
  class from inside the wrapper, so it is still live when the `ValueError`
  propagates out; the post-condition read has to happen with a real `_find`.
  Anyone extending these tests will hit the same thing.
- **The `tcw work validate` false positive is real and now reachable in a test.**
  `test_work_target_reports_an_item_that_vanishes_mid_check` asserts the spurious
  `no such work item` line as the *desired* outcome (it beats a traceback). If
  someone later implements the skip-items-that-vanish-mid-scan policy the spec
  suggests, that test is the one that will fail, and it should be inverted rather
  than patched around — same posture as the Task 4 pin.
- **The honest closeout claim, unchanged from the plan:** the loser no longer
  crashes and is told where the item went. The race is *not* handled — the
  pre-move field writes still land, which Task 4's pin proves and the follow-up
  item now owns.
- Nothing here touched the abstract store interface. `_require_dir` and the guard
  are private FS-adapter details; the error type (`ValueError`) is the one the
  abstract CLI already handles, and "re-read the item's current status" is an
  operation any store can perform.
