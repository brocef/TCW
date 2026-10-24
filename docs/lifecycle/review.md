<!-- Bound to the `review` stage of `tcw work`; see `.tcw/tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Review rules for this repository

_Applies at `review`. The built-in completion gate already requires an
accepted, current review verdict, and the records gate already checks the
capability records. What neither can check is below._

## Before writing an accepted verdict

Do both of these over the item's whole difference, not only its last commit:

1. **Run the test suite the way CI runs it:** bare `pytest` from the
   repository root, not `python -m pytest`. The two put different folders on
   Python's module search path, so a suite that passes one way can fail the
   other, and CI uses the bare form. A failing or erroring test means the
   verdict is not `accepted`.
2. **Invoke the `documentation-sync` skill** to evaluate this project's
   documentation entries (`tcw work docs` prints them) against the change, and
   make or list every update it calls for.

Neither is a `pre` hook: the suite runs far longer than a hook is allowed to,
and `documentation-sync` is a skill, which a hook cannot run. So the round
itself is the record. **Say in the round that both were done**, with the
suite's summary line and what `documentation-sync` concluded.

## Originating GitHub issues

If the item came from a GitHub issue, the issue is answered and closed only
after the fix is published: complete every item, cut the version, push, and
only then answer and close the issue, with text the owner has approved. An
issue closed earlier tells its reporter the fix is out when they still cannot
install it. The review does not close it; the item's qa findings (on this
project, a comment on its ticket, since qa is kept in Jira) say that the
closing waits for publication, and why.
