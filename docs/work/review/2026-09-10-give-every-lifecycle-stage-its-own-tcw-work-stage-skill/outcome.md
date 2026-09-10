# Outcome: give every lifecycle stage its own `tcw-work-stage-<stage>` skill

Seven commits on `work/2026-09-10-give-every-lifecycle-stage-its-own-tcw-work-stage-skill`,
branched from `591e155`.

## What shipped, by task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 | `593bbcd` | `NUMBER_WORDS` extended 12 → 20, and skill names matched as whole tokens instead of bare substrings. |
| 2 | `2b0ed97` | The four composing-skill guards parametrised over all six skills; the per-stage set derived from `STAGE_IDS` minus a named exclusion set; two new tests. Committed red, 26 failures, all of them the five absent files. |
| 3 | `9f16070` | `skills/tcw-work-stage-spec/SKILL.md`. |
| 4 | `8cbaef3` | The remaining four skills, plus the Codex description (see below). |
| — | `bb477a9` | Skill frontmatter parsed as YAML rather than scanned line by line. |
| — | `5eff875` | The YAML defect in `tcw-work-stage-spec`, which Task 3 shipped. |
| 5 | — | No commit: `git diff main..HEAD -- skills/tcw-work-stage/SKILL.md` is empty. Criterion 6 holds. |
| 6 | — | **Not completed.** See below. |
| 7 | `3dbb82b` | README, the `tcw-work` commands table, the `run-a-lifecycle-stage` capability, release notes, changelog. |

## Test result

`python -m pytest -q -p no:cacheprovider` at `3dbb82b`: **2496 passed in 758.94s**,
exit 0. `tcw capabilities check` and `tcw validate` both exit 0.

## What the plan and spec got wrong

**The plan's green-at-every-boundary claim was impossible as written.**
`test_the_codex_description_counts_the_skills_it_ships` goes red the moment the
tenth skill lands and stays red until the description is updated, which the plan
scheduled last in Task 7. Four commits would have been red. The Codex description
is a tested invariant rather than free-form prose, so it moved forward into
Task 4's commit; Task 7 kept the rest. The plan's preamble is wrong about this
and was not corrected in place — this note is the correction.

**The plan under-specified Task 1.** It named only the `NUMBER_WORDS` `KeyError`.
The rename to `tcw-work-stage-<stage>` also silently disabled the enumeration
guard, because that test asked `n not in blob` and `tcw-work-stage` is a
substring of every one of the five new names. The spec caught this at rename time
and added criteria 8 and 11; the plan's Task 1 was rewritten to match. Worth
recording that the spec found it and the first plan did not.

**The plan said to verify the whole-token fix with a throwaway command.** That
leaves criterion 8 unprotected: reverting the helper to substring matching would
have failed nothing. A committed test replaced the throwaway
(`test_a_shared_name_prefix_cannot_stand_in_for_the_shorter_name`), and it was
confirmed red by reintroducing the substring matcher.

**Neither document anticipated the YAML defect, and it was the serious one.** All
five skills were written with a `when_to_use` containing `": "` inside an
unquoted plain scalar, which is a YAML syntax error. Every existing check passed:
`test_every_skill_has_name_and_description_frontmatter` split on `:` line by line
and found the keys it wanted. Codex parses this frontmatter, so all five skills
would have failed to load there while every test stayed green — precisely the
harness-compatibility failure the `spec` stage's own instructions warn about. The
root cause was not the wording but the check: line scanning cannot distinguish
valid frontmatter from invalid. `bb477a9` parses it, and it was confirmed red by
reintroducing the colon into `tcw-work-stage-verify`.

## Task 6 was not completed

Criterion 11 asks for a live invocation of `/tcw:tcw-work-stage-spec`, with and
without an item reference. It could not be run here. Claude loads the plugin from
`~/.claude/plugins/cache/tcw/tcw/2.0.0/`, which holds versioned **copies**, not a
link to this checkout, so this session runs the published 2.0.0 skills. Making it
run the new ones means writing into the user's plugin cache, which was not done.

Everything underneath the criterion was verified instead, and the parts that
remain unproven are narrow:

- Both injected commands were run by hand, exactly as the skills write them.
  `cat …/lifecycle/stage-spec.md` resolves. `tcw work stage prompt spec` with no
  reference exits 0 and prints the instructions with `<slug>` placeholders;
  `tcw work stage prompt spec <item>` exits 0 and substitutes the reference.
- That `$item` interpolates, and that an **omitted** argument becomes the empty
  string rather than a literal, were both observed earlier in the same session
  against the generic `tcw-work-stage` skill, which uses the identical mechanism.
  This is the fact the whole optional-argument design rests on and it is recorded
  in the spec's `## Notes` for the same reason.

What is left unproven is only that these five files, once installed, render. The
check needs a session with the plugin installed from this branch.

## Notes

**One out-of-scope fix.** `README.md` claimed two read-only review agents ship
and named `tcw-verifier` and `tcw-post-mortem`; three ship, and
`tcw-backlog-auditor` was missing. The error sits in the paragraph directly below
the skills table this item rewrote, and correcting it was smaller than filing an
item about it. It is unrelated to the per-stage skills and is called out here so
it is not mistaken for part of them.

**The five descriptions were read side by side** as the plan's Verification
section asks. Each opens `Read the TCW <stage> stage`, so the stage id is the
first discriminating token and `TCW` appears in all six. A prompt about writing a
spec for something that is not a TCW work item should not match.

**`tcw-work-stage` gained nothing and lost nothing.** It still takes both
arguments and still reaches all seven stages, which is what keeps `inbox` and
`postmortem` reachable as one composed read.
