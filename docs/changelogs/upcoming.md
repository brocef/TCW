# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Five capability declarations covering the cross-node recursion surface, which
  the standing ledger did not describe at all: `work/inspect-the-node-topology`,
  `work/coordinate-a-cross-node-epic`, `work/reconcile-an-epic-rollup`,
  `work/delegate-a-request-to-a-child-node`, and
  `work/escalate-a-request-to-the-parent-node`. Declared `Supported` at creation
  — they document behavior that already ships, so the usual `Missing` +
  `Planning doc` seeding would have misattributed it. `Subject` and `Feature`
  point at existing taxonomy entries (`node`, `work-item`,
  `connected-project-registry`, `work-inbox`); no taxonomy entry was minted.
  Documentation only — no file under `tcw/` changed.

### Work inbox intake

- `FsWorkStore._resolve_inbox_ref` resolves an inbox identifier in a fixed order:
  exact ref, then `<ref>.md`, then a unique `InboxEntry.title` from `inbox_list`.
  `inbox_show` and `inbox_accept` both route through it, so sibling commands take
  the same identifiers. Exact wins outright — a folder named `example` stays
  addressable as `example` with an `example.md` beside it. Ambiguity is reachable
  only at the title step and raises `ambiguous inbox entry: … matches …` rather
  than picking by iteration order; nothing is consumed.
- `inbox_accept` propagates a delegated `initiative` into the accepted item's
  `state.yaml` via `_inbox_initiative`, parsed before anything is created or
  consumed. Absent, null, or whitespace-only means no initiative and produces the
  same item shape as before (no key written); a structured value (list/dict/tuple/
  set) raises rather than being serialized into state. Only this one frontmatter
  key crosses from intake into model state.
- Extracted `FsWorkStore._frontmatter(content, label)` from `_plan_manifest`, which
  now calls it. Same behavior and messages for `plan.md`; the inbox parser is the
  second caller rather than a second implementation.
- `tcw work delegate`'s `child` argument help named a "child node path"; it
  resolves a canonical project ID (`registered_project_id` over `child_nodes`).
  Help string corrected — no behavior change. The prior tests could not catch it
  because `mk_node` derives the project ID from the directory name;
  `test_delegate_resolves_the_project_id_not_the_directory_name` breaks that
  coincidence.

### Stable reads across claims

- Split `FsWorkStore.get` into `_get_now` (one immediate probe) and a stabilizing
  `get`. `get` returns hits and evidence-free misses immediately, and only waits —
  50 × 10 ms, the existing publication window — when `_claiming_dirs(slug)` proves
  that exact slug is mid-flight. An abandoned claim raises the documented
  interrupted-claim `ValueError`. `.claiming/` is not exposed through `WorkStore`;
  the abstract contract is still "the current item or None", with the adapter free
  to settle a transient move first.
- `_get_now` re-probes once when `_find` returns a folder that `_item_from_dir`
  then finds gone. That window is *not* the claim window — an ordinary `git mv`
  transition opens it and there is no `.claiming/` evidence to key on — so it is
  closed in the probe rather than in `get`.
- Three call sites deliberately keep the immediate probe, each because its job is
  the unstable state: `_lost_the_claim` (else each of its 50 iterations nests
  another 500 ms wait), `start`'s take-over probe (the branch exists for the state
  `get` now raises on, so `--take-over` would have become unreachable), and
  `_effect_transition`'s lost-race message (which wants the raw state to describe).
- `WorkStore.unresolved_blockers` catches an adapter's refusal to settle and
  reports that blocker as a blocker. Raising there would answer "why can't I start
  B?" with an error about A. Storage-neutral: any adapter may fail to resolve a
  reference.
- `get_detail` is now a whole-snapshot read: `_detail_snapshot` raises the private
  `_Moved` (or a `FileNotFoundError` from a path inside the item) and `get_detail`
  restarts, bounded at 5 attempts. All-or-nothing on purpose — pairing the first
  item with files re-read from its new status would hand out revisions that never
  coexisted. Permission errors and malformed content still surface.
- `test_get_detail_lost_at_find_returns_none` is superseded by
  `test_get_detail_retries_a_transient_loss_at_find`: `None` was the honest answer
  only while nothing looked again. `test_get_detail_gives_up_when_the_item_never_settles`
  pins the bound.
- Sibling sweep over every `_find` call site in `tcw/store`, `tcw/serve`, `tcw/work`
  found no further vulnerable reader. `artifacts()` and `_validation_resources`
  already carry explicit vanish guards; the rest are transition/write logic that is
  conflict-aware by contract, or single path lookups that read nothing.
