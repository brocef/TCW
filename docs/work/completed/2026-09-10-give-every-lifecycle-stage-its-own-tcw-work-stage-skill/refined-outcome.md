# Refined outcome

## Decision

**Accepted.** The user approved completion on 2026-09-10, with criterion 11
explicitly deferred (below) rather than waived.

## Evidence

- `python -m pytest -q -p no:cacheprovider` at the final commit: **2496 passed**,
  exit 0. Re-run independently by the `tcw-verifier` agent: 2496 passed, same
  count.
- `tcw capabilities check` and `tcw validate` both exit 0.
- An independent read-only verification pass checked all eleven acceptance
  criteria **by mutating files and observing failures**, not by reading the
  assertions. Ten confirmed met. Twenty-five separate mutations across the five
  new skills — dropping `|| true`, deleting the prose gate line, breaking the
  router path, restoring the two-argument form, dropping `Bash(cat *)` — each
  produced exactly one failure, so no assertion is vacuous for any of the six
  composing skills.
- The five new skills were normalised against the generic one and differ in
  exactly one place, identically across all five: an added sentence in the
  manual-fallback fence. No accidental drift from the template.

## Deferred: acceptance criterion 11

Criterion 11 — a live invocation of `/tcw:tcw-work-stage-spec` with and without a
work item reference — is **not met**, and this item completes anyway by explicit
decision.

**Why it could not be discharged here.** Claude loads the plugin from
`~/.claude/plugins/cache/tcw/tcw/<version>/`, which holds versioned *copies*. A
session editing `skills/` is therefore not running those skills unless the plugin
is reinstalled from the checkout, and that write into the user's plugin cache was
not made. Independently confirmed during verification: the cache holds nine skill
directories and none of the five new ones.

**Where it goes instead.**
`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness`, on
`main`, was rewritten around lifecycle prompt-injection fidelity while this item
was in flight. Its axis A enumerates seven injection failure modes, and its first
two are precisely what criterion 11 checks: **I1**, nothing renders, and **I2**,
one block renders and the other does not. It already names this item and this
item's test file. It is a better home for the check than a one-off manual
observation, because it runs under both harnesses and is repeatable.

**What is unproven until then.** That these five files, once installed, render.
Everything underneath was verified: both injected commands were run by hand, in
both argument cases, for all five stages, each exiting 0; the router paths
resolve; and the interpolation behaviour the optional argument depends on was
observed against the generic skill. What is extrapolated is that behaviour moving
from a two-argument skill to a one-argument one.

## Follow-ups, neither blocking

1. **An assertion weaker than it looks.** Deleting the injected
   `tcw work stage prompt <stage> $item` line from a skill leaves the suite green
   — reproduced, 147 passed. `test_the_composing_skill_names_the_gate_in_its_own_prose`
   searches the whole body for that literal, and the manual-fallback fence
   contains a copy, so the fence alone satisfies it;
   `test_every_injected_command_survives_its_own_failure` only constrains
   whichever injections remain. This is the same failure the neighbouring `gate`
   assertion already suffered once and was fixed for by stripping fenced blocks —
   the fix is recorded in that test's own docstring. The `prompt` line never got
   the same treatment. **Pre-existing**: it held for the generic skill before this
   item, which then copied the shape into five more files.
2. **Stale citations.** The eval-harness spec on `main` cites
   `tests/test_skill_lifecycle_parity.py:344` and `:365` as the two static
   guards. This item rewrote that file; those guards are now at `:427` and
   `:449`, and lines 344 and 365 hold different tests entirely. That spec's own
   stage instructions require citations to still resolve.

## Corrections to `outcome.md`

Surfaced by verification and recorded here rather than by amending a committed
artifact:

- It said "branched from `591e155`". That commit is an ancestor; the actual base
  is `cda6769`, two commits later.
- It said "seven commits". Seven carried implementation and documentation; the
  branch holds more once the outcome and the status transitions are counted.
- It said all five skills hit the YAML frontmatter defect on first write. All
  five did, but only one was committed in that state and the rest is unrecorded.
  The claim had also shipped in `docs/changelogs/upcoming.md` and was narrowed
  there to what the history supports.

## Closeout choices

- **Merge route:** merged into `main` locally by `tcw work complete`, which does
  the merge-back before the status move and then removes the worktree. Not
  pushed as part of completion.
- **Capability ledger:** `work/run-a-lifecycle-stage` recorded as `changed:` in
  `capabilities.yaml`. It stays `Supported`; its description gained the per-stage
  route. No status flip, and no new capability — nothing became possible that was
  impossible, the same composed read got a shorter way to ask for it.
- **Documentation:** all four declared entries fired and were answered in one
  pass — README, release notes, changelog, and the `tcw-work` driving skill.
- **Version:** a patch bump, at the user's direction, after completion.
- **Post-mortem:** not requested. Verification surfaced no defect that shipped;
  the two it found were caught before merge.
