# Refined outcome: accepted after fourth adversarial review

## Decision

Accepted under the user's final-round stopping rule: fix findings that belong to
this subject, file work requiring a different mechanism, and close the item.

Both primary fixes withstand the requested adversarial checks. The supersession
guard drops stale responses before any DOM mutation without disabling the
same-dependency live-DOM re-query. The work-reference check rejects absent items
without changing `resolve_qualified_work_ref` or server routing, preserves
completed/discarded items, and reports the existing qualified-reference cause.

## Evidence

- Removing only `if (superseded) return` makes the stale-first regression fail
  because the replacement anchor becomes `tcw-inert`.
- Removing only the `store.get(bare)` existence block makes both new resolver
  tests fail with `ResolveResult(ok=True, ...)`.
- `python -m pytest -q`: 1961 passed in 476.87 seconds.
- `pnpm test`: 61 passed in 11 files.
- TypeScript, ESLint, committed-bundle parity, focused Prettier, capability,
  taxonomy, recursive validation, and diff-integrity gates all exit cleanly.

## Findings and disposition

Belongs to this subject and fixed: stale lifecycle claims about the badge guard,
capability delta, and `_resolve_work` helper; the two declared capability bodies
are reconciled with the shipped behavior. Commits: `cb7173a`, `c398eea`.

Needs a different mechanism and filed separately: repeated strict work-reference
lookups rescan the work tree, producing O(references x items) cost. Backlog item:
`2026-08-25-avoid-rescanning-work-items-for-every-tcw-work-reference`, committed
as `8eab955`.

The two defects previously absorbed by this item are absent from
`docs/work/inbox/`; their implementation and evidence remain in `outcome.md`.

## Closeout

The public README, release notes, developer changelog, lifecycle artifacts, and
capability ledger describe the code that shipped. No skill-driven component
documentation trigger fired. No version cut was requested; the current version
and tags remain unchanged, with the applicable upcoming changelog files already
updated.
