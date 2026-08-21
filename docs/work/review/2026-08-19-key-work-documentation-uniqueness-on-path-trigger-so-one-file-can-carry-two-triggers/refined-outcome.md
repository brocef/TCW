# Refined outcome — key `work.documentation` uniqueness on (path, trigger)

## Decision

**Accepted.** Brian approved closeout on 2026-08-21, after the `verify`-stage
review round. Resolution: `done`.

## Evidence

All nine acceptance criteria met, every number from a command run during this
item:

| # | Criterion | Evidence |
| --- | --- | --- |
| 1 | Pair accepted — 2 entries, 0 problems | `test_one_path_may_carry_two_triggers` |
| 2 | Same path *and* trigger — 1 entry, 1 problem naming both | `test_the_same_path_and_trigger_twice_is_still_a_duplicate` |
| 3 | `[A,B,C]` reports entry 2 → entry 0, keeps `[A,B]` | `test_a_duplicate_names_the_entry_that_first_declared_the_pair`, and the scratch-node run |
| 4 | `test_a_duplicate_path_is_reported` unchanged, passing | unmodified in the diff; green |
| 5 | Suite green | `1955 passed in 388.00s`, exit 0, final tree at `713e0a2` |
| 6 | Reporter's pair passes `tcw validate` | `validate OK`, exit 0 |
| 7 | Two rows, two JSON objects | `tcw work docs` / `--json` on the scratch node |
| 8 | This repo's `tcw work docs` byte-identical | `diff` empty |
| 9 | README no longer says a bare "duplicate path" | `760f9a8` |

**Review round.** `codex exec --sandbox read-only` over `e4c5b22..760f9a8`,
prompted adversarially at the duplicate guard, downstream path-keying consumers,
the output contract, documentation accuracy, test quality, and the abstraction
litmus test. One finding, Low, and it was against the *record* rather than the
code: `outcome.md` justified skipping a post-docs suite re-run with a false
claim that no test reads `README.md` or `skills/**/references/*.md`.
`tests/test_documentation_sync_wiring.py:27-33,127-135` does both. Reproduced
before accepting, then fixed properly — that suite green (`7 passed`) and the
whole suite re-run on the final tree — and `outcome.md` amended in `a67bb75` to
record the bad reasoning rather than bury it. The code itself drew no findings,
and none landed in the "separate item" bucket.

## Capability ledger

Reconciled: `tcw capabilities drift` → **no capability drift**. This item
declared no ledger delta and wrote no records, as `spec.md` planned.

## Closeout choices

- **Merge route:** none needed — every commit landed directly on `main`, no
  branch and no worktree.
- **Documentation:** all four entries fired and all four were answered in
  `760f9a8` — `README.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, and
  `skills/documentation-sync/references/setup.md`.
  `skills/tcw-work/references/commands.md` and the 0.21→1.0.0 migration guide
  were checked and correctly left alone.
- **Version:** `scripts/unpushed-version.sh` → `STATUS: NOT-FOLDABLE`, exit 1 —
  v1.0.1's tag is present on `origin`, so folding into it is off the table. The
  changelog and release-note entries sit in `upcoming.md`; the bump is offered
  to Brian after this item closes.
- **GitHub issue:** #21 is the origin and is answered by this change; the fix
  commit `e22af98` carries `Closes #21`.

## Deferred follow-ups

- **The documentation capability records were never written.** The item that
  introduced `work.documentation`
  (`2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-…`) planned
  two records in its `spec.md:5-10` — *Declare which documents track which
  changes* and *Read the documentation gate for a change* — and a
  case-insensitive sweep of `docs/capabilities/` finds neither, yet
  `tcw capabilities drift` reports clean both then (`refined-outcome.md:65`) and
  now. Two questions for its own item: write the missing records, and work out
  whether `drift` should have caught their absence. Out of scope here — this
  item changed one dict key and declared no ledger delta.

## Notes

- The reporter can drop the `README.md#invalid-constructions` workaround once
  this ships; nothing in this repo depends on their doing so.
