# Stage: postmortem

**Purpose.** Find which stage first missed a problem. Not blame and not a
summary: the question is _where would this have been cheapest to catch_. This
stage never moves the item, nothing waits on it, and it applies to any item
that was not discarded, finished or not.

**Inputs.** The item, read **backwards**: qa rounds, then review rounds, then
implement rounds (`tcw work path <slug> <stage>` for each); then the plan, the
spec and the request; then the item's comments, from `tcw work show <slug>`.
**`## Notes` across them is the primary trail**: where each stage recorded what
it knew at the time, often a detail noticed and not pursued. Also read:

- what an implement round says the plan or spec got wrong: was it knowably
  wrong when it was written?
- the spec's acceptance criteria: if work that met every one was rejected, the
  criteria were the defect;
- a missing document: a spec absent from an item that needed one is itself the
  finding.

**Resuming.** Read the newest `handoff-*.md` beside the file
`tcw work path <slug> postmortem` names, as a description of the work when it
was written, and check for anything newer before trusting it. To leave one,
write it to `tcw work path <slug> postmortem --handoff`.

**Produce** the postmortem, at `tcw work path <slug> postmortem`: what went
wrong; which stage could first have caught it; what would have had to be
different; and whether that change is worth making.

## Steps

1. Find the earliest stage whose documents could have shown the problem.
2. **Tell "nobody could have known" from "nobody checked."** Ask of that
   stage: was the information there at that point? If the code that disproved
   a spec claim existed and was readable, the spec could have checked:
   actionable. If the failure showed only once it was built, no earlier stage
   could have caught it, and the honest finding is that the process worked.
3. Write the postmortem. Create follow-up items with `tcw work new` for
   anything worth changing.
4. **What the request missed.** Only when the project's instructions for this
   stage ask for it: post a comment with `tcw work comment <slug>` saying what
   the request missed, written in the request's own language for its readers.

## Exit badly

Stop without a recommendation, and say why, when:

- the cause is a one-off; record it and stop;
- the only recommendation left is "be more careful", which is a wish, not a
  change: the cause has not been found yet;
- the fix costs more than the failures it would prevent; that is a real
  conclusion, not a failure to reach one.
