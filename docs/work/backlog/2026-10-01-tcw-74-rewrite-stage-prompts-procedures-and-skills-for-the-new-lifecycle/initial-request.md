# Rewrite stage prompts, procedures and skills for the new lifecycle

TCW 3.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) replaces the
work lifecycle: new stages, one move command (`advance`), item folders that never
move, stage folders with rounds and handoffs, comments, and Jira as a first-class
backend. Everything an agent reads about that lifecycle has to change with it. This
slice rewrites that text: the instructions TCW prints for each stage, the procedures
it ships, and the plugin's skills and agents.

## What is wanted

The instructions agents follow at each stage, rewritten for the new stages,
artifacts and readers, free of any assumption about how a project uses git, with
exactly one source for each piece of text. In the requester's terms:

1. **One built-in prompt per stage that has work to do**: inbox, request, spec,
   plan, implement, review, qa and postmortem. Completed and discarded have none.
   Today's `verify` prompt goes; review and qa replace it.
2. **Each prompt fits its stage's new job and readers.**
   - The request is written for any reader, product-first, from a template that
     asks what users will be able to do differently ("none" is a valid answer).
   - The spec declares the product changes formally and posts a **QA plan** as a
     comment on the item, readable by people outside engineering.
   - Implement changes the taxonomy and capability records in the same change as
     the code, and a later round reads the latest rejection.
   - Review checks the code (and the records) against the spec and plan; qa checks
     the product's behavior against the request and the QA plan.
   - Postmortem writes its document and can, when a project asks for it, say what
     the request missed in the request's own language.
   - Every prompt that resumes work reads the newest handoff first.
3. **Backend differences are marked, not duplicated.** One file per stage;
   passages that apply to only one backend are marked, and the instructions a
   project sees contain only the passages for its own backend. A project's own
   prompt files get the same treatment.
4. **The capabilities skill stops planning records.** No `Missing` records seeded
   at planning, no planning-document pointers, no flipping records at completion.
   Records change during implement, and `Missing` means a gap the team has
   acknowledged, not a plan.
5. **One source for each text.** Stage text exists once (the duplicated stage
   documents in the work skill go). Each procedure exists once. The artifact
   template module goes with `scaffold`; the request template lives in the
   request prompt.
6. **No git in built-in text.** Built-in prompts, procedures, skills and agents
   never tell an agent to commit, pull, push, branch or use a worktree. That is
   each project's choice, made through its own bindings and hooks.
7. **A decision for every skill, agent and procedure**: keep, rewrite or delete,
   defaulting to delete, with the work, capabilities, taxonomy, configure and setup
   skills rewritten, and the setup skill gaining a walkthrough for making a Jira
   workflow compatible, built on `tcw validate --remote`.

## Constraints

- **Breaking changes are expected.** This ships in 3.0.0; nothing is kept for 2.x
  compatibility.
- **Both harnesses are first-class.** Skills ship to Claude Code and Codex, so
  nothing a user must be able to do may depend on a Claude-only mechanism
  (`docs/lifecycle/harness.md`).
- **The abstraction litmus test applies** (`docs/lifecycle/abstraction.md`): text
  must work for both work backends.
- **TCW-69's model is fixed.** Stage names, folders, rounds, `judges`, handoffs,
  `path`, `advance` and `<item>/capabilities.yaml` are as TCW-69's spec defines
  them; this slice writes text against them and does not redefine them.
- **Plain language** throughout, as the repository's own guidance requires.

## Out of scope

- The `documentation-sync` skill's release flow (commit and tag) is exempt from
  the no-git rule.
- Strings in the Python code that mention git: TCW-73.
- User-facing documentation (README, guides, `docs/lifecycle/*.md`): TCW-75.
- This repository's own bindings and procedure files (`docs/lifecycle/*.md`,
  `docs/procedures/create-work.md`, the opt-in git example): TCW-76.
- The core model, backends, personal configuration and command surface: TCW-69 to
  TCW-73.

## Notes

- **No user was available to ask.** This request was written from the ticket
  (`intake.md`) and the epic's reference material, as the stage allows. Reference
  material was not asked for; what is listed below is what the epic supplied.
- **Assumption:** "skills and agents" means every file the plugin ships under
  `skills/` and `agents/`, including `skills/README.md` and the configure skill's
  reference documents. TCW-75's ticket also claims two of those reference
  documents; `spec` must settle the boundary.
- **Assumption:** the evals harness in `evals/` is in scope. It measures whether
  lifecycle instructions reach an agent, and every case is written against 2.x
  stages and verbs, so it breaks when the text it measures is rewritten.
- **Assumption:** this repository's `docs/lifecycle/*.md` bindings belong to
  TCW-76's migration, not here.
- **Open questions the ticket hands to `spec`:** the keep / rewrite / delete
  verdict for each candidate it lists (the five `commands-*` skills, `work-stage`,
  the `post-mortem` skill and agent, the `verifier` and `backlog-auditor` agents,
  `work-create`, the `extras-*` skills, three work-skill references, and four
  procedures).
- **Self-hosting.** Part of this change edits `tcw/` (the prompt loader and the
  backend filter), so from implementation onwards the repository's board is driven
  by editing files, not through the CLI, as `CLAUDE.md` requires.

## References

- [TCW-74](https://proposit.atlassian.net/browse/TCW-74): the ticket; `intake.md`
  holds it as imported. It is the requirement.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68) and its attached design
  decision record: the vision, and where the QA plan comment, the request
  template's product changes and the "built-in prompts never mention git" rule
  were first agreed.
- TCW-69's spec (`docs/work/backlog/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance/`):
  the stage table, layout, `judges`, handoffs, `path` and `advance` this text
  must describe exactly.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70),
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71): what differs between the
  filesystem and Jira backends, which decides every backend-marked passage.
- [TCW-73](https://proposit.atlassian.net/browse/TCW-73): the final command names
  the text must use.
- [TCW-75](https://proposit.atlassian.net/browse/TCW-75),
  [TCW-76](https://proposit.atlassian.net/browse/TCW-76): the documentation and
  migration slices that draw this slice's boundary.
- `skills/README.md`: today's verdict table for every skill, reference and agent,
  which the disposition table replaces.
- `evals/`: the harness that measures whether lifecycle instructions reach an
  agent.
