# Resume state — delete this file before completing the item

Written at `d5d62931` when the session was restarted mid-implementation. This is
scaffolding, not a lifecycle artifact.

## Where this item stands

`spec.md` and `plan.md` are written and committed. Implementation is **two of six
tasks done**.

| Task | State | Commit |
| --- | --- | --- |
| 1 — failing tests for the loader contract | done | `7aaf66ae` |
| 2 — the loader raises on a non-mapping | done | `b94ab11f` |
| 3 — classify the 21 uncaught call sites | **not started** | — |
| 4 — `validate` parses everything, shape-checks what TCW owns | **not started** | — |
| 5 — the contract in the abstract store | **not started** | — |
| 6 — end-to-end by hand | **not started** | — |

Then: `outcome.md`, review, `refined-outcome.md`, an `## Autonomous decisions`
section, `tcw work complete`.

## The tree is mid-change and `tcw validate` fails right now

This is expected, predicted by the spec, and is exactly what task 4 fixes:

```
$ tcw validate
docs/work/dod.yaml: …/docs/work/dod.yaml: expected a mapping, found list
1 problem(s).
```

`tcw/validate.py:271` scans every `*.yaml` through `load_yaml` for syntax alone
and discards the value. Now that `load_yaml` refuses a non-mapping, the one
legitimate top-level list in the tree fails it. **Nothing is wrong with
`dod.yaml`** — task 4 makes that loop parse directly.

Until task 4 lands, `tcw work complete` will refuse anywhere `tcw validate` is a
`pre` hook, which it is in this repository. That blocks completing *any* item,
not only this one.

## The one thing to do first

**Run the full suite.** `tcw/store/fs.py:load_yaml` now raises where it used to
coerce, across 31 call sites. The run that would have shown what that breaks was
killed by a branch merge and never restarted, so **the blast radius of task 2 is
currently unmeasured**. Baseline before this item was `2627 passed`.

```sh
python -m pytest -q
```

Anything that fails is task 3's input, not a surprise.

## What task 3 actually is

The plan deliberately predicts no diff for it. There are 31 `load_yaml` call
sites, 28 in `tcw/store/fs.py` and 3 in `tcw/validate.py`; ten are already inside
an `except yaml.YAMLError`. Read every other one and classify: does an exception
there reach a user as a message, or as a traceback? Record the classification as
a table in `outcome.md`. Sites that would traceback get a catch.

## Facts already established, so they are not re-derived

- **Three defects, not the one the intake reports.** A falsy `tcw-config.yaml` is
  silently overwritten by `init` where a truthy non-mapping is refused; a
  `state.yaml` of `[]` makes a corrupt item read as healthy with `tcw validate`
  reporting OK; a `state.yaml` of `- a` crashed `tcw work list`, taking the whole
  board down. All three reproduced at `31241b5c`.
- **`yaml.YAMLError` was the load-bearing choice**, not `ValueError`. Ten sites
  already catch it, so the board crash is fixed at all of them with no per-site
  edit. Both advisors reached this independently.
- **Raising does not fix the worst defect.** `_safe_yaml` catches the new error
  and still yields a fabricated title, so `tcw validate` still reports OK. That
  tolerance is correct — one corrupt item must not blank the board — which is why
  the report belongs in `validate` (task 4).
- **Exactly one site needs a different contract**: `tcw/validate.py:271` scans
  every `*.yaml` for syntax only and must keep accepting any shape, because
  `docs/work/dod.yaml` is a legitimate top-level list and an attachment may be
  anything.
- **The owned-name set for task 4** is `state.yaml`, `meta.yaml`,
  `capabilities.yaml`, `graveyard.yaml`, `config.yaml`. All 372 such files in
  this repository are mappings today; `dod.yaml` is the only non-mapping and is
  deliberately not in the set.

## Run-level state

Five of six items in the sweep are complete. The sixth,
`2026-08-18-report-the-missing-skill-caveat-from-tcw-work-lifecycle-rather-than-the-skill`,
has not been started.

Four follow-ups are filed in `docs/work/inbox/` and none is triaged. The largest
is `2026-09-11-take-over-cannot-recover-a-claim-from-the-cli.md`: the documented
remedy for an interrupted claim cannot be run from the command line at all.

Standing instruction for the run: accumulate changelog and release notes in
`upcoming.md`, never cut a version, and never push.
