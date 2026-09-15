# Outcome — Build taxonomy list's tree from real parentage instead of sorting path strings

Shipped as planned, as a one-line sort-key change plus three regression tests.
The headline finding is in "What the plan or spec got wrong": **this repo's own
taxonomy was rendering wrong**, which neither the issue nor the spec anticipated.

## What shipped

### Task 1 — sort on the segment tuple (`5948866`)

`fix(taxonomy): order list by path segments so a hyphen sibling cannot capture a subtree`

`tcw/taxonomy/cli.py`, the `key=` expression only:

```python
key=lambda t: (t.origin != "local", t.origin, tuple(t.slug.split("/")))
```

`indent = "  " * t.slug.count("/")` is unchanged — once ordering is a true
depth-first pre-order, that depth expression is correct for every row. An
eight-line comment above the sort records why the tuple matters (`-` 0x2D sorts
before `/` 0x2F) and why `origin` is a separate key component, so the next reader
does not "simplify" it back to `t.qualified`.

### Task 2 — regression tests (`6b2422a`)

`test(taxonomy): pin the hyphen-vs-slash collision and depth-first list ordering`

Three cases in `tests/test_taxonomy.py`, all asserting **full ordered output**
rather than membership — the defect was an ordering defect, so a membership
assertion would pass against the broken code:

- `test_cli_list_does_not_interleave_hyphen_sibling_with_subtree` — the issue's
  exact shape.
- `test_cli_list_is_depth_first_preorder_at_three_levels` — `a`, `a/b`, `a/b/c`,
  `a/b/c2`, `a/d`, `a-sibling`; pins pre-order, indent width, and sibling
  alphabetical order together.
- `test_cli_list_never_splices_an_inherited_tree_into_the_local_one` — built on
  the existing `consumer_with_shared` fixture, so criterion 4 is covered by test
  rather than by inspection as the plan allowed for.

### Task 3 — documentation sync (`4c67477`)

`docs: record the taxonomy list ordering fix`

| Entry | Trigger | Result |
| --- | --- | --- |
| `docs/changelogs/upcoming.md` | `Any-Code-Change` | **fired** — `Fixed` entry with the 0x2D/0x2F cause, the new key, and the note that this repo's own taxonomy exhibited it |
| `docs/release-notes/upcoming.md` | `Public-API` | **fired** — before/after listing side by side, in plain language |
| `README.md` | `Public-API` | did not fire — checked, not assumed: grep for `[V]`/`[F]` across `README.md`, `skills/`, `commands/`, `docs/capabilities/` returns **nothing**, so no document shows sample `list` output that could have gone stale |
| `skills/<component>/SKILL.md` | `Skill-Driven-Component` | did not fire — same grep. `skills/tcw-taxonomy/references/init.md` encourages the naming pattern that *produces* the collision, but says nothing about ordering, so it needed no change |

## Test result

```
$ python -m pytest tests/test_taxonomy.py -q
33 passed in 1.69s          # 30 before

$ python -m pytest -q
1133 passed in 186.14s (0:03:06)
```

### The tests were proven red against the old key

The plan required this, and the first attempt at it **silently did nothing** —
`git stash push tcw/taxonomy/cli.py` had nothing to stash because the fix was
already committed, so the suite ran against fixed code and reported 33 passed.
That is exactly the false-confidence outcome the step exists to prevent, and it
is recorded here rather than quietly re-run.

Done properly with `git checkout 5948866^ -- tcw/taxonomy/cli.py`:

```
FAILED tests/test_taxonomy.py::test_cli_list_does_not_interleave_hyphen_sibling_with_subtree
FAILED tests/test_taxonomy.py::test_cli_list_is_depth_first_preorder_at_three_levels
2 failed, 31 passed
```

**Two of three, not three.** `test_cli_list_never_splices_an_inherited_tree_into_the_local_one`
passes against the old key too, because `qualified` (`shared/Argument`,
`shared/Argument/nested`) happens to sort correctly when no hyphen collision is
present. It is a genuine guard against a future regression in origin grouping,
but it does **not** discriminate the reported defect, and claiming otherwise
would overstate the coverage.

The fix was then restored with `git checkout HEAD -- tcw/taxonomy/cli.py` and the
suite re-confirmed green before committing.

### End-to-end against the real CLI

The issue's exact commands, re-run in a throwaway repo after the fix:

```
event  [V] (local)
  log-batch  [V] (local)
  stat  [V] (local)
event-reporting  [F] (local)
```

Matches the spec's criterion 1 exactly. Before the fix, the same commands
reproduced the reported output character for character.

## What the plan or spec got wrong

**One material error, and it made the item more valuable than specified.**

The plan's Notes proposed diffing `tcw taxonomy list` over *this repo's* taxonomy
before and after as "a cheap, real-data confirmation that the change is inert
where it should be", predicting an empty diff on the grounds that TCW's 22-entry
taxonomy has "no known collision".

The diff was **not** empty:

```
 capability  [V] (local)
-capability-feature-association  [F] (local)
   status  [V] (local)
   subject  [V] (local)
+capability-feature-association  [F] (local)
```

TCW's own taxonomy had the bug. `status` and `subject` are children of
`capability`, and were rendering as though they belonged to
`capability-feature-association` — a Feature named after the Vocabulary it
operates on, precisely the pattern the issue predicted and that
`skills/tcw-taxonomy/references/init.md` encourages.

Two consequences:

1. Criterion 6 ("row format byte-identical for any taxonomy that did not exhibit
   the collision") still holds — but this repo turned out to *be* a colliding
   taxonomy, so the intended inertness check instead became a second live
   reproduction. The criterion was verified against the throwaway repro's
   non-colliding terms instead.
2. The spec's framing of the collision as a hazard users "may" hit understated
   it. The maintainer's own taxonomy hit it, undetected, while the item to fix it
   sat in the backlog.

## Notes

- **Not an explicit tree, deliberately.** The issue offered "build the actual
  parent/child tree" or "sort on the tuple of path segments". The segment tuple
  was chosen because taxonomy parentage *is* the path — `Term.slug` is documented
  as "path from the taxonomy root" (`tcw/store/base.py:142`) — so both produce
  the same order and the sort is one line against roughly thirty. `tcw/work/cli.py`
  and the web client's `buildPathTree` do build explicit trees, but they must:
  work items carry `parent`/`initiative` parentage that can point outside the
  path.
- **The web editor was checked and has no defect.** `buildPathTree`
  (`web/client/src/model/tree.ts:17-46`) attaches each node to `map.get(parentPath)`
  — real parentage, never a string sort — so the request's second open question
  resolves to "the CLI was the only affected renderer".
- **Orphaned nested terms** (a `event/log-batch` with no `event/meta.yaml`) still
  render indented under nothing. Pre-existing, unreachable through
  `tcw taxonomy add`, and out of scope — recorded in the spec's Risks so it reads
  as considered rather than missed.
- **GitHub issue #11 is deliberately not closed by this item**, per the user's
  2026-07-30 sequencing decision: issues in this batch are answered only after
  the containing minor version is cut and pushed.
