# Implementation outcome

Implemented configurable external per-project filesystem work stores while
preserving the owning project's canonical ID, lifecycle policy, hooks,
capabilities, and code-worktree repository — then, after CI rejected the first
pass twice, closed the remaining claim-race read window.

## Delivered (first pass)

- `FsWorkStore` now separates the owning node root, configured work root, and
  work-store Git root. Default, relative, absolute, and symlinked locations use
  the same factory; broken, malformed, non-store, and configured non-Git targets
  fail with `work.path` diagnostics.
- Work discovery, qualified references, recursion, validation, web access,
  staging, transitions, resolved-status ignores, and transition commits route
  through the configured store. Relative configured paths are re-anchored to a
  linked worktree's primary checkout.
- `tcw work init --path` and `tcw init --work-path` scaffold external stores,
  preserve existing work configuration, write target-relative ignore rules,
  and replace only an exactly pristine generated default scaffold.
- Validation rejects registered projects that resolve to one physical work
  root.
- Starts now record claimant identity and UTC time, publish claims with a
  single-winner private rename, report contention, support explicit takeover
  and interrupted-claim recovery, clear claim metadata when leaving active, and
  show claim metadata in CLI/API read surfaces.
- README, release notes, changelog, capability records, taxonomy, and the
  `tcw-work` skill/reference guidance were updated.

## Delivered (rework pass)

`rework.md` asked for three things, and its central instruction was to enumerate
the windows rather than discover them one CI run at a time.

### 1. The windows, enumerated

Every `_find` call site and every read that follows one was classified. `_find`
resolves a slug by scanning, so *any* code that touches the returned path can
have the folder moved out from under it by a competing claim.

| Site | Shape | Verdict |
| --- | --- | --- |
| `start()` claim lookup | `_find` → `os.replace` | Windows 1 & 2, already closed |
| `get()` → `_item_from_dir` | `_find` → read `state.yaml` | **Window 3 — closed here** |
| `query()` → `_item_from_dir` | `_item_dirs` → read `state.yaml` | Same window, same fix |
| `artifacts()` | `_find` → `is_file()` → `read_text()` | **Closed here** — the board's own window |
| `path()`, `locate()`, `artifact_locator()` | `_find` → pure path math | No window; nothing is opened |
| `_require_dir()`, `body_path()` | `_find` → return a path | No window here; the *caller's* read is the window |
| `_unique_slug()` | `_find` → existence only | No window |
| `_validation_resources()` | `_find` → `is_file()` filter | No window; consumers read later |
| `create()` / `edit()` parent lookup | `_find` → write path | Out of scope: not a claim path |
| `get_detail()` | `_find` → unguarded `read_text` | Open, tracked separately (below) |
| `_effect_transition()` | `_find` → move | Out of scope by `rework.md`; closed by its own item |

### 2. What a loser is told, decided once

`_item_from_dir` answers `None` when the folder went away mid-read. Two
conditions are needed, and the second is the one that matters:

- **The exception.** The narrow case — the folder went while a read was open.
- **A re-check of `state.yaml` after the read.** The wide case. `load_yaml`
  returns `{}` for an absent file and `_safe_yaml` tolerates a malformed one, so
  a folder already gone reads back as a perfectly *valid* item full of
  defaults — reporting its old status. That silent phantom is worse than the
  crash it would replace, and no exception handler catches it. This answers
  `rework.md`'s explicit question about `_safe_yaml`: its tolerance stays scoped
  to malformed *content*. A vanished file is not malformed, it means the item
  moved, and the honest answer is "not here" — made one level up, where the
  caller can act on it.

`rework.md` predicted the trap in the obvious local fix, and it was real: with
`get()` degrading to `None`, `start()`'s next line reports `no such work item`
to a claim loser — a worse lie than the crash, and a criterion 3 failure of its
own. So an empty read now looks for the claim before denying the item exists:
in `.claiming/` if the winner is mid-flight, and in a re-read of `get()` if it
published to `active/` while we were asking. Those are the only two places a
claim in progress can be, so a slug that misses all three probes really is
absent — and still says `no such work item`, verified below.

