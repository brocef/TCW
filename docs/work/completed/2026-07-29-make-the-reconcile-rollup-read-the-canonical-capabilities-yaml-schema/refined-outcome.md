# Refined outcome — Make the reconcile rollup read the canonical capabilities.yaml schema

**Verdict: accepted.** Verified in the coordinating session on 2026-07-30.
Subagent dispatch was unavailable (account session limit), so every stage ran
inline.

## Evidence, criterion by criterion

| # | Criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Canonical `new:`/`changed:` sidecar renders both paths, no `skipped` | met | `test_reconcile_surfaces_canonical_capability_deltas` |
| 2 | `added:` honored as an alias of `new:` | met | `test_reconcile_honors_added_alias` asserts `new a/b` |
| 3 | Legacy list renders exactly as before; existing test passes **unmodified** | met | `test_reconcile_surfaces_capability_deltas` untouched and green |
| 4 | Mapping with no recognized keys still yields `skipped`, without claiming "not a list" | met | `test_reconcile_tolerates_malformed_capabilities` untouched and green; wording now "has no new:/changed: entries" |
| 5 | Unparseable YAML yields an `unreadable` note; `reconcile` returns rather than raising | met | `test_reconcile_tolerates_unreadable_capabilities` |
| 6 | No second implementation of the mapping schema | met | Read of the finished function: `declared_capabilities` is the only `new:`/`changed:` parse in `recursion.py` |
| 7 | `pytest -q` green | met | `1130 passed in 156.43s` |
| 8 | Changelog `Fixed` entry; release note added | met | `docs/changelogs/upcoming.md` `## Fixed`; `docs/release-notes/upcoming.md` "Epic summaries now list the capabilities an item declares" |

`tests/test_recursion.py` went 23 → 26. The two pre-existing cases passing
without edits is the load-bearing evidence for criteria 3 and 4 — the plan named
editing them as a failure signal, and neither required it.

## Checks beyond the criteria

- **The real-data check is stronger than the criteria asked for.** 39 of 39
  canonical sidecars in this repo would have rendered as
  `capabilities.yaml present but not a list — skipped` under the old code. The
  defect's blast radius was total, not partial. Verified read-only by calling
  `_capability_deltas` directly rather than running `reconcile`, which writes
  into an epic's body — correct restraint, since the only epic here is completed.
- **Abstraction litmus test: passes, and the change improves the position.**
  `_capability_deltas` lives in the cross-node recursion layer above the abstract
  store, and it now consumes `declared_capabilities` from `tcw/store/base.py` —
  the shared, storage-agnostic reader — instead of hand-parsing the sidecar. One
  fewer schema reader outside the abstract spine.
- **The gate is genuinely untouched.** `capability_gate` still lets
  `SidecarError` propagate and fail closed; only the display surface swallows it.
  This asymmetry is deliberate, documented in the function's docstring, and is
  the right split: a rollup spanning an epic must not die on one child's broken
  file, while a completion gate must.
- **Harness compatibility: unaffected.** Pure library change.
- **Capabilities: no delta, confirmed against the ledger** — this changes how an
  existing capability behaves, not what a user can do. No sidecar for this item.
- **No documentation went stale.** Grep for `not a list` and `Capability deltas`
  across `README.md`, `skills/`, `commands/`, and `docs/capabilities/` returns
  nothing, so no document ever described the buggy behavior.

## Deferred follow-ups

None opened. Two things recorded rather than actioned:

- **Two sidecar schemas remain readable.** Unifying them is a migration with
  cross-node blast radius and the reported defect does not require it. The legacy
  branch is retained specifically because `_tasks_for` reads items out of child
  nodes — separate repositories this one cannot inspect — so "no producer here"
  is not evidence of "no producer".
- **Historical sidecars render pre-0.11 `file#heading` addresses** (e.g.
  `work#view-the-board`) alongside modern `namespace/path` ones, because
  `declared_capabilities` returns refs as authored. Cosmetic, out of scope, noted
  in `outcome.md` for whoever next reads a rollup over old items.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Commits
  `befc3d5`, `c4cf8d3`, `1cff54d`, plus the outcome commit.
- **Version:** none cut at closeout; folded into the single **minor** bump
  covering this seven-item batch, per the user's decision on 2026-07-30.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, `version offered` all satisfied.

  The sixth entry — *originating GitHub issue answered and closed* — **applies
  and is deliberately deferred, not missed.** This item resolves
  [GitHub #8](https://github.com/brocef/TCW/issues/8). The user decided on
  2026-07-30 that issues in this batch are answered only after the containing
  version is cut **and pushed**, so that closing an issue never tells a reporter
  a fix is available before it is installable. The issue remains open at
  completion by design; the closing comment is drafted and approved after the
  push.
