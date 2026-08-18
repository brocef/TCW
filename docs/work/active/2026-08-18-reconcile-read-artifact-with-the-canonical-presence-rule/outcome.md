# Outcome — Reconcile `read_artifact` with the canonical presence rule

The two presence rules are now stated on the `WorkStore` interface, pinned by a
test, and **unchanged**. Suite: **1624 passed, 0 failed in 264.50s** — exactly
the 1623 baseline plus the one test this item adds, which is the number the plan
predicted rather than a floor it cleared.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1 | Characterization test, written against the untouched tree | `24a8b46` |
| 2 | Mutation check — no commit by design | — |
| 3 | Both rules stated in `base.py`; `_present` and `read_artifact` in `fs.py` | `6825a76` |
| 4 | Changelog | `e3bc0de` |

## The decision this item was filed to make

**The split is deliberate. `read_artifact` keeps `is_file()`.** Written down in
four docstrings and one comment, where an adapter author will look.

## Acceptance criteria

All seven met.

- **1, 2, 3, 7** — `tcw/store/base.py`'s `artifacts` and `read_artifact` state
  their rules and cross-reference each other; `read_sidecar` and
  `read_plan_stage` carry the resource rule; `_present` no longer claims to be
  "the one presence rule" and does not enumerate its callers.
  `grep -rn "the one presence rule" tcw/` returns nothing.
- **4** — `test_the_two_artifact_presence_rules_disagree_on_purpose` asserts all
  four facts about one whitespace-only artifact.
- **5** — verified by mutation, below.
- **6** — 1624 passed, and no behavior changed (proven structurally, below).

## Two verifications worth more than the criteria asked for

**The test was necessary, and this measures how necessary.** With `read_artifact`
mutated to `self._present(p)` — the change the request originally proposed —
`tests/test_work.py`, `test_scaffold.py`, `test_serve.py`, `test_serve_write.py`,
`test_show_json.py` and `test_projection.py` were run together:

```
1 failed, 388 passed in 124.67s
FAILED tests/test_work.py::test_the_two_artifact_presence_rules_disagree_on_purpose
```

**388 tests passed under the mutation.** Before this item, the "obvious" fix would
have landed green across every suite that plausibly covers artifact reads, and the
read/write contradiction would have shipped. That is the case for the item, and
it is stronger than the spec's argument was.

**"No behavior change" is proven, not asserted.** `git diff --stat` showing only
docstring hunks is an eyeball check. Instead both files were parsed before and
after, docstrings stripped from every module/class/function body, and the ASTs
compared — comments never enter an AST, so what remains is exactly the executable
content:

```
tcw/store/base.py: executable AST identical = True
tcw/store/fs.py:   executable AST identical = True
```

## What the plan or spec got wrong

**1. The spec's central argument was overstated, and it contradicted its own
evidence.** The first draft called the `_present` adoption a *deadlock* — "the
client cannot recover". Its own measured table three paragraphs earlier showed
`get_detail().artifact_revisions` containing the revision. Adversarial review
found it; `WorkStore.get_detail`'s abstract docstring promises revisions for
"every lifecycle artifact", so the recovery route is part of the published
interface, not a filesystem escape hatch. The claim is now the narrower true one:
the paired read/write calls contradict each other, and every route out requires
knowing about the split — which is an argument for writing it down, not for
changing code.

**2. The spec inherited a false claim from the request and repeated it.** "No
user-facing path currently reaches the disagreement" is wrong. `tcw serve` builds
its artifact list from `read_artifact` (`tcw/serve/__init__.py:658-662`), so the
web app shows a blank Spec as present while the board says the stage never ran,
and `tcw work scaffold` writes a competing draft beside it. Now decided
explicitly — all three surfaces are right, each answering its own question — with
the missing *affordance* filed as a follow-up rather than absorbed.

**3. The sweep table was wrong twice, in opposite directions.** The request named
three `_present` callers including `body_path`, which is not one (it delegates
through `_resolve_body`). There are four, and the two nobody had listed —
`update_work`'s promotion check and `write_draft`'s clobber guard — are the most
persuasive evidence in the spec, because both would be *wrong* with `is_file()`.
Then the corrected version overstated in the other direction, claiming all
sixteen assignments were deliberate; review pushed back and it is now narrowed,
with two sites named as arguably on the wrong rule (`write_draft`,
`PlanStage.present`).

**4. Nothing in the plan turned out to be wrong.** Stated rather than omitted,
because an empty section here is a claim.

## Notes

- **The strongest evidence in the spec was already in the repository.**
  `tests/test_scaffold.py:220` is named
  `test_a_whitespace_only_artifact_does_not_block_scaffolding`, and its docstring
  argues the rule: *"The board says no spec exists, so the verb must agree."* The
  original sweep missed it. The split was never undecided — the reasoning just
  lived in a test for one verb instead of in the interface every verb implements.
- **Follow-up to file at completion:** the web app shows a blank artifact as
  present with no indication that its stage has not run. A `tcw serve` UI change,
  deliberately not folded into an item whose premise is that no behavior moves.
- **Stage ordering was correct this time.** `spec` and `plan` were both written
  and committed in `backlog`, and `tcw work start` ran after the plan and before
  the first code edit — the mistake the sibling stdin item made and is still
  carrying a note about.
- **Reviewed by `codex`. `bllm-review` was not attempted for this item**, having
  produced nothing on the sibling item after 1440s on a workload lock; the bug is
  filed to `/Users/brian/llama/docs/work/inbox/`.
