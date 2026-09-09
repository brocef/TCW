# Outcome: compose a lifecycle stage into one skill document

Shipped as specified. The three unknowns in Task 0 were measured, and two of the
three answers changed the design.

## What the measurements said

Probed with throwaway skills under `.claude/skills/` and headless `claude -p`
runs, then re-run against the real skill installed into the plugin cache.

| Question | Answer | Effect on the design |
| --- | --- | --- |
| Argument substitution vs. injection order | Substitution happens **first**. `$name`, `$ARGUMENTS[0]`, and `$0` all interpolate *inside* a `` !`cmd` `` — `$0` came back as the argument, not the shell name | The design is possible at all. Named arguments chosen for readability |
| Does stderr reach the model? | **Yes.** `` !`echo X >&2` `` renders X | **No `2>&1` needed.** The plan assumed one; `prompt`'s illegal-stage note arrives on its own |
| Non-zero exit | Aborts the whole invocation; the model sees **nothing**, not an error, and not the static body either | Both commands end `|| true`, so the CLI's own message is what the reader gets |

A fourth thing surfaced only by running it: **an injected command that is not
pre-approved aborts the invocation the same silent way.** The first live run
returned an empty result with `num_turns: 0` and no error; adding
`allowed-tools: Bash(tcw *)` fixed it. That is now criterion 7 and a test,
because the failure is indistinguishable from the skill not existing.

## Acceptance criteria

Criteria 1–4 were checked by invoking the real skill from the installed plugin
against this repository's own board.

| # | Result |
| --- | --- |
| 1 | Pass — `implement` on the active split item: both blocks real content, no error |
| 2 | Pass — `plan` on the same active item: both blocks render and the model quoted back `note — 'plan' is not legal for an item in 'active'` |
| 3 | Pass — `inbox` with no item: both blocks render, no error text |
| 4 | Pass — `spec no-such-item-at-all`: skill renders, `no such work item: no-such-item-at-all` visible, and the model quoted the "to enter the stage, run `tcw work stage begin`" line back |
| 5 | Pass — `test_the_composing_skill_reads_a_router_that_exists_for_every_stage` |
| 6 | Pass — `test_the_composing_skill_reads_with_prompt_and_names_begin_for_entry` |
| 7 | Pass — `test_the_composing_skill_declares_the_commands_it_injects` |
| 8 | Pass — `test_every_stage_document_names_the_harness_neutral_binding_command` untouched and green for all seven |
| 9 | Pass — `skills/tcw-work/SKILL.md` unchanged |

All three new tests were confirmed capable of failing: renaming the router path,
renaming `begin` to `enter`, and dropping `Bash(cat *)` from `allowed-tools` each
fails its own test and only its own.

## What the plan got wrong

**The `2>&1` was unnecessary.** The plan carried it as a fix for a hazard that
does not exist — injection captures both streams. Reasoning from the
documentation alone would have shipped a redirect that does nothing and an
explanation of why it was needed that is false.

**The pointer did not fit where the plan put it.** It was written into
`skills/tcw-work/SKILL.md`'s `Always` bullet, which took the body from 60 lines
to 63 and failed `test_the_router_stays_within_its_line_budget` — whose message
is "extract, don't grow". It moved to `references/commands.md`, which is where
the two stage verbs are already documented. Claude's discovery of the skill does
not depend on that row; it depends on the skill's `description`.

## Notes

This is `tcw work stage prompt`'s second caller and its first that is not its
author, which is the question the split item's plan left open under
"`prompt` is worth its cost". A skill can only be built this way because `prompt`
resolves without gating: `begin` would run `require_artifact.py` and print
nothing for exactly the stage someone is asking about.

The hazard is the same fact seen from the other side, and it is why criterion 6
exists rather than being left to review: a skill that hands over a stage's
instructions and does not name `begin` is a route around the gate, and it would
read as helpful.
