# Plan — Tell agents what to do when the person who decides a Jira-kept stage tells them, in chat, to move it

The spec's rules 1-6 and places P1-P9 are referred to by number.

## Lifecycle note

Step 2 edits `tcw/`. Following this repository's CLAUDE.md, once it starts,
the lifecycle is worked by hand: the ticket is moved in Jira to each stage's
status, round files are written directly, and the item's folder is committed
by hand, as the `commit-item-after-move.sh` hook would have done.

## Steps

1. **Tests first (red).**
   - `tests/work/test_stage_bookends.py` and
     `tests/work/jira/test_jira_stage_bookends.py`: replace `EXTERNAL_SENTENCE`
     with the new sentence, "a person decides whether the item moves on".
     Change `test_an_external_stage_footer_names_no_advance` into a test that
     the external footer names `` `tcw work advance <item>` `` and says
     "only when that person tells you to"; for qa, that it names `--to` and
     `--reason`, and keeps "The verdict is that move.". Assert that
     "Do not move it yourself" appears nowhere.
   - The stand-in backend test keeps checking that the choice is keyed on
     `external`, not on stage names: spec gets the external sentence and
     request the plain advance sentence.
   - `tests/test_shipped_prompts.py`: a test that the Jira request passage
     names writing the adopted wording into the description, reading it back,
     and `tcw work advance <slug> --reason`; and one that the Jira qa passage
     names both commands (`--to completed`, `--to implement`) as the agent's to
     run when the person gives the verdict in the conversation.
   - Run them; confirm they fail for the expected reason.
2. **P1, the footer** (`tcw/work/resolve.py`, `stage_footer`). For an external
   stage: "**When this stage's work is done, a person decides whether the
   item moves on.** Move it only when that person tells you to, in this
   conversation; a question or an implied yes is not that. Then run
   `tcw work advance {target} --reason "<who told you>"`." With a verdict:
   "`tcw work advance {target} --to <stage> --reason "<who decided, and
   why>"`. The verdict is that move." No stage or backend named.
3. **P2, P3, the prompts** (`tcw/work/prompts/request.md`, `qa.md`, Jira
   passages only). Request: rule 3, in order. Qa: replace step 3 with rules 4
   and 5.
4. **P4-P8, the skills.** Edit the passages listed in the spec's Problem
   section to carry the rules the spec's table assigns to each. Update the drive
   skill's `description`/`when_to_use` lines only if they contradict the new rule
   ("to qa for a person where it may not" still holds when nobody gives the
   verdict, so it stays).
5. **P9, the guides and README.** `docs/guide/jira.md` (the request paragraph
   at 44-46 and "Accepting or rejecting the work"), `docs/guide/work.md:168-169`,
   `README.md:512`.
6. **Capability records.** Update the three `description.md` files the spec's
   Capability changes names.
7. **Documentation entries.** `docs/changelogs/upcoming/<folder>.md` (Changed)
   and `docs/release-notes/upcoming/<folder>.md` (the behavior change for
   people using Jira). README.md and `docs/guide/jira.md` are covered by step
   5; `skills/<component>/SKILL.md` by step 4; no configuration key changes,
   so `skills/configure/references` is not touched.
8. **Sweep** (criterion 9): search outside `docs/work/` and changelogs for
   "person moves", "move it yourself", "stop at qa for a person", "Leave the
   decision to a person".
9. **Suite** as CI runs it: bare `pytest`, plus `tcw validate`.

## Documentation entries expected to fire

- Public-API: README.md (step 5), release notes (step 7).
- Jira-Change: `docs/guide/jira.md` (step 5).
- Guide-Topic-Change: `docs/guide/work.md` (step 5).
- Any-Code-Change: changelog (step 7).
- Skill-Driven-Component: the `work` skill and the command skills (step 4).
- Configuration-Key-Change: does not fire; no key changes.
