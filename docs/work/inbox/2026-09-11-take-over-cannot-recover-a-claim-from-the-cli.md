# `tcw work start --take-over` cannot recover an interrupted claim

## Desired outcome

The documented remedy for an interrupted claim works when a user runs it.

## Context

Found by verification of
`2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`, and
pre-existing — reproduced at `60c8b857` and at `8fe0123b`, so neither that item
nor its companion caused it.

When a process dies holding a claim, every read of the item reports:

```
<slug> has an interrupted claim; use --take-over --owner <identity>
```

Following that advice produces the same message:

```
$ tcw work start 2026-09-11-real --take-over --owner recovery@example.com
tcw: 2026-09-11-real has an interrupted claim; use --take-over --owner <identity>
$ echo $?
1
```

`_start` (`tcw/work/cli.py:781-784`) evaluates `st.get(bare)` as an argument to
`run_pre`, so it runs **before** `st.start` is reached and before the
`take_over` flag is consulted at all. `get` stabilizes its read by consulting the
claim directories, finds the interrupted claim, and raises. `FsWorkStore.start`
is never entered, so its take-over branch — the code that exists precisely to
recover this state — is unreachable from the command line.

The branch itself works: `FsWorkStore.start(slug, owner=…, take_over=True)`
recovers correctly when called directly, and
`tests/test_external_work_store.py:590` covers it. **The tests exercise the store
API, so nothing failed.**

## Constraints

- **The `pre`-hook ordering is deliberate and must not be casually reversed.**
  The comment at `tcw/work/cli.py:778-780` explains it: a `pre` hook may refuse
  the transition, and a refusal has to mean nothing happened, so evaluating one
  after any store call would make that false. A fix that moves `st.get` after
  `st.start` trades this bug for that one.
- **The likely shape is to make the read tolerate the state it is reporting** —
  pass `take_over` down, or use the non-stabilizing `_get_now` that `start`
  itself uses for exactly this reason (`tcw/store/fs.py:3553-3556` says the
  stabilizing `get` "would make `--take-over` — the documented remedy for an
  interrupted claim — unreachable the moment there was something to recover").
  **That comment describes this bug, in the store, about the CLI, and has been
  sitting there correct and unheeded.**
- **`tcw serve` cannot recover either**, for a different reason: its start action
  never passes `take_over` (`tcw/serve/__init__.py:870`). Decide whether that is
  in scope.
- **Check what else `run_pre` pulls forward.** `st.get` is one of four arguments
  evaluated there; the others may have their own preconditions.

## Supporting resources

- `tcw://work/2026-09-09-validate-a-slug-before-the-claiming-lookup-globs-with-it`
  — its spec records that the same `st.get` call is also what makes that item's
  destructive case unreachable from the CLI, which is why its severity was
  corrected downward. The two are the same mechanism seen from opposite sides:
  it blocks an attack and it blocks the remedy.
