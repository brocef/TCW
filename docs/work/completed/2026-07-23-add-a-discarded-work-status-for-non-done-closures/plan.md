# Implementation plan

## Overview

Seven phases. The core status model lands first because everything else derives
from `WORK_STATUSES`; the resolved/shipped split is spread across phases 1–2 and
is the part to get right. The repo's own migration is its own commit, after the
code can see a `discarded/` folder. Documentation and the capability flip close
it out.

Run `tcw work start 2026-07-23-add-a-discarded-work-status-for-non-done-closures`
and commit that transition before the first code edit.

## Phase 1: Core status model

`tcw/store/base.py`

1. `WORK_STATUSES = ("backlog", "active", "completed", "discarded")`.
2. Add `RESOLVED_STATUSES = ("completed", "discarded")`.
3. Add `resolution_status(resolution)` — raises `ValueError` on anything outside
   `WORK_RESOLUTIONS`, returns `"completed"` for `done` and `"discarded"`
   otherwise. It must never guess a destination (see spec §1).
4. `LEGAL_TRANSITIONS` gains `("active", "discarded")` and
   `("backlog", "discarded")`.
5. `complete()` — derive `dest = resolution_status(resolution)`; narrow
   `from_backlog_epic` to `dest == "completed"`; use `dest` in both the
   legality check and the final `transition()` / `_effect_transition()` calls.
6. **The resolved split** — switch to `RESOLVED_STATUSES`:
    - `unresolved_blockers` (`base.py:939`)
    - `epic_completable` (`base.py:920`, both the child test and its own
      already-terminal guard)
    - `complete()`'s open-children check (`base.py:977`)

Tests (`tests/test_work.py`, `tests/test_epic_completable.py`):

- Update the `WORK_STATUSES` guard at `tests/test_work.py:53`.
- Each of the four resolutions lands in the right folder.
- `backlog → discarded` direct, for each non-`done` resolution.
- `backlog → completed` still refused for a non-completable item, still allowed
  for a completable epic.
- An item blocked by a discarded item starts and completes.
- An epic with one completed and one discarded child is completable.
- `resolution_status()` raises on `""`, `None`, and an unknown string.

## Phase 2: The rest of the resolved split

1. `tcw/work/recursion.py:106,109` — rollup counts a discarded child as
   resolved.
2. `tcw/capabilities/cli.py:210` — **leave reading `completed`.** Add a comment
   naming the distinction so a future reader doesn't "fix" it into
   `RESOLVED_STATUSES`. This is the shipped-vs-resolved boundary.

Tests:

- `tests/test_recursion.py` — reconcile rollup with a discarded child reports
  the epic ready to close; `--complete-when-ready` closes it.
- A discarded item's still-`Missing` declared capability is **not** reported by
  `tcw capabilities drift`; a completed item's still is.

## Phase 3: The consistency detector

`tcw/store/fs.py:1916` (`FsWorkStore.check`), reusing the core
`resolution_status()` so the rule has one definition.

Report, per item:

- terminal status with a missing or invalid `resolution`;
- valid resolution whose derived status disagrees with the item's status;
- non-terminal status (`backlog`/`active`) carrying a `resolution`.

Tests: one case each, plus a clean node reporting nothing.

## Phase 4: CLI gates

`tcw/work/cli.py`

1. `list` (line 276) hides `discarded` as well as `completed`; `--all` includes
   both; `--status discarded` selects it. `--status` choices pick the new value
   up from `WORK_STATUSES` automatically.
2. `_complete` (line 561) branches on the resolution:
    - **DoD** — print the checklist only for `done`; pass `dod_ack=[]` otherwise.
      `--confirm` is still required either way.
    - **Capability gate** — run `capability_gate` only for `done`. For a discard,
      print a non-blocking warning naming any declared capability still reading
      `Missing`, suggesting `tcw capabilities set <path> --status Omitted`.
    - **Worktree** — skip `merge_worktree` for a discard. Still call
      `remove_worktree`, and warn naming the retained branch so the user can
      `git branch -D` it deliberately.

Tests (`tests/test_work.py`):

- Discard prints no DoD lines and records `dod: []`; `done` still prints them.
- Discard without `--confirm` is still refused.
- Discard with an unreconciled declared capability succeeds and warns; `done`
  with the same state still fails closed.
- Discarding a `--worktree` item performs no merge, removes the worktree, leaves
  the branch, and names it in the warning.
- `list` default hides discarded; `--all` and `--status discarded` show it.

## Phase 5: Web app

1. `tcw/serve/__init__.py` — confirm the `complete` action needs no change (it
   delegates to `work.complete`, which now derives the destination). Add a test
   asserting a non-`done` resolution returns status `discarded`.
2. `web/client/src/ui/app.tsx:51` and `content-views.tsx:47` — extend both
   `WORK_STATUSES` literals in place. Deduplicating them is out of scope.
