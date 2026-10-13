# Stage: implement

**Purpose.** Build it, and record what happened, including where the plan
was wrong.

**Inputs.** The spec and plan (`tcw work path <slug> spec` and `plan`), the
earlier rounds in `tcw work path <slug> implement`, and the latest rejection,
which is what makes a later round different from the first. Repository
discovery is unrestricted. **The latest rejection** is every review or qa round
saying `verdict: rejected` whose `judges` is the newest implement round's number
<!-- backend: filesystem -->
(in `tcw work path <slug> review` and `qa`).
<!-- /backend -->
<!-- backend: jira -->
(in `tcw work path <slug> review`), and every comment in `tcw work show <slug>`
recording a move from qa to implement that no implement round names as
answered: in Jira that move, with its comment, is how qa rejects.
<!-- /backend -->

**Resuming.** Read the newest `handoff-*.md` in `tcw work path <slug> implement`
as a description of the work when it was written; check for anything newer
before trusting it. Leave one at `tcw work path <slug> implement --handoff`.

**Produce** the code, the record changes, and one round at
`tcw work path <slug> implement --next`, with no verdict. The round says what
was done, step by step; the test result, from a command run just now; what the
plan or spec got wrong; which records changed; and which rejections it answers,
each by its round file or, for a comment, by its time as `tcw work show` prints
it. **Write the round once, at the end**, when the work it describes is
finished: never first, to fill in later.

## Steps

1. Work the plan's steps in order.
2. **Change the taxonomy and capability records in the same change as the
   code**, as `capabilities.yaml` in the folder `tcw work path <slug>` prints
   declares, so review finds them true. Write that file first if no earlier
   stage did. Give every new capability its status, normally `Supported`.
3. **Write the failing test first and watch it fail** before the code that
   makes it pass. A test that has never been red proves nothing. When a new
   test passes on its first run, break the behaviour it names and confirm it
   goes red before writing anything else.
4. On a bug or unexpected failure, **find the root cause before the fix**, and
   fix it where every caller goes through, not where it was reported.
5. **When the code disproves the plan, fix the plan and say so.** Working
   around it silently is how documents start lying.
6. Check each capability change against the standing records for
   contradictions.
7. **Once every step is done and the tests pass,**
   {{tcw:documentation}}evaluate every Documentation Sync entry in the project's agent guide
   (`AGENTS.md` or `CLAUDE.md`) once, against the whole finished change.{{/tcw:documentation}} Where the TCW plugin is
   installed, invoke the `documentation-sync` skill to do this.
8. **No claim that something works without output from a command run just now.**
9. Write the round. **Self-review:** an empty "what the plan or spec got wrong"
   is a claim, not an omission.

## Exit badly

- _The plan is unworkable._ Return to plan with
  `tcw work advance <slug> --to plan`; do not build a different design and
  leave the plan describing the abandoned one.
- _A step is blocked by other work._ Record it
  (`tcw work edit <slug> --blocked-by <ref>`), finish the rest, and say what
  was left out.
- _Scope grew._ Build what was specified; create a follow-up item for the rest.
