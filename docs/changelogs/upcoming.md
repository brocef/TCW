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
