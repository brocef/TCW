# Refined outcome — The claiming lookup globs with an unescaped slug

**Accepted.** Two lines of production code, five tests, seven criteria met.

## The verification decision

Taken autonomously, on four readings plus my own — and one of them overturned my
central claim.

- **Codex** and an **Opus advisor**, before implementation. Both confirmed that
  the validator the request named does not reject pattern syntax, so the proposed
  fix would not have worked. The Opus advisor reproduced the destructive case and
  found that the escape alone closes it.
- **`adversarial-code-reviewer`**, on the combined difference with the companion
  item. Built claim directories for a dozen awkward slug shapes and confirmed
  each matches only its own; verified the slice arithmetic against the
  construction site.
- **`tcw-verifier`**, which **proved my severity claim wrong** — see below — and
  found that deriving the take-over destination is load-bearing rather than
  defence in depth.
- **My own**: the destructive case reproduced through the store API, the fix
  confirmed end to end, a mutation check turning both wildcard tests red, and a
  sweep of every glob in the package.

## The one thing worth remembering

**I asserted that the destructive case was reachable from the command line, and
raised the item's priority on it, without ever running the command line against
the unfixed code.**

My reproduction was through the Python store API throughout. The check I recorded
as "end to end through the CLI" ran against the *fixed* code, where it correctly
refuses — and I read a correct refusal as confirmation of a reachability claim it
said nothing about. The verifier tested it properly: an earlier read in the CLI
path raises before the destructive branch is entered, so the item survives. I
then reproduced that myself against the pre-change source.

The requester's original assessment, which I overrode in the spec, was closer to
right than my correction of it. Priority is back from 55 to 35 and every
user-facing document has been rewritten.

**The lesson is narrow and exact: a reproduction through one entry point says
nothing about another, and "I ran the CLI" means nothing if the run was against
the fixed code.** A green check proves only what it was pointed at.

## What acceptance rests on

That the destructive path was reproduced, closed, and the closure confirmed at
the entry point that can reach it; that a mutation reopening it turns tests red;
and that recovery demonstrably did not narrow, including the half a criterion had
quietly dropped.

## Also corrected during review

- **Task 3 is not redundant**, as the plan and my first outcome both said. For a
  slug containing `/` the escape does nothing, and deriving the destination is
  the only thing bounding where the item is published. That is the second half
  of the original request, implemented correctly while misunderstood.
- **An acceptance criterion was narrowed between spec and plan** and reported met
  on the narrower wording.
- **A test could not catch what it was written for**: a swept sibling is
  committed, not moved, so asserting the directory still exists proved nothing.
  It now reads the commit.
- **The glob sweep reported the wrong number of call sites.**

## Deferred

- **`tcw work start --take-over` cannot recover from the CLI at all**, filed.
  Pre-existing, and the store already carries a comment predicting it.
- **A slug beginning with `/` crashes the lookup** rather than refusing, filed.
  Not fixed here because this spec made that validator an explicit non-goal, and
  reversing it mid-implementation is how scope drifts.
- **The version cut**, per the run's standing instruction.