3. `web/client/src/model/tree.ts:9` — sort `discarded` after `completed`.
4. Status filter — a fourth toggle, defaulted **off**, matching the CLI.
5. Complete modal — a non-`done` resolution replaces the DoD acknowledgments and
   the capability-reconciliation reminder with the discard warning.

Tests: `web/client/src/model/tree.test.ts` for ordering;
`tests/test_serve_write.py` for the API status; existing vitest coverage for the
filter and modal branch.

Also assert an invalid resolution posted to the API returns **422**, not 500.
The existing handler catches `ValueError` and `_map_store_error` maps a
validation `ValueError` to `UNPROCESSABLE_ENTITY` (`serve/__init__.py:162`), so
this should already hold — but `resolution_status()` introduces a new raise on
that path and the assertion is what keeps it from regressing into a 500.

## Phase 6: Migrate this repo's three items

**Its own commit, no code.** After phase 1 so the folder is scannable:

```sh
git mv docs/work/completed/2026-06-19-additional-capability-sidecars docs/work/discarded/
git mv docs/work/completed/2026-07-03-live-browser-test-pass-for-the-interactive-web-editor docs/work/discarded/
git mv docs/work/completed/2026-07-03-per-object-capability-revision-token-fix-file-scoped-409s docs/work/discarded/
```

`state.yaml` is not edited — status derives from the folder, so the move is the
status change.

Also add `docs/work/discarded/` to `.prettierignore` beside the existing
`docs/work/completed/` entry (line 25). Without it, `pnpm prettify:check` starts
failing on the three frozen items.

Verify: `tcw validate`, `tcw work list --status discarded` shows exactly three,
`check()` reports no disagreement, `pnpm prettify:check` passes.

## Phase 7: Documentation and capability reconciliation

Documentation Sync triggers, all four expected to fire:

1. **`README.md`** [Public-API] — the lifecycle diagram (line 473), the
   `tcw work init` folder list (484), `list` behavior (505–508), `drop` (531),
   the web board description (268–276, 578), and the formatting-surface
   paragraph (237) which names completed work items.
2. **`docs/release-notes/upcoming.md`** [Public-API] — plain language: what
   `completed/` now means, discarding straight from backlog, the reduced gate,
   and a link to the migration guide.
3. **`docs/changelogs/upcoming.md`** [Any-Code-Change] — grouped
   Added/Changed/Fixed, with the commit range from `git rev-parse --short HEAD`.
   The `capabilities drift` false positive belongs under **Fixed**.
4. **`skills/tcw-work/SKILL.md`** [Skill-Driven-Component] — the opening status
   sentence, the lifecycle handshake's `complete` bullet, and quick-reference
   rows for `list`, `complete`, and `drop`. Also
   `references/lifecycle.md` (the status list and closeout boundary) and
   `references/task-lifecycle.md` (§ Closeout decisions).

Plus, not a tracked trigger but required by the spec:

5. **`docs/migration-guide-0.14.X-to-0.15.0.md`** — the move rule, `discarded`
   joining the reserved project-ID set, and re-pointing any `completed/<slug>`
   status-path locator. Filename assumes a minor bump; confirm at closeout.

Capability reconciliation:

- `work/discard-a-work-item` → `Supported`.
- `work/drop-a-work-item` → reword to its actual niche (erasing a mis-creation
  that should leave no record), so it no longer claims "won't be done".
- `work/complete-a-work-item`, `work/view-the-board`, `web/editing` → bodies
  updated to match shipped behavior.

## Verification

```sh
python -m pytest
pnpm prettify:check
pnpm typecheck
pnpm vitest run
tcw taxonomy check
tcw capabilities check
tcw validate
git diff --check
```

Record evidence in `outcome.md`, then stop for user verification. Do not
complete the item or cut a release without closeout decisions.

## Parallelization and dependencies

- Phase 1 gates everything; it defines the constants the rest import.
- Phases 2, 3, and 4 are independent of each other once phase 1 lands.
- Phase 5 depends only on phase 1 (the API behavior it asserts).
- Phase 6 must follow phase 1 and should precede phase 7 so docs describe the
  migrated tree.
- Phase 7 depends on all behavioral phases and needs the final commit range.

## Guardrails

- `resolution_status()` and `RESOLVED_STATUSES` live in the core model, not the
  adapter — both are expressible by any store (litmus test: a Jira store maps
  them to resolved-but-not-done). Folder mechanics stay in `fs.py`.
- One definition of the status/resolution rule, shared by `complete()` and
  `check()`.
- Do not "simplify" `capabilities/cli.py:210` into `RESOLVED_STATUSES`.
- Migration is one commit containing only `git mv`s and the `.prettierignore`
  line.
- Narrow lifecycle commits; leave unrelated working-tree changes unstaged.
