What each layer tends to reveal:

- **`## Notes` across every artifact is the primary trail.** It is where each
  stage recorded what it knew _at the time_ — including things that looked
  unimportant then. A miss is often visible there as a noticed-but-unpursued
  detail.
- **`outcome.md`'s corrections.** A stage that had to correct the plan is a stage
  where the plan was wrong; ask whether it was knowably wrong.
- **`spec.md`'s acceptance criteria.** If verification rejected work that met
  every criterion, the criteria were the defect, not the implementation.
- **An artifact's absence.** A missing `spec.md` on an item that needed one is
  itself the finding — do not go looking further.
- **The commit range.** `git log` over the item's commits shows what order things
  actually happened in, which frequently is not the order the plan claims.

## The distinction that decides everything

**"Nobody could have known" versus "nobody checked."**

Only the second is actionable. Conflating them manufactures process for
non-recurring events, which is how a lifecycle accumulates ceremony nobody
believes in.

Ask of the earliest candidate stage: _was the information available at that
point?_ If the code that disproved a spec claim existed and was readable, the
spec stage could have checked and did not — actionable. If the failure depended
on something discovered only by building it, no earlier stage could have caught
it, and the honest finding is that the process worked.

TCW's own history has examples of both, and they look identical in hindsight
unless you ask this question explicitly.

## When to stop without a recommendation

Finish and say so when:

- The cause is genuinely one-off. Record it and stop.
- The only available recommendation is "be more careful." That is not a change;
  it is a wish. A post-mortem that produces it has not found the cause yet.
- The fix costs more than the failures it would prevent. Say that plainly — it is
  a real conclusion, not a failure to reach one.
