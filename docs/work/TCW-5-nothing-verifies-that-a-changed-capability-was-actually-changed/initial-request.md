# Nothing verifies that a `changed:` capability was actually changed

## The observation

`tcw work complete` enforces capability reconciliation, but only half of it. From
`skills/work/references/transitions.md`:

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

## Folded in: 2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

## Nothing enforces a spec's declared capability deltas without a capabilities.yaml

### Origin

Found at the `verify` stage of
`2026-08-19-key-work-documentation-uniqueness-on-path-trigger-so-one-file-can-carry-two-triggers`,
while checking the standing ledger before writing that item's own
`## Capability changes` section.

### What was found

`2026-08-18-serve-documentation-sync-entries-from-tcw-config-yaml-instead-of-scraping-the-agent-guide`
declared two new capabilities in prose, in its `spec.md:5-10`:

> **New.** Two capability records under `docs/capabilities/work/`:
> - *Declare which documents track which changes* …
> - *Read the documentation gate for a change* …

Neither record was ever written. The item completed anyway, and its
`refined-outcome.md:65` records `tcw capabilities drift` as reporting **no
capability drift** — which was true, and is the problem.

The two records have since been written by hand (`55b49c2`), so the ledger is
correct now. What remains is the hole that let it happen.

### Why nothing caught it

Three mechanisms could have, and none applies:

1. **`tcw capabilities drift`** looks for inherited-but-unreviewed entries and
   local entries still reading `Missing` whose `Planning doc` names a completed
   item. A capability that was never created has no record to read `Missing`, so
   it is invisible to drift **by construction**. This is arguably correct
   behavior rather than a bug — drift audits the ledger, and the ledger is where
   the entry is absent.
2. **The `capabilities.yaml` completion gate** does exactly the right check: it
   blocks `complete` when a path under `new:` still reads `Missing` or fails to
   resolve. But the item never had a `capabilities.yaml` — the file is the
   work→capability back-pointer, and nothing requires one even when the spec's
   `## Capability changes` section is non-empty. No file, no gate.
3. **The `spec` stage instructions** require a `## Capability changes` section,
   but its content is prose. `tcw` never reads it, so "New. Two capability
   records…" is a sentence, not a commitment.

So a spec can promise capability records in the one section built for it, and
the item can complete with the ledger untouched and every check green.

### Shape of a possible answer

Not a decision, just where the seam looks like it is: the `spec` (or `plan`)
stage is where a declared delta could be turned into the `capabilities.yaml`
back-pointer that the completion gate already knows how to enforce — either by
writing it, or by refusing to leave the stage with a non-empty
`## Capability changes` section and no corresponding file. Whether TCW should
parse that prose section at all is the open question, and it may be that the
honest fix is in the stage instructions rather than in the CLI.

Worth checking whether other completed items have the same gap before choosing.

### Later evidence

> Worth checking whether other completed items have the same gap before choosing.

Checked, 2026-08-31, on the two completed children of
[the store-home-repository epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it).
Both **had** a `capabilities.yaml`, so the gate described in point 2 above did
run — and a sibling hole showed up beside this one: the gate checks `new:` and
says nothing about `changed:`. Child A declared three `changed:` capabilities and
edited none of them, and would have completed cleanly.

Tracked separately as
[Nothing verifies that a changed: capability was actually changed](tcw://W/2026-08-31-nothing-verifies-that-a-changed-capability-was-actually-changed),
because the fixes differ — that one is about what `changed:` obliges once the
file exists, this one is about the file existing at all. They are the same gate
and probably want one spec.

Axis: work (and capabilities).
