# Spec — Close four instruction gaps proposit found in 3.0.1

## Capability changes

Changed:

- `skills/commands-plan-work`: the description gains that the skill stops at
  plan even though the plan prompt's last line says to advance.

No new or removed capabilities, no taxonomy changes. The cross-project filing
behavior (`work/delegate-a-work-item-to-another-project`) does not change: only
one stderr line's wording does, and that record does not quote it (checked:
`grep -n "left uncommitted" docs/capabilities -r` finds nothing).

## Problem

1. `tcw/work/prompts/request.md`, Jira passage (added by TCW-100): "If they
   adopted changed wording, first put it into the ticket's description". It
   does not say whether that replaces the description. PRPI-198's description
   held an audit the proposed sections did not repeat.
2. `tcw/work/prompts/spec.md:50-58`, "Exit badly": only "_The code contradicts
   the request._ Stop and return to request." Nothing covers a requester who
   revises the request at spec.
3. `tcw/work/prompts/plan.md` ends with the footer "run `tcw work advance
   <slug>`" (`tcw/work/resolve.py`, `stage_footer`), while
   `skills/commands-plan-work/SKILL.md` says "Stop once the plan is written,
   leaving the item at plan." It never says that it overrides the footer.
4. `tcw/work/prompts/plan.md:38-40` (step 6) and `skills/work/SKILL.md:90-96`
   (epics; delegation) describe children only in the same project. With
   `--project`, `tcw work new` refuses `--parent`, `--tag`, `--blocked-by`
   (`tcw/work/cli.py:198-209`). TCW commits nothing and creating an item runs
   no hooks (`docs/guide/multi-repo.md:140-144`). A second filing into the same
   store before the first is committed is refused for a filesystem target
   (`tcw/work/open.py:155-158`). For a Jira target, the ticket is created and
   stays in the inbox (`tcw/work/jira/tickets.py:381-384`). The first filing's
   message, "the new files in … are left uncommitted"
   (`tcw/work/jira/tickets.py:395`), does not warn of this.

## Goals

1. The request prompt says to keep what the requester did not ask to change.
2. The spec prompt says what to do when the requester revises the request.
3. `commands-plan-work` says it overrides the plan footer's advance line.
4. The plan prompt and the `work` skill give the cross-project child steps,
   and the Jira filing message warns about the next filing.

## Non-goals

TCW-102 (children on other boards), TCW-103 (`--parent` with `--project`), any
commit by TCW, and any change to which flags `--project` accepts.

## Design

1. **Request, Jira passage.** After "put it into the ticket's description":
   "Change only what they adopted; keep everything else in the description."
2. **Spec, Exit badly**, a new bullet: "_The requester revises the request._
   Their word decides it, so the item stays at spec. Record the change where
   the request lives, as the request stage does (in Jira, the description at
   their word, with a comment saying who changed what and why; on files, a
   dated `## Added` section in the request), then write the spec against the
   revised request." Both backends' forms are in one bullet, because "Exit
   badly" is shared text. The spec prompt has no backend passages there, and
   adding a pair for one bullet is more than it needs.
3. **commands-plan-work.** In "Stop once the plan is written": "The plan
   prompt's last line says to run `tcw work advance`; under this skill, do
   not. That line is for `commands-drive-work-to-completion`."
4. **Cross-project children.**
   - Plan step 6 gains: "A part that belongs to another project: file it with
     `tcw work new "<title>" --project <id>`, which takes no `--parent`, then
     commit what it wrote in that project's store (TCW commits nothing), and
     set `--parent` and any `--blocked-by` with `tcw work edit` from inside
     that project. File the next part only after committing: until then a
     filing there is refused, or with Jira, stays in its inbox."
   - The `work` skill's delegation bullet says the same in one sentence,
     pointing to plan step 6.
   - The message at `tcw/work/jira/tickets.py:395` becomes: "the new files in
     <folder> are left uncommitted; commit them before filing into <project>
     again, or the next ticket stays in its Jira inbox".

## Abstraction litmus test

No new or changed operation. One message string and instruction text.

## Acceptance criteria

1. The Jira request passage contains "keep everything else in the
   description".
2. `spec.md` "Exit badly" has a bullet for the requester revising the request,
   saying the item stays at spec and naming both backends' forms.
3. `commands-plan-work` says the plan prompt's advance line does not apply
   under it.
4. Plan step 6 names `--project`, the commit, and `tcw work edit` from inside
   that project, in that order. The `work` skill's delegation bullet names the
   commit and points to it.
5. A Jira delegation that makes an item reports the new message: covered by a
   test through the fake Jira, asserting the "commit them before filing into"
   wording.
6. Bare `pytest` passes; `tcw validate` is clean.

### Coverage

Design items 1-4 map one-to-one to criteria 1-4; criterion 5 covers the
message in Design 4. A test asserts criteria 1, 2, 4 (plan step 6) and 5:
`tests/test_shipped_prompts.py` for the prompts, a Jira delegation test for
the message. Criterion 3 and the `work` skill sentence are read in review: no
test reads skill wording (the TCW-93 gap).

## Risks

- **Item 2 could read as "rewrite the request whenever you like".** The bullet
  says "their word decides it": the requester's word, as at request.
- **Plan step 6 grows.** It stays one paragraph.

## Notes

Changed during implement, and why:

- **Design 4's wording.** It said "commit". Shipped agent text may not name
  git or tell an agent to commit (`tests/test_shipped_text.py`,
  `test_no_shipped_text_names_git`, from TCW-74 criterion 8): TCW's text stays
  free of any one version control system, and each project brings its own
  through its hooks. The plan prompt and the `work` skill say instead to
  "record them in that project's version control, the way that project does".
  The guide and the CLI message, which may name git, still say "commit".
- **Design 2's bullet** is two lines, not six. The spec prompt has a 60-line
  limit (`test_each_prompt_is_at_most_60_lines_for_each_backend`), and it
  stood at 58.
