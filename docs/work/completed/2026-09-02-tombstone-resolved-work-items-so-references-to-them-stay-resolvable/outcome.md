# Outcome — Tombstone resolved work items so references to them stay resolvable

Ten plan tasks, ten commits plus three the tooling made itself. No task was
dropped, and one was added that the plan did not have.

## What shipped

| # | Task | Commit |
| --- | --- | --- |
| 1 | `Tombstone` + abstract `WorkStore.tombstone()`; `FsWorkStore` reads `graveyard.yaml` | `ebfc3c1` |
| 2 | `complete`/`discard` record it via `_effect_transition`; refuse rather than absorb | `d171853` |
| 3 | `tcw work tombstone add`, plus `WorkStore.record_tombstone()` | `22d51a4` |
| 4 | `refs.py` consults the tombstone; `ResolveResult.archived`/`.resolution` | `6e7d1ba` |
| 5 | `tcw validate` reproducibility tests | `4d32663` |
| 6 | `_unique_slug` consults the graveyard | `c038d8b` |
| 7 | `/api/resolve` reports `reason: "archived"` | `688bc87` |
| 8 | Backfill this repository | `a570726`, `2a5f6ad` (written by the command) |
| — | The CI item, unblocked and completed | `7011e44` (written by `tcw work complete`) |
| 9 | Capability ledger | `79e50af` |
| 10 | Documentation sync | `9550b9c` |

## Tests

Full suite, in a venv without a pre-installed setuptools so the wheel test is
real:

```
2210 passed, 4 deselected in 422.06s (0:07:02)
```

The four deselected are this container's root-only failures, unchanged by this
work and green on CI: three assert a `PermissionError` that cannot raise under
root, one is the process-group flake characterised in the previous item.

```
$ tcw validate            → validate OK
$ tcw capabilities check  → capabilities OK
$ tcw capabilities drift  → no capability drift
```

**The end-to-end demonstration** is task 8. `tcw validate` in this repository
went from `4 problem(s)` to `validate OK`, and
`tcw work complete 2026-09-02-restore-the-ci-test-suite-to-green` — refused all
session by its own `pre` hook — succeeded, printing `validate OK` from that hook
on the way through. The item recorded itself in the graveyard as it went.

Every test was watched fail before the code that makes it pass. Two were
checked by mutation rather than by ordering, because they passed on first run:
the fresh-clone validate test (red when the resolver's tombstone consultation is
removed) and the tolerant-read tests — see Corrections.

## Corrections

### The spec was wrong that this needs no new capability

`tcw work tombstone add` is a distinct thing a user can do, covered by no
existing entry, so folding it into completion's wording would have hidden a
whole command from the ledger. Added `work/record-a-tombstone-for-resolved-work`
(cap-a458b8), Supported, with the item as its Planning doc. The spec's four
amendments stand as planned. The item's `capabilities.yaml` records one `new:`
and four `changed:`.

### The plan named one abstract method; two were needed

`tombstone()` reads. Nothing wrote, and the CLI cannot compose store paths, so
`record_tombstone()` joined it. It passes the litmus test on the same argument:
an adapter whose resolved items stay retrievable can treat it as a no-op.

### A test that passed for the wrong reason

`test_an_entry_missing_its_fields_still_answers_that_the_slug_existed` used
`slug: {}`, which parses to an *empty mapping* — still a `dict`, so the
non-mapping branch it was meant to cover never ran, and a mutation removing that
branch left it green. Replaced with `slug:` (parses to `None`), which is both
the shape a hand-edit actually produces and one that fails under the mutation.

### Task 7 needed no client change, and the plan implied one

The SPA's unrecognized-reason branch already neutralizes the anchor and shows
`detail`, which is the specified rendering. Sending `reason: "archived"` with a
`detail` gets it right on a client that knows nothing about archived work, so
`web/` is untouched and no bundle rebuild was needed. A dedicated affordance —
the off-board badge treatment — remains available later.

### `refs.py` recorded a claim that stopped being true

Its docstring said it added "no new store-interface method — litmus-clean".
Corrected in place with the reason: `get()` alone cannot tell resolved work from
a typo, because a store whose resolved items leave it answers `None` to both.

### A plan detail that was wrong about setup, not design

The plan's task 2 assumed the backlog-epic route could be reached with a
*completed* child. It cannot: an initiative child refuses to `start` until its
epic is `active`, and an active epic no longer takes the backlog route. The test
discards the child straight from `backlog` instead — still a resolved child, so
the epic is completable, and the route under test is preserved.

## Verification

The plan's five by-hand items, discharged:

1. **The prime directive, as review.** `WorkStore.tombstone` and
   `record_tombstone` mention no file, path, commit, or git — only ids,
   resolutions and dates.
2. **Codex parity.** Everything is in the `tcw` CLI: the recording rides the
   transition, and the backfill is a plain subcommand. Nothing depends on a hook
   or injected context.
3. **The real end-to-end.** Task 8, above.
4. **CI on both legs.** Not settled here — only the runner can.
5. **Nothing can hide the graveyard.** Checked on a scratch node with
   `docs/work/graveyard.yaml` gitignored: `_warn_hidden` already fires with the
   remedy — *"a .gitignore rule hides docs/work/graveyard.yaml; it is on disk but
   git will not record it. Remove the rule, or run `git add -f` on it."* It warns
   and proceeds rather than refusing, which is that function's stated convention
   for this whole class. Loud, not silent, so the tracked-unconditionally
   decision is enforced in practice.

## Notes

- `SKILL.md` is deliberately unchanged. It is a thin router; the recording
  belongs in `references/transitions.md` and the command in
  `references/commands.md`, both of which it already points to.
- Follow-up worth its own item, not filed: `unresolved_blockers` still fails open
  on any slug it cannot resolve, so a **misspelled** blocker silently stops
  blocking. The tombstone now makes that distinguishable, but acting on it
  changes when transitions refuse, which the spec ruled out of scope.
- Also unfiled: "tombstone" and "graveyard" are now domain nouns and arguably
  belong in the registered Vocabulary. The new capability uses existing subjects
  (`work-item`, `reference`) rather than inventing an unregistered term.
