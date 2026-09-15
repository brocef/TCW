# Outcome — Emit new location when CLI commands move a TCW object

Approach B shipped as planned: an abstract `WorkStore.locate(slug) -> str | None`
realized by `FsWorkStore`, with four CLI call sites reading it. The CLI contains
no `node_root`/`relative_to` for this feature.

## What shipped

### Phase 1 — store interface + FS adapter (`eb55ad7`)

`feat(store): add abstract WorkStore.locate + FS repo-relative realization`

- `tcw/store/base.py` — `WorkStore.locate(slug) -> str | None` added as an
  `@abstractmethod` immediately after `artifact_locator`, with the spec's
  docstring verbatim (presentation only; do not parse).
- `tcw/store/fs.py` — `FsWorkStore.locate` beside `path`: `path(slug)` relative
  to `node_root`, `None` when the item does not exist, and the absolute path as
  the `ValueError` fallback when the item sits outside `node_root`.
- No other `WorkStore` subclass exists, so nothing else needed an implementation
  (spec's claim confirmed — the full suite would have failed instantiating an
  abstract store otherwise).

### Phase 2 — CLI wiring (`f4da0df`)

`feat(work-cli): report the item's new location on start, complete, inbox accept, and new`

All in `tcw/work/cli.py`, each site calling `st.locate(...)` and appending only
when the result is truthy:

- `_start`, non-worktree: `started <slug> → docs/work/active/<slug>`.
- `_start`, worktree: `started <slug> → <loc> (worktree <wt>)`, falling back to
  the previous `started <slug> → worktree <wt>` when `loc` is `None`.
- `_complete`: `completed <slug> (<resolution>) → docs/work/completed/<slug>`.
- `_inbox_accept`: stdout still the bare slug; stderr gains `→ now at <loc>`.
- `_new`: stdout still the bare slug; stderr gains `→ created at <loc>` above the
  existing `→ edit:` / `→ next:` hints.

### Phase 3 — tests (`d58bb05`)

`test(work): cover locate() and the new location text on start/complete/accept/new`

- New `test_locate_reports_repo_relative_home_and_degrades_gracefully`
  (`tests/test_work.py`): backlog then active repo-relative paths, `None` for a
  missing slug, and — with `path` monkeypatched to a directory outside
  `node_root` — the absolute-string fallback with no raise.
- `test_cli_new_and_start_emit_next_step_hints`: `start` stdout asserted as
  `started {slug} → docs/work/active/{slug}`; `new` stderr asserted to contain
  `→ created at docs/work/backlog/{slug}`.
- `test_cli_inbox_list_show_accept`: stdout still the bare slug, stderr contains
  `→ now at docs/work/backlog/{slug}`.
- `test_cli_complete_requires_confirm`: stdout contains
  `completed {slug} (done) → docs/work/completed/{slug}`.
- `test_work.py:1544` (cross-node `started project-a/{slug}`) uses `in` and
  needed no change, as the plan predicted.

### Phase 4 — documentation sync (`7655371`)

`docs: record the new-location output in README, changelog, and release notes`

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fired.** Added:
  `WorkStore.locate` + the FS realization and its two degradation cases.
  Changed: the four commands' output, with the stdout/stderr split spelled out.
- `docs/release-notes/upcoming.md` [Public-API] — **fired.** Plain-language note
  with a sample line per command and the reassurance that `inbox accept`/`new`
  stdout is unchanged for scripts.
- `README.md` [Public-API] — **fired** (the plan guessed it likely would not; see
  corrections). Extended the existing paragraph about the `→ next:` / `→ edit:`
  hints with the location line and where each command emits it.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — **did not fire.** The
  skill drives the component purely through CLI verbs; it quotes no transition
  output and no `docs/work/<status>/…` paths, so there is nothing to drift.

## Test result

```
$ python -m pytest tests/test_work.py -q
152 passed in 46.58s

$ python -m pytest -q
1098 passed in 171.64s (0:02:51)
```

Both green, run after the Phase 3 commit; the Phase 4 commit is documentation
only.

## What the plan or spec got wrong

All corrections were made in `plan.md` in place.

1. **Every line number in the spec's current-state findings was stale**, by 200–300
   lines. Actual: `artifact_locator` is `base.py:948` (not `:633`);
   `FsWorkStore.path` is `fs.py:1776` (not `:1583`); in `cli.py`, `_new` is
   `:233`, `_inbox_accept` `:284`, `_start` `:473`, `_complete`'s print `:875`.
   The test line numbers were stale too (`:880` → `:927`, `:1497` → `:1544`).
   Everything the findings *asserted* at those lines was correct — only the
   coordinates were wrong.
2. **`_complete`'s print serves discards as well.** The spec and plan describe it
   as the completion message, but the one line renders
   `{'completed' if shipping else 'discarded'} …`, so a discard now also reports
   its `docs/work/discarded/<slug>` home. Kept deliberately: suppressing it would
   have added a branch in order to make the output less useful, and "where did it
   go" is exactly as unclear after a discard as after a completion. Not a
   behavior the spec forbade — a case it did not notice it was specifying.
3. **`tests/test_fs_*` does not exist.** Phase 3 offered it as the first home for
   the `locate` unit test; the work-store tests all live in `tests/test_work.py`,
   which is where it went.
4. **README fired.** The plan predicted "likely no change" on the grounds that it
   might quote the old output. It does not quote it, but it does document this
   exact surface — the `→ next:` and `→ edit:` hint lines and their stdout/stderr
   split — so a README describing that surface without the new location line
   would have been incomplete rather than merely stale.

## Notes

- `FsWorkStore._find` rescans the filesystem on every call (no caching), so
  calling `locate` after the store has moved the folder reports the new home
  rather than a stale one. This is load-bearing for all four call sites and is
  worth knowing before anyone adds caching there.
- The `ValueError` branch in `locate` is unreachable through the FS adapter's own
  `path()` today — every item folder is under `docs/work/` inside `node_root`.
  It is defensive, and the test reaches it by monkeypatching `path`. If a future
  change makes it genuinely reachable (e.g. items resolved through a symlinked or
  externally-mounted store root), the fallback's absolute output is the intended
  behavior, not a bug.
- The spec's constraint note stands: `start`/`complete` stdout is prose and
  changed, so this is a user-visible output change and a minor-bump candidate at
  closeout. No version was cut.
