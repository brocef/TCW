# Plan — Harden _effect_transition against a lost status-transition race

Five tasks. Ordering rationale: the mechanical, behavior-preserving work lands
first so the one piece of *new* behavior (`_effect_transition`'s race message)
sits alone in a small commit that is easy to read and easy to revert. Each task
is green at its own commit boundary — no task leaves the tree broken for the
next, so no test is committed ahead of the code it pins. Where the spec requires
"fails against current code" evidence (criterion 4), the task says to obtain it
by stashing the fix, not by committing a red suite.

---

## Task 1 — Add `_require_dir` and collapse the eight identical guards

**Changes:** `tcw/store/fs.py`.

Add next to `_find` (after `fs.py:2077`):

```python
def _require_dir(self, slug: str) -> Path:
    d = self._find(slug)
    if d is None:
        raise ValueError(f"no such work item: {slug}")
    return d
```

Then replace the eight hand-written copies of that exact guard. Each is a
`d = self._find(slug)` followed by a two-line `if d is None: raise
ValueError(f"no such work item: {slug}")`, and each becomes
`d = self._require_dir(slug)`:

| `_find` line | `raise` line | Function |
| --- | --- | --- |
| `fs.py:2143` | `2145` | `_declared_plan_stages` |
| `fs.py:2721` | `2723` | `set_field` |
| `fs.py:2793` | `2795` | `_delete` |
| `fs.py:2946` | `2948` | `update_work` |
| `fs.py:3084` | `3086` | `read_artifact` |
| `fs.py:3104` | `3106` | `write_artifact` |
| `fs.py:3141` | `3143` | `read_sidecar` |
| `fs.py:3163` | `3165` | `write_sidecar` |

**Do not touch** `fs.py:2868` and `fs.py:3010` — they guard a *parent* lookup and
raise a different message (`no such parent work item: {parent}`). Collapsing
those into `_require_dir` would silently change their text.

**Verify:**

- `pytest` full suite green with **zero test edits** — in particular
  `tests/test_work.py:1680`, `tests/test_qualified_ref.py:95`, and
  `tests/test_store_editor.py:299`, which assert the literal
  `no such work item` text (acceptance criterion 7).
- Read the diff: exactly eight `raise ValueError(f"no such work item: {slug}")`
  statements disappear and one appears inside `_require_dir`. No site gains or
  loses a `raise`. `git diff --stat` should show a net line reduction in
  `fs.py`.
- Criterion 8 holds structurally, not by test: `MultipleMatch` is raised *inside*
  `_find` (`fs.py:2076`), which `_require_dir` calls before its own check, so it
  propagates unchanged from every collapsed site. The callers that rely on it
  (`work/cli.py:451`, `474`, `820`) are unaffected; `tests/test_work.py`'s
  `test_multiple_match_resolution_error` (~line 325) still passes.

**No new tests.** This task is behavior-preserving by construction and the
existing three text assertions are the regression pin.

---

## Task 2 — Guard the four remaining unguarded `_find` sites

**Changes:** `tcw/store/fs.py`; tests in `tests/test_external_work_store.py`,
`tests/test_work.py`, `tests/test_validate_target.py`,
`tests/test_store_editor.py`.

Three sites become `_require_dir`; one returns `None`:

1. **`fs.py:2005`** — `start()`'s take-over commit path.
   `rel = str(self._find(slug).relative_to(...))` →
   `rel = str(self._require_dir(slug).relative_to(...))`.
   Turns an `AttributeError` on `None.relative_to` into the handled `ValueError`.
2. **`fs.py:2219`** — `_plan_stage_path`.
   `return self._find(slug) / "plan" / f"{stage_id}.md"` →
   `return self._require_dir(slug) / "plan" / f"{stage_id}.md"`.
3. **`fs.py:2485`** — `_validation_problems`.
   `folder = self._find(item.slug)` → `folder = self._require_dir(item.slug)`.
   Its `ValueError` is absorbed by the enclosing `except ValueError`
   (`fs.py:2504`) and reported as a validation problem — see the Verification
   section for the false-positive this deliberately accepts.
4. **`fs.py:2804`** — `get_detail`. **Not** `_require_dir`: the function is
   already `-> WorkDetail | None`, so add `if d is None: return None` under the
   `_find` call. Smaller and correct.

**Tests** — one per site, each forcing `_find` to return `None` by monkeypatch
(never by racing threads), following
`tests/test_external_work_store.py:126-163`:

- **`fs.py:2005`** → `tests/test_external_work_store.py`, beside the existing
  take-over tests (lines 166, 179). `start(slug, owner=…, take_over=True)` on an
  active item; assert `ValueError` matching `no such work item`, and assert it is
  **not** an `AttributeError`. A raw call counter is brittle here (the take-over
  branch does `get` → `set_field` → `set_field` → the guarded `_find`, four
  lookups), so prefer wrapping `set_field`: after the `started` write lands,
  `monkeypatch.setattr(FsWorkStore, "_find", lambda self, slug: None)`. That is
  deterministic regardless of how many lookups precede it. Requires
  `auto-commit-transitions` on, which is the default
  (`tests/test_work_autocommit.py:157`).
- **`fs.py:2219`** → `tests/test_work.py`, beside
  `test_staged_plan_dag_and_revision_safe_crud` (line ~261). Write a staged
  `plan.md`, then call `read_plan_stage(slug, "model")` with `_find` patched to
  return `None` on its **second** call (`_declared_plan_stages` consumes the
  first). Assert `ValueError`, not `TypeError`.
- **`fs.py:2485`** → `tests/test_validate_target.py`, which already drives
  `validate(root, target=ValidationTarget("work", slug))` into
  `_validation_problems` (line 87). Give the item a staged `plan.md`, then wrap
  `_declared_plan_stages` so that after it returns, `_find` starts returning
  `None`. Assert the result is a returned problem list containing
  `no such work item` — not a raised `TypeError`. (A call counter is unreliable
  here because `validate` walks other paths that also call `_find`.)
- **`fs.py:2804`** → `tests/test_store_editor.py`, beside
  `test_get_detail_unknown_slug_returns_none` (line 109). `_find` patched to
  return `None` on its second call (`get()` consumes the first); assert
  `get_detail(slug) is None`.

**Verify:** each new test fails before its one-line fix (check by `git stash`ing
the `fs.py` hunk, or by writing the test and running it once before editing
`fs.py`) with the specific error the spec predicts — `AttributeError`,
`TypeError`, `TypeError`, `TypeError` respectively. Full suite green after.

---

## Task 3 — The race-aware error in `_effect_transition`

The only new behavior in this item, deliberately isolated in its own commit.

**Changes:** `tcw/store/fs.py:2734`; tests in
`tests/test_external_work_store.py`.

Between `src = self._find(slug)` (`fs.py:2734`) and the `mkdir`
(`fs.py:2741`), insert the spec's five lines verbatim:

```python
src = self._find(slug)
if src is None:
    current = self.get(slug)
    where = (f"it is now in '{current.status}'" if current is not None
             else "it no longer exists")
    raise ValueError(
        f"cannot move {slug} to {to_status}: another process moved it first "
        f"({where}). This process did not move it; re-read the item before "
        f"retrying."
    )
```

Not `_require_dir`: "no such work item" is the wrong claim here — the item
exists, it moved. Keep the guard **above** `mkdir` and `_mv` so nothing is
touched on the failing path (criterion 3).

**Tests** — three, all in `tests/test_external_work_store.py` (it holds the
sibling's monkeypatch test and already imports `main` from `tcw.cli`):

1. **Store level, criteria 1 and 3.** Call `store._effect_transition(slug,
   "completed")` directly on a `review` item — exactly two `_find` calls, so the
   counter is unambiguous. Patch `_find` to return `None` on call 2 only (call 3,
   the re-read inside the handler, must be real, or the message degrades to "it
   no longer exists"). To make the reported status *meaningfully different* from
   both ends of the attempted move, have the patched call-2 also `shutil.move`
   the folder from `docs/work/review/<slug>` to `docs/work/backlog/<slug>` before
   returning `None` — two extra lines that turn a near-tautological assertion
   into a real one. Assert: `ValueError`, message contains the slug and
   `is now in 'backlog'`; and the folder is still where the "competitor" left it
   (criterion 3 — a pin against someone later moving the guard below `_mv`).
2. **Criterion 4, the failing-first proof.** The same test satisfies it. Before
   editing `fs.py`, run it and record the failure: with `completed/` gitignored
   by default (`fs.py:489-499`) it fails with `FileNotFoundError` from
   `shutil.move("None", …)`, **not** `TypeError`. Note that in the test's
   docstring — the spec's Notes section flags the request's guess as wrong and
   the test is the place that record survives.
3. **CLI level, criterion 2.** `main(["work", "complete", slug, "--resolution",
   "done", "--confirm"])` with `_effect_transition` wrapped so it installs the
   call-2-returns-`None` patch on entry. Assert exit code `1`, stderr contains
   `tcw work complete: cannot move`, and no traceback. `ValueError` is already in
   `_ERRORS` (`work/cli.py:34`) and the handler is `work/cli.py:923`. Do **not**
   add a submit/rework variant unless the complete one proves the routing is
   per-command — the prefix inconsistency (`tcw work:` at `cli.py:583`/`605` vs
   `tcw work complete:` at `923`) is pre-existing and explicitly not changed
   here.

**Verify:** the three tests; full suite green.

---

## Task 4 — Pin the residual, and file the follow-up item

**Changes:** `tests/test_external_work_store.py`; one new backlog item.

Must follow Task 3 — before the guard exists, `complete` crashes in `git_mv`
rather than reaching this state.

1. **Regression pin for the known-unfixed residual (criterion 9).** A `complete`
   that loses the race has already written `resolution` via `set_field`
   (`base.py:1397`) before `_effect_transition` runs. Assert the *current*
   behavior: after the guarded `ValueError`, the item still carries the loser's
   `resolution` while sitting in its unmoved status. The test's docstring must
   say this is a documented limitation, not a passing behavior, and name the
   follow-up item slug from step 2. Also note it can produce exactly the
   status/resolution disagreement that `_status_resolution_problems`
   (`fs.py:2508-2513`) still describes as something "no code path can produce" —
   that docstring is now known to be optimistic.
2. **File the follow-up.** The flag is `--tag`, repeatable — **not**
   `--tags` with a comma list (`work/cli.py:1035`; comma support is itself a
   separate backlog item):

   ```
   tcw work new "Roll back or reorder the pre-move set_field writes on a lost transition" --tag bug --tag work
   ```

   Then write its `initial-request.md` from spec §Design 3: the two-completers
   scenario, the `base.py:1272-1274` / `base.py:1397` write sites, and the
   ordering constraint documented at `work/cli.py:915-918` (a hook evaluated any
   later would abort after already stamping a resolution). **Do not fix it here.**
   Fill in the slug in step 1's docstring once `tcw work new` reports it.

**Verify:** the pin passes; `tcw work list --status backlog` shows the new item;
full suite green.

---

## Documentation Sync

Evaluated against `CLAUDE.md` §Documentation Sync via the `documentation-sync`
skill, entry by entry — including the two the spec predicted, checked rather
than copied.

- **`README.md` [Public-API]** — **does not fire.** No command, subcommand, flag,
  or documented behavior changes. `_require_dir` is private; the four guards
  produce error text README never quotes.
- **`docs/release-notes/upcoming.md` [Public-API]** — **fires.** A user racing
  two agents on one item previously got a Python traceback
  (`FileNotFoundError`, or `CalledProcessError` on a node that un-ignored
  `completed/`) and now gets a plain sentence naming where the item actually is.
  That is user-visible. Plain language, no module names.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — **fires.** Behavior
  changes in `tcw/store/fs.py`. Grouped: *Fixed* for the `_effect_transition`
  guard and the four `None`-dereference sites; *Internal* for the `_require_dir`
  collapse. The `tcw work validate` false-positive noted under Verification
  belongs here too — it is a real output change, and the changelog is where a
  developer parsing that output would look.
- **`skills/tcw-work/SKILL.md` [Skill-Driven-Component]** — **does not fire.**
  Verified independently, not taken from the spec: the trigger fires on a change
  to the driven component's *CLI surface, model/fields, lifecycle, or
  guardrails*. None move. `grep -n "AlreadyClaimed\|race\|no such work item"`
  across `skills/tcw-work/SKILL.md` and `skills/tcw-work/references/*.md` returns
  nothing about transition races or error recovery, so there is no existing
  statement this change makes stale. The `submit`/`rework`/`complete` contract the
  skill teaches is unchanged — it becomes true on one timing where it previously
  crashed.

### Task 5 — Write the two doc entries

One pass over the finished diff, after Tasks 1-4, as
`stage-implement.md` step 6 requires:

- `docs/changelogs/upcoming.md` — Fixed / Internal entries as above.
- `docs/release-notes/upcoming.md` — one line under a Fixed heading.

**Verify:** `pytest tests/test_documentation_sync_wiring.py` and the full suite.
Neither file is version-bearing, so no version bump is implied.

---

## Verification

What the suite covers: criteria 1-5, 7 (via the three unmodified text
assertions), and 9. What it does not:

- **Criterion 6 — the sweep.** Run `grep -n "_find(" tcw/store/fs.py` after Task
  4 and read every hit. Expected end state: `2073` (the definition), `2080`
  (`path`, returns it), `2260` (`_unique_slug`, `is not None` loop), `2320`
  (`get`, checks), `2543` (`_validation_resources`, checks), the four sites
  guarded in Task 2, the eight now routed through `_require_dir`, `2734` (Task
  3's guard), and `2868` / `3010` (parent lookups with their own guard and their
  own message). No hit may dereference a bare `_find` result. This is a
  read-the-code check; no test can assert it.
- **Criterion 7's collapse, beyond the three text assertions.** Those three tests
  do not cover all eight collapsed sites individually. The remaining evidence is
  reading the Task 1 diff — confirmed by inspection, not by the suite.
- **Criterion 8.** `MultipleMatch` propagation from all eight collapsed sites is
  structural (raised inside `_find`, above the guard). Argued in Task 1, not
  tested per-site.
- **Criterion 10 — CI.** Both legs need a push; local green is necessary, not
  sufficient.
- **The false validation problem this deliberately accepts.** After Task 2, a
  `tcw work validate` sweep that races a *healthy* transition reports
  `<slug>: no such work item: <slug>` against an item with nothing wrong with it.
  A spurious line beats a traceback, so this is the right trade, but it is a
  visible output change in a command whose output may be parsed, and the reported
  problem is untrue. No test asserts the false positive does not occur, because it
  does occur by design. If it ever matters, the fix is for the validation loop to
  skip items that vanish mid-scan — out of scope here.
- **The race itself is never exercised.** Every test drives the *handler* via
  monkeypatch; no arrangement of files reproduces the interleaving, because
  whatever makes `get()` succeed makes `_find` succeed. Accepted, same as the
  sibling item. Nothing in this plan demonstrates the window is reachable in the
  wild — the spec assesses it as reachable but rare, and that is the honest
  framing at closeout.
- **The honest closeout claim** is "the loser no longer crashes, and is told where
  the item went", **not** "the race is handled". The pre-move `set_field` writes
  still land (Task 4's pin proves it). Task 4's follow-up item must exist before
  this item completes.

## Notes

- The spec is accurate against the code as of this reading; every `file:line` in
  it verified. No factual errors found.
- Tasks 1 and 2 touch already-correct call sites in a bug-fix item. That is the
  spec's accepted risk, bounded by criterion 7. If review objects, Task 1 is
  droppable on its own — Task 2 then writes three inline guards instead — and
  Tasks 3-5 are unaffected either way.
