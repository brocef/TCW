# `tcw capabilities drift` goes silent in a clone without the resolved folders

## Desired outcome

`tcw capabilities drift` reports the same capabilities in every checkout of a
repository at the same commit, rather than only in the one that ran the
completions.

## Context

`_drift` (`tcw/capabilities/cli.py:195-213`) reports a `Missing` capability whose
`Planning doc` names a work item that shipped:

```python
item = work.get(str(slug))
if item is not None and item.status == "completed":
    out.append((c.path, str(slug)))
```

`completed/` is gitignored by default, so the folder exists only on the machine
that ran `tcw work complete`. Everywhere else `work.get(slug)` answers `None`,
the branch never fires, and the command prints nothing — not an error, just an
empty result that reads exactly like "no drift". A capability left `Missing`
after its work shipped is invisible in CI and in every other clone.

This is the same defect as the one
`2026-09-02-tombstone-resolved-work-items-so-references-to-them-stay-resolvable`
fixed for references: an answer that depends on local residue rather than on
tracked content. That item's spec ran a repo-wide sweep for the pattern
(`spec.md`, "Sweep") and recorded two negative results — `unresolved_blockers`
and `tcw work list`. It missed this one, so the sweep's claim to be repo-wide is
not currently true and should be corrected wherever it is restated.

Found during the adversarial review of that item's branch, and confirmed by
reading the code rather than by running it in a clone.

## Constraints

- The graveyard makes the fix available: `work.tombstone(slug)` survives into
  every clone, and its `resolution` field distinguishes shipped from abandoned.
  A `done` resolution is the tombstone equivalent of `status == "completed"`.
- **Keep the existing distinction.** The comment at `tcw/capabilities/cli.py:206`
  is deliberate: this asks *"did it ship?"*, not *"is it closed?"*, so a
  discarded item's capability is supposed to stay `Missing`. A tombstone
  resolution of `wontfix`, `duplicate`, or `superseded` must not be reported as
  drift. That mapping is the whole fix.
- **Fail closed on an unknown resolution.** `tcw work tombstone add` may record
  an empty resolution, because a backfilling adopter often does not know it.
  Report nothing in that case rather than guessing — the comment above says a
  false positive is the failure mode to avoid here.
- Deliberately **not** folded into the tombstone item. It changes what a
  different command reports, which is the same reason that item non-goaled
  making `unresolved_blockers` precise: acting on a newly available distinction
  is its own behaviour change and deserves its own item.
