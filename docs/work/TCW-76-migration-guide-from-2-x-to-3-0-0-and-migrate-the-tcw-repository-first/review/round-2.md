---
verdict: rejected
judges: 2
---
# Review round 2 (TCW-76, Task B22)

A confirming reviewer, a separate agent that did not write the change and
could only read, reviewed implement round 2 at `d5fd6dc0` (`epic/tcw-3.0`):
whether each of review round 1's findings was fixed, and whether the fixes
brought new defects. It found four defects and four smaller notes, below,
and ended with **NOT DONE**.

**Verdict: rejected.** D1 and D4 make a step's order or command wrong for
some project (criteria 1 to 10 and 32: the guide gives a migration an agent
can follow, with a check per step); D2 is a test that cannot notice the
guide's check changing; D3 is a pointer to a rule that is not where it says.
The notes are wrong or unclear statements.

**The owner's decision (2026-10-20).** Asked how to finish, the owner
answered "I fix + test, no review": implement fixes all eight findings,
gives each defect a test that fails without its fix (each one
mutation-checked), and no further review round is run. TCW-76 then moves to
qa.

**The owner's Jira account ID.** Review round 1's B-G removed the ID from
the migration log. The owner chose to leave it in the history of the older
commits that hold it, and not to rewrite them.

Implement must fix every finding below, verifying each against the code or
files first, changing only `docs/`, `tests/`, `AGENTS.md` and the migration
log.

## Findings

`guide` is `docs/migration-guide-2.8-to-3.0.0.md`; line numbers are at
`d5fd6dc0` and approximate.

### Defects

- **D1.** The check that the configuration's status names are spelled as
  Jira spells them is at step 3 (about 381-387), and the `work.tracker.statuses`
  row ends "(step 3)". Step 2's first bullet ("a status for each stage turned
  on that has none yet", about 329) runs first, so a misspelled 2.x status
  reaches step 2 unchecked and Jira gains a status it already had. The
  comparison belongs in step 1's stages bullet and step 2's first bullet,
  with the row pointing there; step 3 can keep a reminder.
- **D2.** `tests/test_migration_guide.py`,
  `test_step_9s_patterns_find_a_whole_old_name_and_not_a_longer_one`, runs
  its own `grep -rnE -f old.re docs` rather than the guide's check, so
  changing the guide's search to `grep -rnF` leaves every test green.
- **D3.** `docs/lifecycle/harness.md` line 19 says "a subagent is permitted,
  never required (the rules below)", but nothing below it says so. Name
  where the rule lives, or state it in place.
- **D4.** Step 12's places command,
  `t=$(realpath "$l" 2>/dev/null) || continue  # a link that points nowhere`:
  GNU `realpath` succeeds on a link that points nowhere, so the dangling
  link's target is added to the places. The test's `broken.md` points inside
  `.claude/skills`, so it cannot notice.

### Notes

- **N1.** Step 5's counter (about 527) joins the first lines with
  `head -n 1`, which merges a file without a final newline into the next
  file's first line.
- **N2.** The changelog entry (`docs/changelogs/upcoming/TCW-76-…md`) says
  "a git pull prompt on every stage from request on", which reads as if
  `completed` and `discarded` took one; they bind no prompt
  (`tcw/work/model.py`, about 314-316).
- **N3.** The migration log, about 588-593: the B-F correction rewrote text
  inside `## Approved plan`, which is recorded word for word.
- **N4.** Pi also reads `AGENTS.MD` and `CLAUDE.MD`, in capitals, which
  differ from the lower-case names on a disk that tells case apart; step 12's
  places leave them out.