Every way of losing now ends in one place, `_lost_the_claim()`, rather than in
three near-copies that had to be found and fixed one at a time.

### 3. Criterion 2, made real

`test_repeated_claim_races_have_exactly_one_winner` runs the two-thread race 25
times over fresh items, asserting each round has exactly one winner, that the
item is in `active` and nowhere else, and that its claim metadata is visible.

**Its weakness is recorded rather than papered over:** it passes with and
without the fix on this machine. `rework.md` warned that a single-shot race
passed 1202 of 1203 local runs with a genuine bug present; repetition raises the
odds on a 2-core runner but does not manufacture evidence on a many-core laptop.
The tests that actually pin the defect are the three deterministic ones, which
force the gap between two calls because — as `rework.md` established — no
arrangement of files on disk reproduces it.

## Verification

- `python -m pytest -q`: **1216 passed** (1180 → 1216 across both passes).
- New tests: 4. Three fail against the previous code
  (`test_get_returns_none_when_the_folder_vanishes_mid_read`,
  `test_query_skips_an_item_that_vanishes_mid_scan`,
  `test_claim_loser_is_told_the_winner_not_no_such_work_item`), plus
  `test_board_artifact_flags_survive_a_concurrent_claim`, which reproduces the
  exact `FileNotFoundError` when run against the unfixed adapter.
- `pnpm run lint` (zero warnings), `pnpm run test` (**50 passed**, 11 files),
  `pnpm run test:e2e` (**13 passed**, every scenario executed).
- `tcw taxonomy check`, `tcw capabilities check`, `tcw validate`,
  `git diff --check`: all pass.
- **Manual operator check** (plan task 7), against a scratch work node — every
  path traceback-free, and the two meanings of "empty" distinguished:

  | Case | Message | Exit |
  | --- | --- | --- |
  | Winner | `started … → docs/work/active/…` | 0 |
  | Loser, item already active | `… is already claimed by one@example.com since 2026-08-12T13:22:55Z` | 1 |
  | Loser, winner mid-flight in `.claiming/` | `… has an interrupted claim; use --take-over --owner <identity>` | 1 |
  | Slug that genuinely does not exist | `no such work item: …` | 1 |
  | Board with a claim in flight | renders; the in-flight item is not listed | 0 |
  | Explicit takeover of the interrupted claim | `started … → docs/work/active/…` | 0 |

## What the plan and spec got wrong

- **The plan treated the claim protocol as a write problem.** Tasks 3 and 4
  specify the atomic move, the private claiming area, and the publication
  barrier in detail, and they were implemented correctly — both CI failures were
  in *reads* that happened to be adjacent to a claim, not in the claim itself.
  A protocol that moves folders makes every concurrent reader a participant;
  the plan has no task for that, which is why the windows were found by CI
  rather than by design.
- **Acceptance criterion 2 was unverifiable as written** at the time it was
  accepted. "Repeated stress races never expose…" was satisfied by a suite that
  ran the race once per session. It now runs 25 times, with its residual
  weakness stated above rather than hidden behind a green check.
- **`rework.md`'s release-impact note is stale.** It says the version files read
  `0.20.0` and the release should be re-tagged rather than re-cut. `v0.20.1` has
  since been cut and tagged, so this work is a fresh patch cut on top of it, not
  a re-tag.

## Follow-ups

- `get_detail()` (`fs.py:2809`) guards its `_find` result and then reads
  `state.yaml` unguarded — the same shape, on a web/API read path rather than a
  claim path. Left in place deliberately, tracked by the existing backlog item
  `2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`.
- `_effect_transition`'s equivalent was out of scope by `rework.md`'s own
  instruction and has since been closed by
  `2026-08-11-harden-effect-transition-against-a-lost-status-transition-race`.
  Its answer and this one converged on the same shape — degrade to a typed error
  the CLI already handles — so neither made the other a duplicate.
