# Outcome — Enforce the gitignore trap at write time, not only at init

Four commits, as planned, `pytest` green at each boundary.

## What shipped

| Task | Commit | What landed |
| --- | --- | --- |
| 1 | `fix: warn when a .gitignore rule hides a staged store write` | `_warn_hidden` + the `git_stage` guard, 5 tests |
| 2 | `fix: warn when git_mv untracks an item into an ignored destination` | the `git_mv` guard, 2 tests |
| 3 | `capabilities: a hidden write now announces itself` | the two capability text deltas |
| 4 | `docs: record the write-time gitignore warning` | changelog + release notes |

The shipped shape is exactly what the spec decided: one module-level helper,
two call sites, warn-and-proceed on stderr, `completed/`/`discarded/` silent,
existence tested per call site rather than in the helper.

## Test result

`python -m pytest tests/test_work_autocommit.py -q` → **50 passed** (43 before).
Full suite green; the final number is recorded at `verify`.

## Red-first, and the one that was green for the wrong reason

Task 1 behaved exactly as the plan predicted: of its four tests, one failed on
an empty `err` and three passed on `main` — they are regression locks, not
red-first tests, and the plan says so.

**Task 2's test passed before its guard existed, and that is the finding worth
recording.** `tcw work submit` into an ignored `review/` reaches *both* call
sites, so `git_stage` was already warning about
`docs/work/review/<slug>/state.yaml`. The folder path is a **prefix** of that
file path, so the planned assertion —

```python
assert f"docs/work/review/{slug}" in err
```

— was satisfied by the other guard's line and proved nothing about `git_mv`.
The plan anticipated the two-line output (R2) and correctly forbade line-count
assertions, but its own substring is too loose in the other direction. Fixed by
matching the message terminator, which pins the folder as its own warned path:

```python
assert f"hides docs/work/review/{slug};" in err, "the git_mv guard did not fire"
assert f"hides docs/work/review/{slug}/state.yaml;" in err
```

With that, the test went red on exactly the missing guard and the failure text
named it. This is the second time in this batch that "watch it red *and read
why*" caught a test that would have shipped green and meaningless.

## What the plan and spec got wrong

The plan was unusually strong — it measured rather than predicted, and its five
empirical re-checks (R1–R5) all held up. Corrections:

- **The plan's own criterion-5 assertion was too loose** — above. Its R2 section
  contains the information needed to see the problem; the assertion it then
  specifies does not use it.
- **The spec named a `tcw work discard` command that does not exist** (caught by
  the plan at R5, confirmed here). The route to `docs/work/discarded/` is
  `complete --resolution wontfix`; `tcw work drop` is a hard delete. Only the
  spec's Goal 3 prose is wrong — its criterion 4 was already right.
- **The spec's criterion 8 expected `git status --porcelain` to show the item
  staged** after `start`. It does not: `start` auto-commits, so the tree is
  clean and the item is at `HEAD`. The test asserts `git ls-files` instead.
- **The spec's `skills/work/SKILL.md` path** is `skills/tcw-work/SKILL.md`.

Nothing in the design changed. Every correction is about what a test may be
written against.

## Documentation Sync

All four declared entries (`tcw work docs`) evaluated against the finished diff:

- **`docs/changelogs/upcoming.md` — [Any-Code-Change] fires.** Names both call
  sites, the helper, and the three load-bearing details: the absolute-path
  component match and why it is biased toward silence, the per-call-site
  existence test and why, and the known two-line output.
- **`docs/release-notes/upcoming.md` — [Public-API] fires.** New section. No
  module names. Covers the `git_mv` case explicitly, since a user with that
  setup has been losing items from version control on every transition.
- **`README.md` — [Public-API] does not fire.** No command, flag, or exit code
  changes. README documents neither `git_stage` nor the ignore interaction
  beyond the rules `init` writes.
- **`skills/<component>/SKILL.md` — [Skill-Driven-Component] does not fire.** No
  CLI surface, model, lifecycle or guardrail change reaches a skill. The nearest
  mention, `skills/tcw-work/references/transitions.md`, already describes the
  ignored-destination *behaviour* correctly; only the output changed, and that
  is a user-facing note, not agent guidance.

## Abstraction litmus test

Passes. `git_stage`, `git_mv` and `_warn_hidden` are private to the filesystem
adapter — `grep` finds no reference to any of them in `tcw/store/base.py`,
`tcw/work/`, `tcw/serve/` or the CLI. "Is this path hidden by an ignore rule"
has no analog in a Jira or wiki adapter and needs none: such an adapter simply
never emits the line. Same disposition as `require_repository`, which documents
itself as a filesystem-adapter precondition rather than a model concept.

## Known limits, accepted

- **Under `tcw serve` the warning reaches the terminal running the server**, not
  the browser. `tcw serve` is a writing surface, so the case is real. Routing an
  advisory into an HTTP response would mean a new field on every mutating
  endpoint and a client surface for it — out of scope, and the operator is the
  only one who can act on the warning anyway.
- **Two lines from one command**, when both call sites fire. Deliberate: a
  de-duplication cache is state the function does not otherwise carry, and it
  only happens in an already-broken setup.
- **A repository path containing a directory literally named `completed` or
  `discarded` silences the warning.** The component match is on the absolute
  path on purpose — a store-relative match risks a spurious `relative_to` raise,
  and that would mean a false warning on every `complete`, the one failure this
  must not have. Marked with a `ponytail:` note naming the upgrade path.
- **A rule naming a real slug still slips past `init`'s guard.** Unchanged; that
  ceiling is what this item exists to cover at write time, not to remove at
  configure time.

## Notes

- `_warn_off_trunk`, the stderr-advisory precedent this design copies, has **no
  test** — noticed at spec time and still true. Not this item's business, but
  worth knowing before anyone assumes that shape is covered.
- `tcw serve`'s help text still calls it "a local **read-only** web viewer",
  which has not been true since the editing endpoints landed. A stale string, not
  this item's scope; flagged in the spec's Notes and repeated here so it is not
  lost.
- Batched with the other four `bug`-tagged items into a single patch release.
  The version cut is not this item's decision, and no version file was touched.
