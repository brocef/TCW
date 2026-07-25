# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

<changes starting-hash="0f7acd7" ending-hash="3984829">

### Added

- `discarded` work status (`WORK_STATUSES`), plus `RESOLVED_STATUSES` and
  `resolution_status(resolution)` in `tcw/store/base.py`. The resolution selects the
  terminal status: `done` → `completed`, everything else → `discarded`.
  `resolution_status` raises on an unknown resolution rather than defaulting, so
  `check()` cannot read a corrupt-resolution item as consistent.
- `LEGAL_TRANSITIONS` gains `("active", "discarded")` and `("backlog", "discarded")`.
  The latter removes the throwaway `backlog → active → completed` round-trip
  previously required to abandon a backlog item.
- `FsWorkStore.check()` status/resolution consistency detector: terminal status with a
  missing or invalid resolution, a resolution disagreeing with the item's status, and a
  non-terminal status carrying a resolution. `complete()` is the only writer of a
  terminal status, so this detects externally-corrupted state (a hand-run `mv`, a bad
  merge), not a second source of truth.
- `docs/migration-guide-0.14.X-to-0.15.0.md`.

### Changed

- Split the overloaded `status != "completed"` idiom. Four sites meant _resolved_ and
  now use `RESOLVED_STATUSES` — `unresolved_blockers`, `epic_completable`,
  `complete()`'s open-children check (all `tcw/store/base.py`), and the reconcile
  rollup `_ready()` (`tcw/work/recursion.py`). One site means _shipped_ and
  deliberately still reads `completed` alone: `_shipped_but_missing`
  (`tcw/capabilities/cli.py`), now commented to prevent a future "fix".
- `tcw work complete` branches on the resolution (`tcw/work/cli.py`): a discard skips
  the Definition-of-Done checklist (records `dod: []`), degrades the capability gate to
  a non-blocking warning, and skips `merge_worktree`. `remove_worktree` is called with
  `branch=None` so the worktree is torn down but the unmerged branch survives.
  `--confirm` is still required.
- `tcw work list` hides `discarded` alongside `completed`; `--all` and
  `--status discarded` reveal it. `--status` choices derive from `WORK_STATUSES`.
- Web client: `WORK_STATUSES` extended in `ui/app.tsx` and `ui/content-views.tsx`,
  `model/tree.ts` sorts `discarded` last, the status filter defaults it off, and the
  complete modal branches on resolution (drops the DoD list, swaps the reconciliation
  reminder for a discard warning, relabels the action `Discard`). The HTTP API needed
  no change — it delegates destination choice to the model.
- Unresolved blockers no longer gate a discard (`complete()` checks them only when
  `dest == "completed"`). The epic open-children gate still applies to both routes,
  since an initiative child cannot start until its epic is active.
- Web `WORK_STATUSES` deduplicated into `model/types.ts`; `model/tree.ts` exports
  `WORK_STATUS_ORDER` (display precedence, a separate concern) and `tree.test.ts`
  guards that it covers every canonical status. The sort's unknown-status fallback
  is now `WORK_STATUS_ORDER.size` rather than a hard-coded `3`, which stopped
  meaning "after everything" once `discarded` took index 3.
- `.prettierignore` excludes `docs/work/discarded/` beside `docs/work/completed/`.
- Whole-repo `pnpm prettify` pass; `prettify:check` is clean for the first time.
- `RESERVED_PROJECT_IDS` gains `discarded`, since it derives from `WORK_STATUSES`.

### Fixed

- `tcw serve` shipped a stale prebuilt bundle: `tcw/serve/dist` was not regenerated
  after the client source changed, so none of the web behavior above reached a real
  browser. Caught by `pnpm check:build` (`23630db`).
- The complete modal rendered its discard form by default, because `shipping` was
  `resolution === "done"` and the dialog opens with an unset resolution — titling it
  "Close Work Item" with a "Discard" button before any choice was made. An unset
  resolution now counts as shipping (`3984829`).
- Backlog items offered only Start and Drop, leaving `backlog → discarded`
  unreachable in the web app and pushing users toward a hard delete. They now offer
  Start · Discard · Drop, with Discard opening the modal in discard-only mode
  (`done` omitted, since it is not legal from backlog). `TLifecycleAction` gains
  `discard` as a UI intent; the API action stays `complete` (`3984829`).

- `tcw capabilities drift` no longer reports `shipped-missing` for a capability whose
  planning doc was closed as `wontfix`/`duplicate`/`superseded`. Those items previously
  landed in `completed/` and tripped a check that means "did this ship?".

### Internal

- Migrated this repo's three non-`done` closures into `docs/work/discarded/` (`43b27a8`).
  `state.yaml` is unedited — status derives from the folder, so the move is the change.

</changes>

<changes starting-hash="d163961" ending-hash="b8e3895">

### Added

- `documentation-sync` skill (`skills/documentation-sync/`) — a TCW-owned port of the
  documentation-sync trigger-evaluation workflow: `SKILL.md` router plus
  `references/release-notes-and-changelogs.md` and `references/setup.md`. Trigger
  vocabulary (`Public-API`, `Public-{Name}-API`, `Any-Code-Change`, `Only-Breaking`) is
  a base set projects may extend with named triggers (e.g. TCW's `Skill-Driven-Component`).
- `tests/test_documentation_sync_wiring.py` — guards that the skill files exist, no
  `skill-cefailures` reference survives, and the tcw-work lifecycle invokes the skill.

### Changed

- Documentation-sync is now sourced from TCW itself instead of the external
  `skill-cefailures:documentation-sync` skill. `AGENTS.md` `## Documentation Sync`
  directive and the `tcw-work` lifecycle references (`task-lifecycle.md`,
  `epic-lifecycle.md`) now invoke the TCW-owned `documentation-sync` skill at the plan
  and completion gates.
- Skill count and framing updated in `README.md` (`five` → `six`; the CLI-driver framing
  now admits one cross-cutting process skill) and `.codex-plugin/plugin.json`
  (`longDescription` / `shortDescription`); `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` framing softened for consistency.
- The absorbed skill defers version-cutting to the project's own process (TCW's
  `scripts/cut_version.py`) rather than hardcoding a path, and replaces the FOLLOWUPS.md
  pattern with `tcw work` backlog items.

</changes>
