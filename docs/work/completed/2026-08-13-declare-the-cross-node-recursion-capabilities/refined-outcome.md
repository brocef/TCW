# Refined outcome — Declare the cross-node recursion capabilities

**Decision: accepted.** Approved by the user on 2026-08-13, closing it alongside
the three bug fixes it shares an unpublished version with.

## Evidence at acceptance

Implemented directly on `main`; `032adf6` and `7b23dd4` are ancestors of `HEAD`,
no branch or worktree remains, and v0.21.1 is still local — tag not on `origin`,
87 commits ahead — so the ledger and the behavior it describes publish together.

All eight acceptance criteria re-checked on `main`:

| Criterion | Result |
| --- | --- |
| 1-2. Five paths, `Supported`, Subject/Feature as specced | `tcw capabilities check` → `capabilities OK` |
| 3. 65 capabilities, 28 under `work/` | both exact |
| 4. `delegate` body says canonical project ID | present, and `--help` now agrees (below) |
| 5-6. No existing capability and no `tcw/` file modified | `git show --stat 032adf6` — both empty |
| 7. Every `tcw://` link resolves | `tcw validate` → `validate OK` |
| 8. Suite + all checks | 1294 passed; `taxonomy check`, `capabilities check`, `drift`, `validate` all clean |

## Two corrections made at acceptance

The item's own outcome flagged the ledger as the honest source where the tool
disagreed with it. Both disagreements resolved during this review, and one cut the
other way.

**The `delegate --help` disagreement is gone.** `outcome.md` recorded, as
deliberate, that the ledger said "canonical project ID" while `--help` said
"child node path". The sibling item
`2026-08-12-fix-work-inbox-accept-s-entry-resolution-and-initiative-stamp` fixed
the string (`f25e048`) in this same unpublished version, exactly as the finding
asked. Nothing ships with the two out of step.

**The rollup capability had two claims the reconcile fix falsified**, and
`capabilities drift` cannot see them — it checks structure and reference
resolution, not prose. Corrected in `9e5de5d` after reading `reconcile` in
`tcw/work/recursion.py:195-230`:

- *"re-running produces no commit and no churn"* — the `changed or auto_completed`
  guard was removed by
  `2026-08-13-report-a-refused-reconcile-commit-as-a-cli-error-not-a-traceback`,
  because it broke that item's own documented recovery. An unchanged rollup with
  other work-store changes already staged now does commit.
- *"unrelated staged changes are left alone"* — true only outside the work store.
  The pathspec is `store.root` relative to the store's git root, so already-staged
  work-store changes ride along.

The body now states both precisely and adds the refused-commit reporting the
sibling item introduced, which closes that item's "link the two at the next drift
review" follow-up here rather than deferring it again.

## Capability reconciliation

`capabilities.yaml` declares five `new:` entries, all `Supported`. This is the
item's entire product, not a side effect. `tcw capabilities drift` clean after the
correction.

## Closeout

- **Route: direct to `main`.** No branch to merge.
- Documentation sync was evaluated per-entry in `outcome.md`; the three skips
  (`README.md`, release notes, `SKILL.md`) hold — this adds no behavior and no CLI
  surface. The changelog entry shipped.
- Version: folds into the unpublished **v0.21.1** with the three bug fixes. No new
  cut offered, since that tag is still local.

## Follow-ups

- **The real lesson, unfiled:** a capability body can be falsified by a code change
  in a sibling item and every automated check still passes. `drift` reads structure;
  prose has no guard. Two of five bodies here made claims about commit behavior, so
  the exposure is concentrated in the ledger's precise-mechanism sentences rather
  than spread evenly.
- **Out of scope and still open**, carried from `outcome.md`: auditing the rest of
  the ledger for further gaps. This item covered only the area that was found.
