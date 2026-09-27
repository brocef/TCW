# Spec: resolve capabilities.yaml sidecar paths while an item is still being worked

## Capability changes

None to the ledger: `tcw validate` reports more.

## Problem

`capability_gate` (`tcw/work/recursion.py:50-152`) routes each declared path
(`route_capability_path`, `:188-237`) and reports unresolvable ones — but only at
`complete`. `tcw validate` and `tcw capabilities check` never look at sidecars.
Routing sends a path whose first segment is not an extended project or a
declared child to the node's own ledger (rule 3, `:233`), so `shared/x` is not a
routing failure: it is a local path that does not resolve.

## Goals

`tcw validate`, for each work item in `backlog`, `active` or `review` (never
`completed` or `discarded`), reports as `<item folder>/capabilities.yaml:<line>:
<problem>`:

1. an unreadable sidecar;
2. a path that cannot be routed, or is ambiguous, in any of those statuses;
3. a `changed:` path that does not resolve, in any of those statuses;
4. a `new:` path that does not resolve, in `active` or `review` only — the
   capabilities skill seeds a new capability (`Missing`) at planning, so by
   implementation it exists; in `backlog` the plan may not have run yet;
5. a `removed:` path naming an inherited capability (it can never be removed).

Not reported mid-work: `new` still `Missing`, `removed` still resolving — both
normal until completion. A ledger or registry that will not open is reported by
validate's other checks, once, not per path.

## Non-goals

- Resolving `shared/` to a unique connected project id (separate item).
- `tcw capabilities check` (ledger-only, unchanged).
- Line numbers beyond "the first line naming the path".

## Design

`capability_gate(st, item, *, in_progress=False)`: one per-path routine, the
in-progress policy switching off the completion-only checks. A pass in
`tcw/validate.py` (whole-node runs, and a work-item target) calls it for each
open item and prefixes the item's sidecar location and line.

## Acceptance criteria

1. An active item with `new: [shared/x]` (no such capability) → `tcw validate`
   reports `…/capabilities.yaml:<n>: shared/x: declared (new) but does not
   resolve`, exit 1.
2. The same in `backlog` → nothing for that path; `changed: [shared/x]` in
   backlog → reported.
3. A `new:` path that exists as `Missing`, and a `removed:` path that still
   resolves, in an active item → nothing.
4. A completed item with a bad path → nothing.
5. An unreadable sidecar in an active item → reported.
6. `capability_gate` at `complete` behaves as before (existing tests).
7. Full suite passes.

## Risks

- This repository runs `tcw validate` as a `pre` hook on `complete`, so one open
  item with a bad sidecar blocks completing any item until fixed. The same is
  already true of every other validate problem; the message names the file.

## Notes

- Advisors: Codex and Opus agreed on validate as the home, review included,
  shorthand out. They split on unresolved `new` paths; see `outcome.md`.
