# Reconcile read_artifact with the canonical presence rule

Filed by the C8 audit of
`2026-08-12-make-the-work-lifecycle-polymorphic-and-cli-driven`. Found during
C5 (`2026-08-12-scaffold-lifecycle-artifacts-from-templates`), deliberately
routed around rather than fixed, and recorded in that item's `refined-outcome.md`
so it would not be lost.

## Product changes

TCW has **two answers to "does this artifact exist"**, and they disagree on a
file that exists but holds only whitespace.

`FsWorkStore._present` (`tcw/store/fs.py:2217-2221`) is the canonical rule —
*is a file and has non-whitespace content*:

```python
return p.is_file() and bool(p.read_text(encoding="utf-8").strip())
```

C1 introduced it precisely because "mere existence would let an empty file claim
its stage ran". `artifacts()`, `_resolve_body`, and `body_path` all use it, so
the board, `tcw work show --json`, and the web app agree.

`read_artifact` (`tcw/store/fs.py:3478`) does not:

```python
if not p.is_file():
    return None
```

So a whitespace-only `spec.md` is **absent** to the board and **present** to
`read_artifact`. Nothing today routes a user into the disagreement — C5 checked,
and used `artifacts()` deliberately for exactly this reason — which is why it is
a latent inconsistency rather than a live bug.

## Technical changes

Decide whether `read_artifact` should adopt `_present`, or whether returning a
resource for an empty-but-existing file is deliberate for the read surface (a
caller may legitimately want to read a file in order to see that it is blank).
**Either answer is defensible; having both rules unstated is not.**

If they are meant to differ, say so in `_present`'s docstring and in
`read_artifact`'s, so the next person does not have to rediscover the split.

Sweep for other callers of `p.is_file()` on an artifact path before deciding —
the epic found this one by accident, and a repo-wide check is cheap.

## Meta changes

None.

## References

- `docs/work/completed/2026-08-12-scaffold-lifecycle-artifacts-from-templates/refined-outcome.md`
  — where this was carried forward, with C5's reasoning for not fixing it.
- `docs/work/completed/2026-08-12-unify-raw-intake-into-a-single-artifact/` — C1,
  which established the canonical rule and spent three verify rounds on exactly
  this class of defect.

## Notes

- Not urgent: no user-facing path currently reaches the disagreement. It is
  filed because no test will remind anyone, and the next artifact-reading feature
  is where it would surface.
