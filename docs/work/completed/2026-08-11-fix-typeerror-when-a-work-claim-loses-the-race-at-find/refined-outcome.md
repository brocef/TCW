# Refined outcome — Fix TypeError when a work claim loses the race at _find

## Decision

**Accepted** by the requester on 2026-08-11, with the fix folded into the
already-cut, unpushed `v0.20.0`.

## Evidence

Suite: **1204 passed** locally.

| # | Criterion | Verdict |
| --- | --- | --- |
| 1 | `AlreadyClaimed`, not `TypeError`, when `_find` returns `None` | **deviates, accepted** — see below |
| 2 | Deterministic test that fails against unfixed code | met — reproduced `TypeError: replace: src should be string, bytes or os.PathLike, not NoneType` at `fs.py:2025`, byte-identical to the CI failure |
| 3 | The threaded race test passes | met |
| 4 | Suite green locally, both CI legs green | locally met; **CI half outstanding** at closeout |

### Criterion 1 — the accepted deviation

The test asserts the recovery path is *reached* (a `ValueError: … interrupted
claim`) rather than which error ends it. Asserting `AlreadyClaimed` would require
faking a second timing — whether the competitor finishes claiming during the
retry loop — and that outcome is already covered by the threaded test which
caught the bug. The property that matters is that `os.replace` is never handed
`None`.

### What counts as evidence here

The deterministic test is the whole case. The threaded test passing 30/30 after
the fix is **not** evidence: it passed 1202/1203 times before the fix too. A
green run of a flaky test proves nothing, which is why the deterministic test was
written first.

## Capability reconciliation

None. `work/start-a-work-item` already promised an atomic claim and a clear
message to the loser; this makes an existing promise true on a timing it missed.
No ledger delta, no `capabilities.yaml`.

## Closeout choices

- **Route:** committed directly to `main`, consistent with the rest of the
  session.
- **Documentation:** both predicted triggers fired. Entries went into
  `docs/changelogs/v0.20.0.md` and `docs/release-notes/v0.20.0.md` rather than
  the `upcoming.md` files the plan named, because of the fold; `upcoming.md` was
  restored to headers only.
- **Version:** folded into `v0.20.0` by **moving the tag forward**, not by
  rewriting the release commit. The distinction was load-bearing: the `v0.20.0`
  *tag* was never pushed, but the commit it pointed at (`e6ba90a`) is
  `origin/main`'s head. Amending that commit would have required force-pushing a
  public branch; moving an unpublished tag onto a later commit rewrites nothing.
  `unpushed-version.sh` returned NOT-FOLDABLE because it tests whether the
  *tagged commit* is public — the right proxy for its own question, but not the
  question being asked here.

## Deferred follow-ups

- `_effect_transition` (`fs.py:2726`) — same `_find` → `_mv(None)` shape on
  `submit`/`complete`/`rework`, a path the claiming mechanism does not cover.
  Filed as its own backlog item at the requester's direction rather than left
  buried in a completed item's request document.

## Notes

- No post-mortem offered. The lifecycle behaved correctly here: CI caught the
  defect on its first run, which is what it was built for. The interesting
  lesson — that the plan's proposed test approach was wrong twice before it was
  right — is recorded in `outcome.md` rather than treated as a process failure.
