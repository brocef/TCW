---
verdict: accepted
judges: 1
---

# Review round 1 — TCW-112

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `f2efe563`, `v4` with this item's commits
rebased onto it (`bbacb6a1..f2efe563`). The dispatching session checked the
findings against the repository before writing this round.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on the rebased branch at the same code, in
  two halves by folder: `2004 passed, 2 skipped` and `4549 passed,
  111 skipped`. `pnpm test` `200 passed`; `tsc --noEmit`, `pnpm lint`,
  `pnpm check:build` clean; the end-to-end suite `18 passed`.
- By the reviewer: the item's new and central test files, `1048 passed,
  2 skipped`; four `tests/serve` files, `127 passed`; fourteen more changed
  files, `375 passed, 10 skipped`; `tests/work` gates and drift, `66 passed`.
- By hand in scratch projects: drift's `unreviewed:` line (AC 32); `rm` of an
  override printing `now shows`; with `core` missing, `show`'s `partial:`
  line, `rm` of the override with no `now shows`, `taxonomy list` exit 7,
  `validate` exit 0 with both "could not check" suffixes; `--field Priority=`
  writing `Priority: null`; `extends add` exit 2; `capabilities.extends`
  refused in the project's own file and ignored in a parent's; `rm` of an
  inherited id-path exit 3; a source object with a newer `tcw-version`
  marking the override `partial`.
- The Design 8.1 sweep: only `docs/use-cases.md`, which is TCW-117's, still
  says `extends`. No git call added under `tcw/`; no private name in the
  change.
- `documentation-sync`: README, the guides, the taxonomy, capabilities and
  configure skills and the records describe the code; `docs/use-cases.md`
  and the skills' `meta.yaml` wording are deferred to TCW-117 within the
  spec's non-goals. Two visible changes were missing from the changelog
  entry and were added at review (`1840b6a4`): `--field K=` now writes
  `K: null` where it wrote an empty string, and a capability's field findings
  name its state file instead of its folder. A long unwrapped README line was
  rewrapped in the same commit.

## The dispatching session's questions

- The collapsed interim steps: about 95 removed test functions each test
  something the spec removes (`extends` and its writers, the opaque id, the
  `overrides:` pointer, ambiguity, the federation walk, `rm` refusing an
  inherited object, the null-pops rule); each changed outcome is required by
  the spec. No unrequested change in outcome was found.
- `origin`: a record read from another owner's store keeps that store's
  "local". The one reader, `tcw/capabilities/cli.py:137`, runs only on the
  active project's own `add` and `set` results, so it is right; Design 3.1
  says nothing on it.
- `--field K=` is read only by `tcw capabilities set`; plan Step 8 and Design
  4.2 name the null.
- `rm`'s referrer refusal keeps today's form, as Design 4.4 says; `reset`'s
  names full identifiers (AC 24).
- The four statements the documentation helper wrote from the spec (the
  `now shows` line, the `partial:` line, the 503, exit 1 on the removed key)
  match the code.
- Exit 7 for a source store that cannot open names the store's own message
  and never says "not on this machine"; TCW's own configuration errors are
  not caught there.

## Acceptance criteria

All 44 are met by named tests, AC 32 also by hand; AC 38 is the suite run
above. The reviewer's note that AC 32 lacked a test of its second half was
checked and rejected: `test_ac32_drift_names_an_override_that_never_set_status`
(`tests/test_overrides_by_path.py:1286`) sets only `Priority` on `cli/y` and
asserts its `unreviewed:` line.

No finding belonging to this change is open.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session:

- `rm`'s referrer message names bare id-paths while `reset`'s names full
  identifiers; TCW-114 rewords the refusals.
- A capability `rm` does not check `parent` among referrers, so removing a
  capability another names as its parent leaves a dangling reference; true
  before this item as well.
