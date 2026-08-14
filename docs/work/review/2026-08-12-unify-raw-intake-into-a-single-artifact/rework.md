# Rework — Unify raw intake into a single artifact

Third rejection at `verify`. The second rework's behavior is **accepted**: all
seven of the previous `rework.md`'s verification bullets were re-checked against
a scratch node through the real CLI, not only against the suite, and each holds
at the property rather than at the mechanism. The refused-commit retry, the
both-sides-prose migration, the absent-block no-op, and the idempotent third
`--commit` were all exercised live. No composed `store.path(...) / "<file>"`
remains in the reconcile flow, and no code path in `tcw/` creates
`initial-request.md` outside the `request` stage.

What follows is small and entirely in the reporting layer — three claims that
say something the code no longer does — plus one gap the verifier priced far
lower than the second rework's outcome document did.

## What still has to be done

### 1. `stage-request.md` still carries the retracted claim

`skills/tcw-work/references/stage-request.md:25-27` says of
`initial-request.md`:

> For an epic it also carries the coordination goal and is the **managed target
> for `tcw work reconcile`'s rollup**.

That is the exact sentence the previous `rework.md`'s Documentation section
declared wrong. It was fixed in `epic-deltas.md` and missed here — and it
contradicts this same file eight lines earlier, which says the request is
"absent until this stage runs — that is what makes `R` on the board mean
something". Inside this rework's own declared scope, and inside CLAUDE.md's
`skills/<component>` sync rule.

### 2. The "no `R` on the board" assertion is a tautology

`tests/test_recursion.py:816`:

```python
assert "R" not in {a.name for a in store.artifacts(epic) if a.present}
```

`artifacts()` yields artifact *names* — `initial-request`, `spec`, `intake` —
never the letter `R`. The set can never contain `"R"`, so the line passes with
the request present and pins nothing.

The property itself is real and is already pinned by the two lines around it
(the folder listing and `read_artifact(...) is None`). The board letter follows
mechanically from the artifact's absence. So this is a line to **remove**, not a
renderer test to add — a check that cannot fail is worse than no check, because
it reads as coverage.

Note the shape: this is the third appearance of the fallacy this item keeps
tripping on, and this time it is in the assertion written to close the second
appearance of it.

### 3. The release note overstates what stayed the same

`docs/release-notes/upcoming.md` says of the rollup: "Reading it, committing it
with `--commit`, and everything else about the command are unchanged; only its
destination moved."

Reading it is not unchanged. `tcw work show <epic>` used to print the rollup,
because the rollup *was* the body. It now prints state alone, and there is no
`tcw work sidecar` read verb. The mitigations are real — `reconcile` re-prints
the block and provably stages nothing when unchanged, `tcw work path` locates
the file, the web app lists and reads it — but the sentence as written is false.
Reword it to say what actually happens.

### 4. Mark the rollup sidecar generated, and stop offering to edit it

`tcw serve` builds its sidecar list straight from `WORK_SIDECARS`
(`tcw/serve/__init__.py:591` and `:650`), and the client renders every present
sidecar with an unconditional Edit button
(`web/client/src/ui/content-views.tsx:548-586`). So `rollup.md` is editable in
the web app, the write succeeds, and the next `reconcile` silently discards it.

The second rework's `outcome.md` deferred this on a cost estimate that was
wrong. Both serve payloads are already assembled field-by-field from `sc_info`,
so the change is one registry key, that key echoed into the two payload
builders, and one conditional around the button. The PUT rejection and a
read-only editor mode are optional hardening, not prerequisites — leave them.

Reading the rollup in the web app is the improvement and must survive: hide the
Edit affordance, not the sidecar.

The structural point is worth stating once in the code: `WORK_SIDECARS` gained a
member of a new *kind* — generated rather than authored — and no consumer
learned the kind exists. The next generated sidecar would inherit the same hole
for free.

## Verification

- `stage-request.md` no longer names the request as the rollup's target, and no
  longer contradicts itself.
- The tautological assertion is gone; the test still fails if reconcile writes a
  request.
- The release note describes reading the rollup accurately, including what
  `tcw work show` does now.
- In the web app, a present `rollup.md` is listed and readable, and offers no
  Edit button; `capabilities.yaml` still offers one.
- Suite green, `pnpm check:build` clean.

## Notes

- Nothing here is a behavior defect in `reconcile`. If the fixes were skipped the
  tool would still be correct — the documents describing it would not be. That is
  the whole of this round.
