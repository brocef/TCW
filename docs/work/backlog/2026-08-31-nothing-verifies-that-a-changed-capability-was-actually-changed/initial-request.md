# Nothing verifies that a `changed:` capability was actually changed

## The observation

`tcw work complete` enforces capability reconciliation, but only half of it. From
`skills/tcw-work/references/transitions.md`:

> **Capability reconciliation is enforced**, not merely acknowledged: it fails if
> a capability the item declared `new:` still reads `Missing`, or a declared path
> does not resolve.

Both of those are real gates. Neither says anything about `changed:`. A work item
can list five capabilities under `changed:`, edit none of them, and complete
cleanly — the paths resolve, so the gate is satisfied.

## Where it was found

Twice in one session, on the same initiative.

**Child A** (`2026-08-26-declare-and-provision-the-work-store-s-home-repository`)
declared three:

```yaml
changed:
    - work/configure-the-work-store-location
    - cli/locate-tcw-storage-folders
    - cli/validate-a-node
```

All three still carried bodies written before that epic began — checked with
`git log -1 -- docs/capabilities/<path>/description.md`, which returned commits
from unrelated earlier items. The item had reached `review` and would have
completed with three capability descriptions contradicting the shipped behaviour.
Caught by hand during the `verify` stage's ledger reconciliation and fixed in
`c2193fb`.

**Child B** (`2026-08-26-generalize-the-store-declaration-to-taxonomy-and-capabilities`)
declared five. They were genuinely edited — but only because the same manual
check was run again, deliberately, having just seen it fail once.

## Why it matters

A stale capability body is worse than a missing one. The ledger's entire purpose
is to describe what a user can currently do, and an entry that confidently
describes the previous behaviour is read as current. `tcw capabilities drift`
does not catch this: it looks for inherited-but-unreviewed entries and for local
`Missing` ones whose planning doc has completed. A `Supported` capability whose
body is out of date is invisible to it.

The `new:` gate exists because "declared and forgotten" is the predictable
failure. `changed:` has exactly the same failure mode and no gate.

## What this is not asking for

Not a check that the body is *correct* — nothing can verify that. The question is
narrower and mechanical: **was this capability's folder touched by this item's
work at all?**

## Sketch, to be decided at spec

Both plausible answers are storage-abstracted; neither needs the filesystem.

- **A revision check.** Capabilities already carry adapter-provided `modified`
  metadata, and `get_capability_detail` returns a core revision token. Comparing a
  `changed:` capability's revision at completion against its revision when the
  item started answers the question without reading git. Needs a place to record
  the starting revision — plausibly the item's own state, set at `start`.
- **An acknowledgement.** Weaker, but honest: `complete` refuses until each
  `changed:` path is explicitly confirmed, the way `--confirm` works. This trades
  enforcement for a prompt, which is what the Definition of Done checklist already
  does and what this item exists to argue is not enough.

The first is the real fix. The second is what to fall back to if the revision
token turns out not to survive the operations a capability edit performs.

## Related

[Nothing enforces a spec's declared capability deltas without a capabilities.yaml](tcw://W/2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml)
is the adjacent hole in the same gate, and the two are worth specced together
even though their fixes differ:

| | that item | this item |
| --- | --- | --- |
| the file | absent entirely | present |
| what fails | no gate runs at all | the gate runs and checks only `new:` |
| the seam | producing `capabilities.yaml` from a spec's declared deltas | what `changed:` obliges, once the file exists |

Together they say the completion gate covers one of the three buckets it is
handed. That item asks "worth checking whether other completed items have the
same gap before choosing" — the two children of this initiative are that check,
and they answer yes.

## Notes

- Found during the `verify` stage of two children of
  [the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it),
  and recorded in child B's `refined-outcome.md` under "Follow-up filed".
- The manual check that caught it, worth keeping until this is fixed:
  `git log --oneline -1 -- docs/capabilities/<path>/description.md` for every
  `changed:` entry, compared against the item's own commit range.
