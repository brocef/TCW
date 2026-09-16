# Delegation

## What makes it correct

- **`Inputs` is the subagent's context brief.** The section that exists for token
  efficiency is the same one that makes delegation safe.
- **`Produce` is the return contract**, and must be specific enough to check. A
  subagent returning "done" gives the coordinating session nothing.
- **The coordinating session re-reads the artifact.** Isolation is not free, and
  pretending otherwise is how a delegated stage ships unverified. The win is
  reading a few hundred lines instead of a multi-thousand-line transcript — large,
  but not total. Where `Produce` names required sections, the check can be
  structural rather than a full read.
- **A subagent's context is discarded when it returns.** Everything it noticed and
  did not write down is lost. `## Notes` is the only channel for the part of that
  knowledge with no home in the required sections.

If a delegated stage fails to produce its artifact, that is a `[judgment]`
failure caught by the coordinating session, not a `[gated]` one — no transition
was attempted, so nothing refused. Check `Produce`, then re-dispatch or escalate.

## The shape this produces

The main session becomes a coordinator: it owns the transitions and the two
interactive stages, and dispatches the rest. `implement` is the largest token
sink and the most valuable delegation.
