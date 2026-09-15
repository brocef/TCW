# Plan — The claiming lookup globs with an unescaped slug

Two lines of production code. The work is in the tests, because the defect is
destructive and the proof has to be that the item survives.

## Tasks

### Task 1 — failing tests

Modifies `tests/test_external_work_store.py` only, which already owns this area:
`:377` tests `_claiming_dirs` refusing a shorter slug, and `:1023` has a helper
that moves an item into `.claiming/` the way `start` does. Use them rather than
writing new scaffolding.

Four cases, covering spec criteria 1 to 3 and 5:

1. **The destructive one.** One interrupted claim for `2026-01-01-axxxb-thing`;
   `start("2026-01-01-axxxb-th*g", owner=…, take_over=True)` must raise
   `no recoverable interrupted claim`. Then assert the aftermath, which is the
   real content: the claim directory is still in `.claiming`, `active/` is empty
   apart from `.gitkeep`, and the victim's `state.yaml` still names its original
   owner. Asserting only the exception would pass against code that raises
   *after* moving the item, which is close to what happens today.
2. The same wildcard without `--take-over` raises promptly and the message does
   **not** contain `interrupted claim`. Today it stalls and does.
3. A claim whose slug literally contains `*` is still found by `_claiming_dirs`
   with that exact slug. This is the criterion that proves recovery did not
   narrow, and it is the one a careless escape would break.
4. `_claiming_dirs` returns `[]` on a store with no `.claiming` directory. Guards
   the invariant the previous item documented, against a future rewrite to
   `iterdir`.

**Proves it:** cases 1 and 2 fail before Task 2. Read the failures: case 1 must
fail on the *aftermath* assertions, not only on the missing exception, or the
test is not testing what it claims.

### Task 2 — escape the slug

Modifies `tcw/store/fs.py` only, in `_claiming_dirs`:

```python
return sorted((self.root / ".claiming").glob(
    glob.escape(slug) + "-" + "[0-9a-f]" * 32))
```

The suffix is concatenated after the escape so it stays a pattern of ours. Check
`glob` is imported at module level; add the import if not.

Extend the docstring: it already warns that a loose `-*` glob would let a claim
on a longer slug answer for a shorter one, and the same hole was open through
`*`, `?` and `[` in the caller's slug. Name `glob.escape` and say the suffix is
deliberately outside it.

**Proves it:** Task 1 cases 1 and 2 go green, 3 and 4 stay green, and
`tests/test_external_work_store.py` passes in full.

### Task 3 — derive the take-over path from what was found

Modifies `tcw/store/fs.py` only, in the take-over branch (`:3557-3573`).

Today `dst` and `src` are composed from the caller's `slug`. Take the slug from
the claim directory that was actually found:

```python
claimed = interrupted[0].name[:-33]        # strip "-" + 32 hex
```

and use `claimed` for `dst`, `src`, `git_stage`, `_commit_transition` and the
final `_require`. Do **not** reassign the `slug` parameter; a separate name keeps
the two meanings distinguishable — what was asked for, and what was found.

Redundant once Task 2 lands, and that is the point: it makes the invariant local
so a future change to the lookup cannot silently reintroduce a mismatch between
the path searched and the path published.

**Proves it:** the suite stays green, and the `-33` arithmetic is checked against
the construction site at `:3627`, `f"{slug}-{uuid4().hex}"` — 32 hex characters
plus one hyphen.

### Task 4 — the combined review pass

Changes nothing. This repository's rule is that when several changes ship
together and touch the same file, the combined difference is reviewed as well,
because the highest-value finding in one batch was an interaction reachable only
once two items had both landed.

This item and `2026-08-20-docs-work-claiming-is-created-by-every-start-and-never-removed`
both touch claiming, and their interaction is already known: that item documented
`.claiming` absent-or-empty as one state because `Path.glob` is blind to the
difference, and this item's rejected scan-based design would have broken it.
Review `git diff` from before the first of the two, as one change.

## Documentation Sync

Evaluated against every entry `tcw work docs` reports.

- **`README.md` — [Public-API].** Does **not** fire. No CLI surface changes; a
  command stops destroying data when misused.
- **`docs/release-notes/upcoming.md` — [Public-API].** **Fires.** A user could
  lose a work item to a typo. That must be said plainly, including how to
  recognize a node it already happened on: an item missing from the board and a
  directory in `active/` whose name contains a metacharacter.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change].** **Fires.** `Fixed`.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component].** Does **not**
  fire. No skill documents `.claiming` or the claim lookup — verified by grep,
  not assumed.

## Verification

What the suite cannot check:

- **That no other caller globs with unvalidated input.** `_claiming_dirs` was
  found by review, not by a search. Grep every `.glob(` in `tcw/` for a pattern
  built from a caller-supplied string, and report what was found, including
  nothing.
- **The end-to-end story through the CLI**, not the store API. Reproduce the
  destructive case with `tcw work start` on a scratch node before the fix,
  confirm the item is destroyed, then after the fix confirm it is refused and the
  item survives.
- **That the `-33` slice is right for every slug**, including one ending in a
  hyphen or containing one. Check against the construction site rather than by
  example.

## Notes

- Tasks 2 and 3 could be one commit. They are two because Task 2 closes the hole
  and Task 3 is defence in depth; a reader bisecting a future regression should
  be able to tell which is which.
- The suite is green at every commit boundary except Task 1's deliberate red.
