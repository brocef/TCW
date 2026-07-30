# Plan — Build taxonomy list's tree from real parentage instead of sorting path strings

Two tasks and one documentation block. The code change is one line; the test is
the substantial part, because the defect's whole nature is that nothing caught it.

Ordering: the test lands **after** the fix rather than before only because the
reproduction is already confirmed by hand at HEAD (recorded in `spec.md`); the
test's job is to pin the collision permanently, and it is written to fail against
the old key — verify that explicitly by stashing the fix, per Verification.

## Task 1 — sort on the segment tuple

**Changes:** `tcw/taxonomy/cli.py`, the `key=` expression at `:56` only.

```python
key=lambda t: (t.origin != "local", t.origin, tuple(t.slug.split("/")))
```

Three components, each load-bearing:

- `t.origin != "local"` — local block first (unchanged).
- `t.origin` — groups each inherited tree under its own alias. This replaces the
  grouping `t.qualified` used to supply implicitly via its `alias/` prefix, and
  it is **not** optional: each `extends` alias is a separate store with its own
  slug namespace (`tcw/store/fs.py:774-779`), so sorting segment tuples across
  origins would splice unrelated trees.
- `tuple(t.slug.split("/"))` — structural comparison; a parent's tuple is a
  strict prefix of its children's.

Leave `indent = "  " * t.slug.count("/")` at `:57` alone — once ordering is a
true pre-order, the existing depth expression is correct for every row. Add a
short comment at the sort line naming why the tuple matters (`-` < `/`), so the
next person does not "simplify" it back to `t.qualified`.

**Verified by:** the issue's reproduction renders correctly (criterion 1), and
`python -m pytest tests/test_taxonomy.py -q` stays green.

## Task 2 — regression test for the collision

**Changes:** `tests/test_taxonomy.py` (confirm the filename and the existing
fixture style before writing — reuse whatever `tmp_path` node helper the file
already has rather than inventing one).

Cases:

- `test_list_does_not_interleave_hyphen_sibling_with_subtree` — the exact issue
  shape: `event`, `event/log-batch`, `event/stat`, `event-reporting`. Assert the
  **full ordered output**, not merely that `event-reporting` appears somewhere:
  the bug was an ordering defect, so a membership assertion would have passed
  against the broken code. Assert indentation too, since indent and order are the
  two halves that disagreed. (Criteria 1, 7.)
- `test_list_orders_depth_first_at_three_levels` — a three-level tree
  (`a`, `a/b`, `a/b/c`, `a-sibling`) asserting pre-order and indent width.
  (Criterion 2.)
- Sibling alphabetical order within a level (criterion 3) — fold into the above
  rather than a third case if the fixtures already cover it; do not add a case
  that asserts nothing new.

Inherited-origin grouping (criterion 4) needs an `extends` fixture. Check whether
`tests/test_taxonomy.py` already has one — if it does, add a case; if building one
costs more than the criterion is worth, say so in `outcome.md` and record
criterion 4 as covered by reading the key expression rather than by test. Do not
silently skip it.

**Verified by:** new cases green; and — importantly — **confirmed red against the
old key** (see Verification).

## Task 3 — documentation sync

Evaluated over the finished diff in one pass, per `stage-implement.md` step 6.
Predicted:

| Entry | Trigger | Expected |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fires** — `Fixed`: `tcw taxonomy list` sorted on the joined path string while indenting from segment count, so a root slug that is a hyphen-extension of another root (`event-reporting` vs `event`) sorted between that root and its children and inherited their indentation. Now sorts on the segment tuple; inherited trees grouped per origin alias. |
| `docs/release-notes/upcoming.md` | `Public-API` | **fires** — wrong output a user reads and believes. Plain language, with the before/after listing. |
| `README.md` | `Public-API` | **check** — README documents `tcw taxonomy list`. It almost certainly does not show a colliding example, but if it prints sample tree output, confirm that sample is still accurate. |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | **check** — `skills/tcw-taxonomy/`. Its `references/init.md` actively encourages the naming pattern that produces the collision (a Feature named after the Vocabulary it operates on). Nothing there is *wrong* now, but if any document shows sample `list` output, it may need refreshing. |

## Verification

**The test must be proven to fail against the old code.** This is the one step
that distinguishes a real regression test from one that passes either way, and
it matters more than usual here: the defect survived because ordering was never
asserted. Procedure:

```sh
# with the new tests written and the fix in place — expect green
python -m pytest tests/test_taxonomy.py -q

# revert only the sort key, keep the tests — expect the new cases RED
git stash push tcw/taxonomy/cli.py
python -m pytest tests/test_taxonomy.py -q
git stash pop
```

Record both outcomes in `outcome.md`. If the tests pass with the fix reverted,
they are not testing the defect — rewrite them.

**End-to-end check against the real CLI**, not just the unit fixtures: re-run the
issue's exact commands in a throwaway repo and paste the actual `tcw taxonomy
list` output into `outcome.md`. The scratchpad repro from the spec stage can be
rebuilt for this. Note that the editable install points at the primary checkout,
so the rebuilt repro exercises the patched code directly.

Full `python -m pytest -q` green before `submit`.

## Notes

No blockers. Independent of the other items in the batch.

Criterion 6 (byte-identical rows for non-colliding taxonomies) is worth an
explicit check rather than an assumption: run `tcw taxonomy list` against **this**
repo's own taxonomy before and after the change and diff the two outputs. TCW's
taxonomy has 22 entries and no known collision, so the expected diff is empty.
That is a cheap, real-data confirmation that the change is inert where it should
be.

GitHub issue #11 is **not** closed at completion — deferred until the containing
minor version is cut and pushed, per the user's decision on 2026-07-30.
