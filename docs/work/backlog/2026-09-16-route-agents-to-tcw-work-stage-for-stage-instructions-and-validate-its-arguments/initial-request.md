# Request — Route agents to tcw-work-stage for stage instructions and validate its arguments

## What is wanted, and why

An agent that wants to know *how* to perform a lifecycle stage should get there
by invoking the `tcw-work-stage` skill. That skill puts two things together: the
stage's own document, and the instructions this project adds for the stage
(`tcw work stage prompt`). Today the `tcw-work` skill links each stage document
directly, so an agent can open one on its own and never see the project's
instructions. The goal is to make invoking `tcw-work-stage` as likely as
possible.

1. **Stop the stage documents being found through `tcw-work`.**
   `skills/tcw-work/SKILL.md`, and the reference documents under
   `skills/tcw-work/references` that it links to, should no longer link to or
   name the Markdown files in `skills/tcw-work/references/lifecycle/`.
2. **Tell the agent to use the stage skill, with emphasis.** Add an emphasized
   note to `skills/tcw-work/SKILL.md`: an agent looking for instructions on *how*
   to perform a particular stage (the instructional prompt for that stage)
   should invoke the `tcw-work-stage` skill with the correct arguments.
3. **Other skills that name stage documents: decide one at a time.** Seven other
   skills name a stage document directly: `tcw-commands-plan-work`,
   `tcw-commands-verify-work`, `tcw-commands-process-inbox`,
   `tcw-commands-drive-work-to-completion`, `tcw-post-mortem`,
   `tcw-extras-triage-issues` and `documentation-sync`. Do not change them all
   in one sweep, and do not skip them all. Look at each reference and work out
   why it is there. Either it deliberately points at the bare stage document, or
   it expects the reader to get that document together with the project's
   instructions, which is what `tcw-work-stage` delivers. Change only the
   second kind.
4. **Check the stage skill's arguments before anything else runs.** Add a new
   command, **`tcw work stage validate <stage> [item]`**, a sibling of `gate`
   and `prompt`. Inject it very early in `skills/tcw-work-stage/SKILL.md`, right
   after the frontmatter, under a heading like "(Claude-only) Skill invocation
   validation".
   - **Valid:** `stage` is a known stage id. `item` is optional for every stage,
     including `inbox`, but when given it must name an existing work item. Valid
     arguments print nothing.
   - **Invalid:** a missing or unknown stage, or an item that does not exist.
     Print a Markdown usage error, for example: **Skill Invocation Error: The
     tcw-work-stage skill must be invoked with one to two arguments:
     `tcw-work-stage stage-id [work-slug]`**
5. **Adapt the output to the agent harness.** Dynamic context injection (the
   `` !`command` `` lines a skill runs when it loads) exists only in Claude Code.
   Under any other harness the command only runs if the agent runs it by hand.
   Use environment variables to tell harnesses apart: Claude Code sets
   `CLAUDE_CODE_SESSION_ID`, and Codex sets `CODEX_SESSION_ID`.
   - **Not Claude Code:** always print a harness message, even when the
     arguments are valid. For example: "Your AI agent harness does not support
     dynamic context injection. You will need to manually run all commands with
     !`command` to interpret this skill." Print it **before** the command's
     normal output, so the agent also gets the real validation result.
   - **Neither variable set** (for example, a person in a plain terminal):
     behave as under Claude Code.

## Constraints

- The command is `tcw work stage validate`, not `tcw work stage prompt validate`.
  `prompt` already takes the stage id as its first argument, so `validate` would
  be read as a stage name.
- Validity matches what `tcw work stage prompt` accepts today: the item is
  optional for every stage. This skill's own description says every stage
  except `inbox` takes an item. That wording and the validity rule should not
  contradict each other once this lands.

## Notes

- The two harness decisions were settled by the user in chat on 2026-09-16:
  print the harness message whenever the harness is not Claude Code, before the
  normal output, and treat "neither variable set" like Claude Code. The spec
  should confirm how "not Claude Code" is decided when only an unrelated
  harness's variables are present.
- Only this skill's two injected lines run automatically, and only under Claude
  Code. The validation line is the first of them, so any other harness only
  sees its result if the agent runs it by hand.

## References

- https://code.claude.com/docs/en/skills.md — Claude Code skills reference: named `arguments`, how `$name` is substituted (including when an argument is missing), and the `` !`command` `` injection syntax.
- https://code.claude.com/docs/en/env-vars.md — Claude Code environment variables, including `CLAUDE_CODE_SESSION_ID` used to detect the harness.
- https://learn.chatgpt.com/docs/config-file/environment-variables.md — Codex environment variables, including `CODEX_SESSION_ID`.
- `skills/tcw-work-stage/SKILL.md` — the skill that receives the validation line; its manual fallback also names the stage document path.
- `skills/tcw-work/references/commands.md:31` — describes `tcw-work-stage` as composing `lifecycle/stage-<id>.md`, so it names a stage document from inside `tcw-work`'s references.
- `tests/test_skill_lifecycle_parity.py`, `tests/test_documentation_sync_wiring.py` — existing tests that reach the stage documents by path and may assume the links this request removes.
- `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names` — related: renames `tcw-work-stage` to `work-stage`.
- `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability` — related: edits `tcw-work-stage`'s manual fallback for Codex.
- `2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings` — related: measures whether injected lines reach the agent.
