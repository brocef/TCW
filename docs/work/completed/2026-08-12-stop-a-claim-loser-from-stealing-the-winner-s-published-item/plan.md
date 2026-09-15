# Implementation plan

1. Guard the claim source in `start()`: `_find` returning `None` *or* a folder
   outside `backlog` means the race was lost. Route both into
   `_lost_the_claim`. Verify with a deterministic test that publishes the
   winner between `start()`'s two lookups.
2. Re-walk in `_find` before raising `MultipleMatch`, bounded at five. Verify
   with a test that shows the item in two status folders on the first walk only,
   plus one that a genuine duplicate still raises.
3. Retry the walk in `_item_dirs` on `FileNotFoundError`, bounded at five.
   Verify with a test that fails the first walk.
4. Raise the stress test from two contenders to four — two never exposed the
   steal locally; four found it in roughly 1 round in 20.
5. Run the full pytest suite, `pnpm lint`/`test`, `tcw taxonomy check`,
   `tcw capabilities check`, `tcw validate`, and `git diff --check`.
6. Push and confirm **CI is green on every supported Python**. Two of these
   three defects have only ever appeared there.

## Documentation Sync

7. Update `docs/changelogs/v0.20.1.md` [Any-Code-Change] and
   `docs/release-notes/v0.20.1.md` [Public-API] — the fold into v0.20.1 is
   already in flight, so these entries join it rather than starting a new
   upcoming file. `README.md` and `skills/tcw-work/SKILL.md` are not expected to
   fire: no CLI surface, model, lifecycle, or guardrail change.

## Verification

The stress test is the probabilistic evidence and the three deterministic tests
are the real ones. Neither is sufficient alone: the deterministic tests cannot
prove the invariant holds under real scheduling, and the stress test passed 20
consecutive local runs at two contenders while the defect was present.
